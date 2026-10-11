import streamlit as st

from config import Target, DEFAULT_TARGET
from run_diagnosis import run_all_diagnostics

st.set_page_config(page_title="개인정보보호 진단 대시보드", page_icon="🛡️", layout="wide")

st.title("한빛마켓 · 한빛페이 개인정보보호 진단")
st.caption("ISMS-P 인증심사 반복 결함 5종 자동 탐지")

# ---------- 사이드바: 진단 대상 ----------
with st.sidebar:
    st.header("진단 대상")
    market_url = st.text_input("한빛마켓 URL", DEFAULT_TARGET.market_url)
    pay_url = st.text_input("한빛페이 URL", DEFAULT_TARGET.pay_url)
    market_db = st.text_input("market.db 경로", DEFAULT_TARGET.market_db_path)
    label = st.selectbox("진단 대상 버전 (표기용)", ["Before", "After"])
    st.warning(
        "본인이 소유·관리하는 시스템에만 실행하세요. "
        "결함3 진단은 대상 한빛페이에 테스트 계정을 실제로 생성합니다."
    )

# ---------- 진단 실행 ----------
if st.button("진단 실행", type="primary"):
    target = Target("custom", market_url, pay_url, market_db)
    try:
        with st.spinner("진단 실행 중... (패치 점검은 수십 초 걸릴 수 있습니다)"):
            st.session_state["summary"] = run_all_diagnostics(target)
            st.session_state["label"] = label
    except Exception as e:
        st.error(f"진단 실행 중 오류: {e}")

# ---------- 결과 표시 ----------
summary = st.session_state.get("summary")

if summary is None:
    st.info("한빛마켓(5000)·한빛페이(5001) 서버를 켠 뒤 '진단 실행'을 눌러주세요.")
else:
    results = summary["results"]
    n_pass = sum(1 for r in results if r["passed"] is True)
    n_fail = sum(1 for r in results if r["passed"] is False)
    n_unknown = len(results) - n_pass - n_fail

    st.subheader(f"진단 결과 · {st.session_state['label']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("전체 항목", len(results))
    m2.metric("통과", n_pass)
    m3.metric("결함 발견", n_fail)
    m4.metric("확인 불가", n_unknown)

    st.divider()

    cols = st.columns(3)
    for i, r in enumerate(results):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{r['check_name']}**")
                if r["passed"] is True:
                    st.success("통과")
                elif r["passed"] is False:
                    st.error("결함 발견")
                else:
                    st.warning("확인 불가")
                st.write(r["detail"])
                with st.expander("상세 결과 (JSON)"):
                    st.json(r)