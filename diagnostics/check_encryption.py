import sqlite3
import re
import json
import os

MARKET_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'hanbit-market', 'market.db')

# 카드번호 패턴: 12~19자리 숫자 (실제 카드번호 형식과 유사)
CARD_PATTERN = re.compile(r'^\d{12,19}$')
# 휴대전화번호 패턴
PHONE_PATTERN = re.compile(r'^01\d{8,9}$')


def check_plaintext_storage():
    """
    [결함2 진단] members 테이블의 card_number, phone 컬럼 값이
    평문(암호화되지 않은 원본 형태) 패턴과 일치하는지 확인한다.

    암호화되어 있다면 Base64/hex 등으로 인코딩된 형태라
    위 정규식 패턴과 일치하지 않아야 한다.
    """
    result = {
        "check_name": "결제정보·연락처 평문 저장 (결함2)",
        "target": MARKET_DB_PATH,
        "passed": None,
        "detail": ""
    }

    if not os.path.exists(MARKET_DB_PATH):
        result["detail"] = "market.db 파일을 찾을 수 없음"
        return result

    conn = sqlite3.connect(MARKET_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, phone, card_number FROM members")
    rows = cursor.fetchall()
    conn.close()

    plaintext_findings = []

    for row in rows:
        member_id, phone, card_number = row
        if phone and PHONE_PATTERN.match(phone):
            plaintext_findings.append(f"member_id={member_id}: phone 평문 패턴 일치 ({phone})")
        if card_number and CARD_PATTERN.match(card_number):
            plaintext_findings.append(f"member_id={member_id}: card_number 평문 패턴 일치 ({card_number})")

    if plaintext_findings:
        result["passed"] = False
        result["detail"] = f"{len(plaintext_findings)}건의 평문 저장 발견: " + " / ".join(plaintext_findings)
    else:
        result["passed"] = True
        result["detail"] = "평문 패턴과 일치하는 값이 발견되지 않음 (암호화 적용 추정)"

    return result


if __name__ == '__main__':
    result = check_plaintext_storage()
    print(json.dumps(result, indent=2, ensure_ascii=False))