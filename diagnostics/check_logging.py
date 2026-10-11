import sqlite3
import json
import os

from config import DEFAULT_TARGET


def check_access_log_table_exists(target=DEFAULT_TARGET):
    """
    [결함4 진단] 접속기록을 저장하는 access_logs 테이블이
    실제로 존재하는지 DB 스키마를 직접 조회하여 확인한다.
    """
    result = {
        "check_name": "접속기록 미보관 (결함4)",
        "target": target.market_db_path,
        "passed": None,
        "detail": ""
    }

    if not os.path.exists(target.market_db_path):
        result["detail"] = "market.db 파일을 찾을 수 없음"
        return result

    conn = sqlite3.connect(target.market_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    if 'access_logs' in tables:
        result["passed"] = True
        result["detail"] = f"access_logs 테이블 존재 확인. 전체 테이블: {tables}"
    else:
        result["passed"] = False
        result["detail"] = f"access_logs 테이블이 존재하지 않음. 현재 테이블: {tables}"

    return result


if __name__ == '__main__':
    result = check_access_log_table_exists()
    print(json.dumps(result, indent=2, ensure_ascii=False))