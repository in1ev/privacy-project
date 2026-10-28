import json
import os
import subprocess
import sys

from config import DEFAULT_TARGET

# 이번 프로젝트에서 취약 버전을 의도적으로 고정한 핵심 패키지
TARGET_PACKAGES = {'flask', 'jinja2', 'werkzeug'}


def check_known_vulnerabilities(target=DEFAULT_TARGET):
    """
    [결함5 진단] 대상 가상환경(target.env_path)에 설치된 패키지를
    pip-audit으로 검사하여, flask/jinja2/werkzeug에 알려진 취약점이 있는지 확인한다.

    pip 등 핵심 대상이 아닌 패키지의 결과는 부가 발견사항으로 별도 집계한다.
    """
    site_packages = os.path.join(target.env_path, 'Lib', 'site-packages')

    result = {
        "check_name": "패치 미적용 (결함5)",
        "target": site_packages,
        "passed": None,
        "detail": "",
        "core_versions": {},
        "core_findings": [],
        "additional_findings": []
    }

    if not os.path.isdir(site_packages):
        result["detail"] = f"검사 대상 가상환경을 찾을 수 없음: {site_packages}"
        return result

    try:
        # 현재 실행 중인 파이썬의 pip_audit 모듈을 사용 (PATH 설정에 의존하지 않음)
        proc = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--path", site_packages, "--format", "json"],
            capture_output=True, text=True, timeout=120
        )
    except FileNotFoundError:
        result["detail"] = "파이썬 실행 파일을 찾을 수 없음"
        return result
    except subprocess.TimeoutExpired:
        result["detail"] = "pip-audit 실행 시간 초과(120초)"
        return result

    # 주의: 취약점이 발견되면 pip-audit은 종료코드 1을 반환하지만 stdout의 JSON은 정상이다.
    # 따라서 종료코드가 아니라 stdout의 유무로 실행 성공 여부를 판단한다.
    if not proc.stdout.strip():
        result["detail"] = f"pip-audit 실행 실패: {proc.stderr.strip()[:200]}"
        return result

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result["detail"] = "pip-audit 출력(JSON)을 해석할 수 없음"
        return result

    for dependency in data.get("dependencies", []):
        pkg_name = dependency["name"].lower()

        if pkg_name in TARGET_PACKAGES:
            result["core_versions"][pkg_name] = dependency.get("version")

        for v in dependency.get("vulns", []):
            finding = f"{pkg_name} {dependency.get('version')}: {v['id']}"
            if pkg_name in TARGET_PACKAGES:
                result["core_findings"].append(finding)
            else:
                result["additional_findings"].append(finding)

    # 검사 경로가 잘못되어 핵심 패키지가 아예 안 보이면 '취약점 없음'으로 오판하지 않는다.
    missing = TARGET_PACKAGES - set(result["core_versions"])
    if missing:
        result["detail"] = f"검사 경로에서 핵심 패키지를 찾지 못함: {', '.join(sorted(missing))}"
        return result

    versions = ", ".join(f"{k} {v}" for k, v in sorted(result["core_versions"].items()))

    if result["core_findings"]:
        result["passed"] = False
        result["detail"] = f"핵심 패키지에서 {len(result['core_findings'])}건의 취약점 발견 ({versions})"
    else:
        result["passed"] = True
        result["detail"] = f"핵심 패키지에서 취약점 미발견 ({versions})"

    return result


if __name__ == '__main__':
    print(json.dumps(check_known_vulnerabilities(), indent=2, ensure_ascii=False))