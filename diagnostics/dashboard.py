import json
import os
import socket
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from config import BEFORE_TARGET, AFTER_TARGET, BASE_DIR
from run_diagnosis import run_all_diagnostics

st.set_page_config(page_title="개인정보보호 진단 대시보드", page_icon="🛡️", layout="wide")

TARGETS = {"Before": BEFORE_TARGET, "After": AFTER_TARGET}
REPORT_DIR = os.path.join(BASE_DIR, "report")


def is_listening(url):
    """주소의 포트에 연결되는지만 확인한다. (HTTP 요청을 보내지 않아 접속기록이 쌓이지 않는다)"""
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=1.0):
            return True
    except OSError:
        return False


def status_label(passed):
    if passed is True:
        return "✅ 통과"
    if passed is False:
        return "❌ 결함 발견"
    return "⚠️ 확인 불가"


def measure(name):
    """대상 하나를 진단하고, 증빙용으로 report 폴더에 JSON으로도 저장한다."""
    summary = run_all_diagnostics(TARGETS[name])
    summary["measured_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, f"latest_{name.lower()}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary


# ---------- 사이드바: 대상과 준비 상태 ----------
with st.sidebar:
    st.header("진단 대상")
    for name, t in TARGETS.items():
        st.markdown(f"**{name}**")
        st.write(f"한빛마켓 `{t.market_url}` " + ("🟢 켜짐" if is_listening(t.market_url) else "🔴 꺼짐"))
        st.write(f"한빛페이 `{t.pay_url}` " + ("🟢 켜짐" if is_listening(t.pay_url) else "🔴 꺼짐"))
    st.button("상태 새로고침")

    st.divider()
    has_sync_key = bool(os.environ.get("HANBIT_SYNC_SECRET"))
    st.write("동기화 키: " + ("🟢 설정됨" if has_sync_key else "🔴 없음"))
    if not has_sync_key:
        st.caption("키가 없으면 결함3의 '정상 서명 요청·재전송 거부' 확인이 생략됩니다.")
    st.warning(
        "본인이 소유·관리하는 시스템에만 실행하세요. 진단은 대상에 테스트 계정을 실제로 생성합니다 "
        "(결함1·3 진단, Before에서는 결함 자체가 계정 생성으로 증명됩니다)."
    )

# ---------- 본문 ----------
st.title("한빛마켓 · 한빛페이 개인정보보호 진단")
st.caption("ISMS-P 인증심사 반복 결함 5종 자동 탐지 · 개선 전(Before)과 개선 후(After) 비교")

c1, c2, c3 = st.columns(3)
run_names = None
if c1.button("Before 진단"):
    run_names = ["Before"]
if c2.button("After 진단"):
    run_names = ["After"]
if c3.button("Before · After 비교 진단", type="primary"):
    run_names = ["Before", "After"]

if run_names:
    store = st.session_state.setdefault("results", {})
    for name in run_names:
        try:
            with st.spinner(f"{name} 진단 실행 중... (패치 점검은 수십 초 걸릴 수 있습니다)"):
                store[name] = measure(name)
        except Exception as e:
            st.error(f"{name} 진단 실행 중 오류: {e}")

results = st.session_state.get("results", {})
if not results:
    st.info("Before 서버(5000·5001)와 After 서버(5010·5011)를 켠 뒤 '비교 진단'을 눌러 주세요.")
    st.stop()

names = [n for n in ("Before", "After") if n in results]

# ---------- 요약 ----------
st.subheader("요약")
cols = st.columns(len(names))
for col, n in zip(cols, names):
    s = results[n]
    delta = None
    if n == "After" and "Before" in results:
        delta = f"{s['passed'] - results['Before']['passed']:+d} (Before 대비)"
    col.metric(f"{n} 통과", f"{s['passed']} / {s['total_checks']}", delta=delta)
    col.caption(f"결함 {s['failed']} · 확인 불가 {s['unknown']} · 측정 {s['measured_at']}")

# ---------- 결함별 비교표 ----------
st.subheader("결함별 결과")
reference = results[names[0]]["results"]
rows = []
for i, r in enumerate(reference):
    row = {"결함": r["check_name"]}
    for n in names:
        row[n] = status_label(results[n]["results"][i]["passed"])
    rows.append(row)
st.table(pd.DataFrame(rows).set_index("결함"))

# ---------- 통과 항목 수 ----------
if len(names) == 2:
    st.subheader("통과 항목 수")
    chart = pd.DataFrame(
        {"통과 항목 수": [results[n]["passed"] for n in names]},
        index=[f"{i + 1}. {n}" for i, n in enumerate(names)],
    )
    st.bar_chart(chart)

# ---------- 항목별 상세 ----------
st.subheader("항목별 상세")
for i, r in enumerate(reference):
    with st.expander(r["check_name"]):
        detail_cols = st.columns(len(names))
        for col, n in zip(detail_cols, names):
            item = results[n]["results"][i]
            with col:
                st.markdown(f"**{n}** · {status_label(item['passed'])}")
                st.write(item["detail"])
                st.json(item, expanded=False)

st.caption("측정 결과는 report/latest_before.json, latest_after.json에 저장됩니다.")