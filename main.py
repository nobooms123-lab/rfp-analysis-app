# main.py
import streamlit as st
import json
# 아래 라인의 오타를 수정했습니다.
from utils import get_vector_db, extract_facts, generate_strategic_report, generate_creative_reports, to_excel

# --- 1. 기본 설정 및 초기화 ---
st.set_page_config(page_title="RFP 전략 분석 AI", layout="wide")
st.title("RFP 전략 분석 및 제안서 작성 도우미")

if 'stage' not in st.session_state:
    st.session_state.stage = 0 # 0: 초기, 1: 텍스트/사실추출 완료, 2: 전략보고서 완료, 3: 전체완료

# --- 2. 사이드바 구성 ---
st.sidebar.title("분석 프로세스")
uploaded_file = st.sidebar.file_uploader("1. 분석할 RFP PDF 파일 업로드", type="pdf")

if uploaded_file and st.session_state.get("uploaded_filename") != uploaded_file.name:
    st.session_state.clear()
    st.session_state.uploaded_filename = uploaded_file.name
    st.session_state.stage = 0

# --- 3. 단계별 실행 로직 ---
if uploaded_file and st.session_state.stage == 0:
    st.session_state.vector_db, st.session_state.ocr_text = get_vector_db(uploaded_file)
    if st.session_state.ocr_text:
        st.session_state.facts = extract_facts(st.session_state.ocr_text, run_id=uploaded_file.name)
        st.session_state.stage = 1
        st.rerun()

if st.session_state.stage >= 1:
    st.sidebar.success("✓ 1단계: 텍스트 및 핵심 정보 추출 완료")
    if st.sidebar.button("2. 전략 보고서 생성", disabled=(st.session_state.stage > 1)):
        report = generate_strategic_report(
            st.session_state.vector_db,
            st.session_state.facts,
            run_id=uploaded_file.name
        )
        if report:
            st.session_state.report = report
            st.session_state.stage = 2
            st.rerun()

if st.session_state.stage >= 2:
    st.sidebar.success("✓ 2단계: 전략 보고서 생성 완료")
    if st.sidebar.button("3. KSF 및 발표 목차 생성", disabled=(st.session_state.stage > 2)):
        # 'summary' 인자에는 이제 'report'를 전달합니다.
        ksf, outline = generate_creative_reports(st.session_state.vector_db, st.session_state.report, run_id=uploaded_file.name)
        if ksf and outline:
            st.session_state.ksf = ksf
            st.session_state.presentation_outline = outline
            st.session_state.stage = 3
            st.rerun()

if st.session_state.stage == 3:
    st.sidebar.success("✓ 3단계: 모든 분석 완료!")

# --- 4. 메인 화면 UI 렌더링 ---
if st.session_state.stage == 0:
    st.info("사이드바에서 RFP PDF 파일을 업로드하면 분석이 시작됩니다.")

if 'facts' in st.session_state and st.session_state.facts:
    with st.expander("📊 프로젝트 개요 (AI 자동 추출)", expanded=True):
        facts = st.session_state.facts
        col1, col2 = st.columns(2)
        col1.metric("사업명", facts.get("project_name", "N/A"))
        col2.metric("사업 예산", facts.get("project_budget", "N/A"))
        col1.metric("사업 기간", facts.get("project_duration", "N/A"))
        st.markdown("**추진 배경**")
        st.info(facts.get("project_background", "N/A"))

tabs = st.tabs(["전략 보고서", "핵심 성공 요소", "발표자료 목차", "OCR 원본 텍스트"])

with tabs[0]:
    if 'report' in st.session_state:
        st.markdown(st.session_state.report)
    else:
        st.info("2단계 '전략 보고서 생성'을 실행해주세요.")

with tabs[1]:
    if 'ksf' in st.session_state:
        st.markdown(st.session_state.ksf)
    else:
        st.info("3단계 'KSF 및 발표 목차 생성'을 실행해주세요.")

with tabs[2]:
    if 'presentation_outline' in st.session_state:
        st.markdown(st.session_state.presentation_outline)
    else:
        st.info("3단계 'KSF 및 발표 목차 생성'을 실행해주세요.")

with tabs[3]:
    if 'ocr_text' in st.session_state:
        st.text_area("추출된 전체 텍스트", st.session_state.ocr_text, height=400)
    else:
        st.info("PDF 파일을 먼저 업로드해주세요.")

if st.session_state.stage == 3:
    st.sidebar.header("결과 다운로드")
    excel_data = to_excel(
        st.session_state.facts,
        st.session_state.report,
        st.session_state.ksf,
        st.session_state.presentation_outline
    )
    st.sidebar.download_button(
        label="📥 전체 결과 Excel 다운로드",
        data=excel_data,
        file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
