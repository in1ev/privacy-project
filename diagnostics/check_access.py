import requests
import json

MARKET_URL = "http://127.0.0.1:5000"


def check_admin_access_without_auth():
    """
    [결함1 진단] /admin/members API가 인증 없이 호출되었을 때
    실제로 데이터를 반환하는지 확인한다.

    정상(After) 상태라면 401 또는 403이 반환되어야 하고,
    결함(Before) 상태라면 200과 함께 전체 회원 목록이 반환된다.
    """
    result = {
        "check_name": "접근권한 미분리 (결함1)",
        "target": f"{MARKET_URL}/admin/members",
        "passed": None,
        "detail": ""
    }

    try:
        res = requests.get(f"{MARKET_URL}/admin/members", timeout=5)

        if res.status_code == 200:
            member_count = len(res.json())
            result["passed"] = False
            result["detail"] = f"인증 없이 200 OK 응답 수신. 전체 회원 {member_count}명의 정보가 노출됨 (카드번호 포함 여부는 별도 확인 필요)"
        elif res.status_code in (401, 403):
            result["passed"] = True
            result["detail"] = f"인증 없는 요청이 {res.status_code}로 차단됨 (정상)"
        else:
            result["passed"] = None
            result["detail"] = f"예상치 못한 응답 코드: {res.status_code}"

    except requests.exceptions.ConnectionError:
        result["passed"] = None
        result["detail"] = "한빛마켓 서버(5000번 포트)에 연결할 수 없음. 서버가 켜져 있는지 확인 필요"

    return result


if __name__ == '__main__':
    result = check_admin_access_without_auth()
    print(json.dumps(result, indent=2, ensure_ascii=False))