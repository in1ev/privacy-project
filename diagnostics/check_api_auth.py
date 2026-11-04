import hashlib
import hmac
import json
import os
import secrets
import time

import requests

from config import DEFAULT_TARGET

SECRET_ENV = "HANBIT_SYNC_SECRET"


def _signed_headers(secret, method, path, body):
    """한빛 서비스 간 서명 규약과 같은 방식으로 헤더를 만든다 (정상 서명 요청 확인용)."""
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    body_hash = hashlib.sha256(body).hexdigest()
    text = f"{timestamp}\n{nonce}\n{method.upper()}\n{path}\n{body_hash}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), text, hashlib.sha256).hexdigest()
    return {"X-Hanbit-Timestamp": timestamp, "X-Hanbit-Nonce": nonce, "X-Hanbit-Signature": sig}


def check_link_api_without_auth(target=DEFAULT_TARGET):
    """
    [결함3 진단] 한빛페이의 /accounts/link가 '요청이 한빛마켓에서 왔는지'를 실제로 검증하는지 확인한다.

    1) 서명 없는 요청        → 401/403이어야 함 (201이면 결함)
    2) 엉터리 서명을 붙인 요청 → 401/403이어야 함 (헤더 유무만 보는 구현을 걸러냄)
    3) [선택] 환경변수 HANBIT_SYNC_SECRET이 있으면 정상 서명 요청이 통과하는지와,
       같은 요청을 다시 보냈을 때(재전송) 거부되는지까지 확인한다.
       정상 요청까지 막아서 통과하는 구현을 가려내기 위함이다.
    """
    base = target.pay_url
    result = {
        "check_name": "API 무인증 통신 (결함3)",
        "target": f"{base}/accounts/link",
        "passed": None,
        "detail": ""
    }

    def payload(market_id):
        return {"name": "진단테스트", "phone": "01099998888", "market_id": market_id, "role": "user"}

    blocked = {401, 403}
    try:
        # 1) 서명 없음
        res = requests.post(f"{base}/accounts/link", json=payload(900000001), timeout=5)
        if res.status_code == 201:
            result["passed"] = False
            result["detail"] = "인증 정보 없이도 계정 생성 성공(201). 요청 출처를 검증하지 않음"
            return result
        if res.status_code not in blocked:
            result["detail"] = f"예상치 못한 응답 코드: {res.status_code}"
            return result

        # 2) 엉터리 서명
        body = json.dumps(payload(900000002)).encode("utf-8")
        fake = {"Content-Type": "application/json",
                "X-Hanbit-Timestamp": str(int(time.time())),
                "X-Hanbit-Nonce": secrets.token_hex(16),
                "X-Hanbit-Signature": "0" * 64}
        res = requests.post(f"{base}/accounts/link", data=body, headers=fake, timeout=5)
        if res.status_code == 201:
            result["passed"] = False
            result["detail"] = "서명 값이 틀려도 계정 생성 성공(201). 서명 내용을 검증하지 않음"
            return result
        if res.status_code not in blocked:
            result["detail"] = f"예상치 못한 응답 코드(엉터리 서명): {res.status_code}"
            return result

        # 3) 정상 서명 + 재전송 (키가 있을 때만)
        secret = os.environ.get(SECRET_ENV)
        if not secret:
            result["passed"] = True
            result["detail"] = ("서명 없는 요청과 엉터리 서명 요청이 모두 차단됨 "
                                f"(정상 서명 요청 확인은 생략: 환경변수 {SECRET_ENV} 미설정)")
            return result

        market_id = 900000000 + secrets.randbelow(90000000)
        good_body = json.dumps(payload(market_id)).encode("utf-8")
        good = {"Content-Type": "application/json", **_signed_headers(secret, "POST", "/accounts/link", good_body)}
        first = requests.post(f"{base}/accounts/link", data=good_body, headers=good, timeout=5)
        replay = requests.post(f"{base}/accounts/link", data=good_body, headers=good, timeout=5)
    except requests.exceptions.ConnectionError:
        result["detail"] = "한빛페이 서버에 연결할 수 없음"
        return result

    if first.status_code != 201:
        result["detail"] = f"정상 서명 요청이 {first.status_code}로 거부되어 판정 불가 (키가 서버와 같은지 확인)"
    elif replay.status_code == 201:
        result["passed"] = False
        result["detail"] = "같은 요청을 다시 보내도 처리됨(재전송 공격에 취약)"
    elif replay.status_code not in blocked:
        result["detail"] = f"재전송 요청에 예상치 못한 응답 코드: {replay.status_code}"
    else:
        result["passed"] = True
        result["detail"] = "서명 없음·엉터리 서명·재전송 요청은 차단되고, 정상 서명 요청은 처리됨"
    return result


if __name__ == '__main__':
    print(json.dumps(check_link_api_without_auth(), indent=2, ensure_ascii=False))