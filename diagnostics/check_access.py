import json
import time

import requests

from config import DEFAULT_TARGET

PROBE_PASSWORD = "Diag-Probe-2345"


def check_admin_access_without_auth(target=DEFAULT_TARGET):
    """
    [결함1 진단] 접근통제가 실제로 작동하는지 두 단계로 확인한다.

    1단계: 인증 없이 관리자 API와 회원 조회 API를 호출한다. 200이면 결함이다.
    2단계: 1단계를 통과한 경우에만, 진단용 일반 사용자 2명을 만들어 아래를 확인한다.
           - 일반 사용자 토큰으로 관리자 API 호출 → 403이어야 함
           - 일반 사용자 토큰으로 다른 회원 조회 → 403이어야 함
           - 일반 사용자 토큰으로 본인 조회 → 200이어야 함 (모든 요청을 막아서 통과하는 것을 방지)
    로그인만 요구하고 권한은 나누지 않는 구현이 통과하지 못하도록 2단계가 필요하다.
    """
    base = target.market_url
    result = {
        "check_name": "접근권한 미분리 (결함1)",
        "target": f"{base}/admin/members",
        "passed": None,
        "detail": ""
    }

    try:
        res_admin = requests.get(f"{base}/admin/members", timeout=5)
        res_member = requests.get(f"{base}/members/1", timeout=5)
    except requests.exceptions.ConnectionError:
        result["detail"] = "한빛마켓 서버에 연결할 수 없음. 서버가 켜져 있는지 확인 필요"
        return result

    # ---- 1단계: 인증 없는 호출 ----
    if res_admin.status_code == 200 or res_member.status_code == 200:
        result["passed"] = False
        parts = []
        if res_admin.status_code == 200:
            try:
                count = len(res_admin.json())
            except ValueError:
                count = "?"
            parts.append(f"인증 없이 200 OK 응답 수신. 전체 회원 {count}명의 정보가 노출됨 (카드번호 포함 여부는 별도 확인 필요)")
        if res_member.status_code == 200:
            parts.append("개별 회원 조회(/members/1)도 인증 없이 가능")
        result["detail"] = ". ".join(parts)
        return result

    unauth_ok = {401, 403}
    if res_admin.status_code not in unauth_ok or res_member.status_code not in unauth_ok:
        result["detail"] = (f"예상치 못한 응답 코드: 관리자 API {res_admin.status_code}, "
                            f"회원 조회 {res_member.status_code}")
        return result

    # ---- 2단계: 인증 후 권한 분리 확인 ----
    try:
        stamp = int(time.time() * 1000)
        users = []
        for tag in ("a", "b"):
            email = f"diag-{stamp}-{tag}@diag.local"
            signup = requests.post(f"{base}/members", timeout=5, json={
                "name": f"진단용{tag}", "phone": "01000000000",
                "email": email, "password": PROBE_PASSWORD})
            login = requests.post(f"{base}/login", timeout=5,
                                  json={"email": email, "password": PROBE_PASSWORD})
            if signup.status_code != 201 or login.status_code != 200:
                result["detail"] = (f"인증 없는 요청은 차단되나 진단용 계정 생성/로그인에 실패해 "
                                    f"권한 분리를 확인하지 못함 (가입 {signup.status_code}, 로그인 {login.status_code})")
                return result
            users.append({"id": signup.json()["id"],
                          "headers": {"Authorization": f"Bearer {login.json()['access_token']}"}})
        a, b = users

        admin_res = requests.get(f"{base}/admin/members", headers=a["headers"], timeout=5)
        other_res = requests.get(f"{base}/members/{b['id']}", headers=a["headers"], timeout=5)
        self_res = requests.get(f"{base}/members/{a['id']}", headers=a["headers"], timeout=5)
    except requests.exceptions.ConnectionError:
        result["detail"] = "진단 중 서버 연결이 끊어짐"
        return result

    problems = []
    if admin_res.status_code == 200:
        problems.append("일반 사용자 토큰으로 관리자 API 접근 가능")
    if other_res.status_code == 200:
        problems.append("일반 사용자 토큰으로 다른 회원 정보 조회 가능")

    if problems:
        result["passed"] = False
        result["detail"] = "로그인은 요구하나 권한이 분리되지 않음: " + ", ".join(problems)
    elif self_res.status_code != 200:
        result["detail"] = f"일반 사용자의 본인 정보 조회가 {self_res.status_code}로 실패해 판정 불가"
    else:
        result["passed"] = True
        result["detail"] = ("인증 없는 요청은 401로 차단, 일반 사용자 토큰은 관리자 API(403)와 "
                            "타인 정보 조회(403)가 차단되고 본인 정보는 조회됨")
    return result


if __name__ == '__main__':
    print(json.dumps(check_admin_access_without_auth(), indent=2, ensure_ascii=False))