import requests

MARKET_URL = "http://127.0.0.1:5000"
PAY_URL = "http://127.0.0.1:5001"


def transfer_member_to_pay(market_member_id):
    """
    한빛마켓 회원 정보를 한빛페이로 전송하여 계정을 연동한다.

    [결함6] 이 함수를 호출하기 전에 반드시 있어야 할 절차가 빠져있음:
        - 이용자에게 "어떤 항목이, 어떤 목적으로, 한빛페이로 전송되는지" 고지
        - 이에 대한 명시적 동의(체크박스 등) 획득 및 동의 이력 저장
      지금은 그런 절차 없이 그냥 회원 정보를 가져와서 바로 전송함
    """

    # 1. 한빛마켓에서 회원 정보 조회
    #    [결함1의 연쇄효과] 이 조회 자체도 아무 인증 없이 가능했다는 걸 이미 확인함
    res = requests.get(f"{MARKET_URL}/members/{market_member_id}")
    if res.status_code != 200:
        print("한빛마켓 회원 조회 실패:", res.status_code)
        return

    member = res.json()

    # 2. 한빛페이로 전송할 데이터 구성
    #    [결함3] 여기서 인증 토큰이나 서명 없이 그냥 평문 JSON을 전송함
    #            한빛마켓→한빛페이 사이에 "이 요청이 진짜 한빛마켓에서 온 게 맞는지"
    #            확인할 방법이 전혀 없음 (누구든 이 API를 알면 가짜 요청을 보낼 수 있음)
    payload = {
        "name": member["name"],
        "phone": member["phone"],
        "birth_date": None,  # 한빛마켓에는 생년월일 필드가 없어 비워둠(실제로는 있다고 가정)
        "market_id": member["id"],
        "bank_account": None,
        "role": "user"
    }

    # 3. 한빛페이로 전송 (HTTP 평문, 인증 헤더 없음)
    res = requests.post(f"{PAY_URL}/accounts/link", json=payload)

    if res.status_code == 201:
        print("계정 연동 성공:")
        print(res.json())
    else:
        print("연동 실패:", res.status_code, res.text)


if __name__ == '__main__':
    transfer_member_to_pay(1)  # 한빛마켓 회원 id=1(홍길동)을 한빛페이로 전송