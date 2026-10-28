import argparse
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

from config import BEFORE_TARGET, AFTER_TARGET
from check_access import check_admin_access_without_auth
from check_encryption import check_plaintext_storage
from check_api_auth import check_link_api_without_auth
from check_logging import check_access_log_table_exists
from check_patch import check_known_vulnerabilities

TARGETS = {'before': BEFORE_TARGET, 'after': AFTER_TARGET}


def run_all_diagnostics(target=BEFORE_TARGET):
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
        results.append(check_fn(target))      # 모든 진단이 target을 받는다

    passed = sum(1 for r in results if r["passed"] is True)
    failed = sum(1 for r in results if r["passed"] is False)
    unknown = len(results) - passed - failed

    return {
        "target": target.name,
        "total_checks": len(results),
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "results": results,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=list(TARGETS), default='before')
    args = parser.parse_args()

    target = TARGETS[args.target]
    summary = run_all_diagnostics(target)

    print("\n" + "=" * 50)
    print(f"[{target.name}] 진단 완료: {summary['passed']} / {summary['total_checks']} 통과"
          f" (결함 {summary['failed']}, 확인 불가 {summary['unknown']})")
    print("=" * 50)

    for r in summary["results"]:
        status = "✅ 통과" if r["passed"] else "❌ 결함 발견" if r["passed"] is False else "⚠️ 확인 불가"
        print(f"\n[{status}] {r['check_name']}")
        print(f"  {r['detail']}")

    # Before/After 결과가 서로 덮어쓰지 않도록 대상별 파일로 저장
    output_path = os.path.join(os.path.dirname(__file__), '..', 'report', f'latest_{args.target}.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n결과가 저장되었습니다: {os.path.abspath(output_path)}")