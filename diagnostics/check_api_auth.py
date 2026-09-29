import requests
import json

PAY_URL = "http://127.0.0.1:5001"


def check_link_api_without_auth():
    """
    [결함3 진단] 한빛페이의 /accounts/link API가
    인증 토큰/서명 없이 호출되어도 계정을 생성해주는지 확인한다.
    """
    result = {
        "check_name": "API 무인증 통신 (결함3)",
        "target": f"{PAY_URL}/accounts/link",
        "passed": None,
        "detail": ""
    }

    fake_payload = {
        "name": "진단테스트",
        "phone": "01099998888",
        "market_id": 9999,
        "role": "user"
    }

    try:
        # 의도적으로 인증 헤더를 전혀 넣지 않고 요청
        res = requests.post(f"{PAY_URL}/accounts/link", json=fake_payload, timeout=5)

        if res.status_code == 201:
            result["passed"] = False
            result["detail"] = "인증 정보 없이도 계정 생성 성공(201). 요청 출처를 검증하지 않음"
        elif res.status_code in (401, 403):
            result["passed"] = True
            result["detail"] = f"인증 없는 요청이 {res.status_code}로 차단됨 (정상)"
        else:
            result["detail"] = f"예상치 못한 응답 코드: {res.status_code}"

    except requests.exceptions.ConnectionError:
        result["detail"] = "한빛페이 서버(5001번 포트)에 연결할 수 없음"

    return result


if __name__ == '__main__':
    result = check_link_api_without_auth()
    print(json.dumps(result, indent=2, ensure_ascii=False))