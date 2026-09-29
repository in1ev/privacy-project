import subprocess
import json

# 이번 프로젝트에서 의도적으로 취약 버전을 고정한 핵심 패키지
TARGET_PACKAGES = {'flask', 'jinja2', 'werkzeug'}


def check_known_vulnerabilities():
    """
    [결함5 진단] pip-audit을 실행하여 flask/jinja2/werkzeug에
    알려진 취약점이 존재하는지 확인한다.

    pip/nltk 등 프로젝트 핵심 대상이 아닌 패키지의 결과는
    부가 발견사항으로 별도 집계한다.
    """
    result = {
        "check_name": "패치 미적용 (결함5)",
        "target": "flask, jinja2, werkzeug",
        "passed": None,
        "detail": "",
        "core_findings": [],
        "additional_findings": []
    }

    try:
        proc = subprocess.run(
            ["pip-audit", "--format", "json"],
            capture_output=True, text=True, timeout=60
        )
        data = json.loads(proc.stdout)

        for dependency in data.get("dependencies", []):
            pkg_name = dependency["name"].lower()
            vulns = dependency.get("vulns", [])
            if not vulns:
                continue

            for v in vulns:
                finding = f"{pkg_name} {dependency['version']}: {v['id']}"
                if pkg_name in TARGET_PACKAGES:
                    result["core_findings"].append(finding)
                else:
                    result["additional_findings"].append(finding)

        if result["core_findings"]:
            result["passed"] = False
            result["detail"] = f"핵심 대상 패키지에서 {len(result['core_findings'])}건의 취약점 발견"
        else:
            result["passed"] = True
            result["detail"] = "핵심 대상 패키지(flask/jinja2/werkzeug)에서 취약점 미발견"

    except FileNotFoundError:
        result["detail"] = "pip-audit이 설치되어 있지 않음"
    except Exception as e:
        result["detail"] = f"실행 중 오류: {str(e)}"

    return result


if __name__ == '__main__':
    result = check_known_vulnerabilities()
    print(json.dumps(result, indent=2, ensure_ascii=False))