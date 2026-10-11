import argparse
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

from config import Target, DEFAULT_TARGET
from check_access import check_admin_access_without_auth
from check_encryption import check_plaintext_storage
from check_api_auth import check_link_api_without_auth
from check_logging import check_access_log_table_exists
from check_patch import check_known_vulnerabilities


def run_all_diagnostics(target=DEFAULT_TARGET):
    checks = [
        check_admin_access_without_auth,
        check_plaintext_storage,
        check_link_api_without_auth,
        check_access_log_table_exists,
        check_known_vulnerabilities,
    ]

    results = []
    for check_fn in checks:
        print(f"실행 중: {check_fn.__name__} ...")
        if check_fn is check_known_vulnerabilities:
            result = check_fn()          # 패치 점검은 target이 필요 없음
        else:
            result = check_fn(target)
        results.append(result)

    passed_count = sum(1 for r in results if r["passed"] is True)
    total = len(results)

    return {
        "total_checks": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "results": results,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--market-url', default=DEFAULT_TARGET.market_url)
    parser.add_argument('--pay-url', default=DEFAULT_TARGET.pay_url)
    parser.add_argument('--market-db', default=DEFAULT_TARGET.market_db_path)
    args = parser.parse_args()

    target = Target("custom", args.market_url, args.pay_url, args.market_db)
    summary = run_all_diagnostics(target)

    print("\n" + "=" * 50)
    print(f"진단 완료: {summary['passed']} / {summary['total_checks']} 통과")
    print("=" * 50)

    for r in summary["results"]:
        status = "✅ 통과" if r["passed"] else "❌ 결함 발견" if r["passed"] is False else "⚠️ 확인 불가"
        print(f"\n[{status}] {r['check_name']}")
        print(f"  {r['detail']}")

    output_path = os.path.join(os.path.dirname(__file__), '..', 'report', 'latest_diagnosis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n결과가 저장되었습니다: {output_path}")