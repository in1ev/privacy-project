"""
한빛마켓 회원이 한빛페이 연동을 요청하는 과정을 시연한다. (After)
사용자는 한빛마켓에 로그인한 뒤 '연동'을 요청하고, 한빛마켓 서버가 서명해서 한빛페이로 전달한다.
사용법:  python transfer_after.py <이메일> <회원id>
"""
import getpass
import sys

import requests

MARKET_URL = "http://127.0.0.1:5010"


def transfer_member_to_pay(email, password, member_id, market_url=MARKET_URL):
    login = requests.post(f"{market_url}/login", json={"email": email, "password": password}, timeout=5)
    if login.status_code != 200:
        return login.status_code, login.json()
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    res = requests.post(f"{market_url}/members/{member_id}/link-pay", headers=headers, timeout=10)
    return res.status_code, res.json()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("사용법: python transfer_after.py <이메일> <회원id>")
        sys.exit(1)
    status, body = transfer_member_to_pay(sys.argv[1], getpass.getpass("비밀번호: "), int(sys.argv[2]))
    print(status, body)