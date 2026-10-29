import json
import os
import sqlite3

import requests

from config import DEFAULT_TARGET


def _count_logs(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM access_logs").fetchone()[0]
    finally:
        conn.close()


def check_access_log_table_exists(target=DEFAULT_TARGET):
    """
    [결함4 진단] 접속기록이 실제로 남는지 확인한다.
    (함수 이름은 run_diagnosis.py와의 호환을 위해 유지)

    1) access_logs 테이블이 존재하는가
    2) 실제로 요청을 보냈을 때 기록이 늘어나는가
    테이블만 만들어 두고 기록하지 않는 경우를 통과시키지 않기 위해 2)까지 확인한다.
    """
    db_path = target.market_db_path

    result = {
        "check_name": "접속기록 미보관 (결함4)",
        "target": db_path,
        "passed": None,
        "detail": ""
    }

    if not os.path.exists(db_path):
        result["detail"] = "market.db 파일을 찾을 수 없음"
        return result

    conn = sqlite3.connect(db_path)
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';")]
    conn.close()

    if 'access_logs' not in tables:
        result["passed"] = False
        result["detail"] = f"access_logs 테이블이 존재하지 않음. 현재 테이블: {tables}"
        return result

    before_count = _count_logs(db_path)
    try:
        # 존재하지 않는 회원(id=0) 조회: 데이터를 건드리지 않으면서 라우트를 지나가는 요청
        requests.get(f"{target.market_url}/members/0", timeout=5)
    except requests.exceptions.ConnectionError:
        result["detail"] = "한빛마켓 서버에 연결할 수 없어 기록 생성 여부를 확인하지 못함"
        return result
    after_count = _count_logs(db_path)

    if after_count > before_count:
        result["passed"] = True
        result["detail"] = f"테스트 요청 후 접속기록이 {before_count}건 → {after_count}건으로 증가함"
    else:
        result["passed"] = False
        result["detail"] = "access_logs 테이블은 있으나 요청 후에도 기록이 늘지 않음 (기록 로직 없음 또는 실패)"

    return result


if __name__ == '__main__':
    print(json.dumps(check_access_log_table_exists(), indent=2, ensure_ascii=False))