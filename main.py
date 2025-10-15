# main.py

import streamlit as st
import json
from utils import (
    process_pdf_file,
    process_text_file,
    refine_rfp_text,
    extract_facts,
    generate_strategic_report,
    generate_creative_reports,
    to_excel
)

# --- 1. 기본 설정 및 초기화 ---
st.set_page_config(page_title="RFP 전략 분석 AI", layout="wide")
st.title("RFP 전략 분석 및 제안서 작성 도우미")

if 'stage' not in st.session_state:
    st.session_state.stage = 0

# --- 2. 사이드바 구성 ---
st.sidebar.title("분석 프로세스")

# [기능 추가] 시작점 선택 UI
start_point = st.sidebar.radio(
    "분석 시작점을 선택하세요:",
    ("RFP 원본 파일로 시작", "정제된 텍스트로 시작"),
    key="start_point_selector"
)

# --- 3. 단계별 실행 로직 ---

# 워크플로우 1: RFP 원본 파일로 시작
if start_point == "RFP 원본 파일로 시작":
    st.sidebar.header("1. 원본 파일 업로드")
    file_type = st.sidebar.radio("파일 유형 선택:", ('PDF', 'TXT'), key="file_type_selector")

    if file_type == 'PDF':
        uploaded_file = st.sidebar.file_uploader("RFP PDF 파일 업로드", type="pdf", key="rfp_uploader")
    else:
        uploaded_file = st.sidebar.file_uploader("텍스트 파일(.txt) 업로드", type="txt", key="rfp_uploader")

    if uploaded_file and st.session_state.get("uploaded_filename") != uploaded_file.name:
        st.session_state.clear()
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.stage = 0

    if uploaded_file and st.session_state.stage == 0:
        full_text = None
        with st.spinner(f"{file_type} 파일에서 텍스트를 추출하는 중..."):
            if file_type == 'PDF':
                full_text = process_pdf_file(uploaded_file)
            else:
                full_text = process_text_file(uploaded_file)
        
        if full_text:
            st.session_state.raw_text = full_text
            st.session_state.stage = 1
            st.rerun()

# 워크플로우 2: 정제된 텍스트로 시작
else:
    st.sidebar.header("1. 정제된 텍스트 업로드")
    refined_file = st.sidebar.file_uploader("수정했거나 다운로드한 정제된 텍스트(.txt) 파일 업로드", type="txt", key="refined_uploader")

    if refined_file and st.session_state.get("uploaded_filename") != refined_file.name:
        st.session_state.clear()
        st.session_state.uploaded_filename = refined_file.name
        st.session_state.stage = 0 # 초기화 후 바로 stage 2로 점프

    if refined_file and st.session_state.stage == 0:
        with st.spinner("정제된 텍스트 파일을 읽는 중..."):
            refined_text = process_text_file(refined_file)
            if refined_text:
                st.session_state.refined_text = refined_text
                # 원본 텍스트는 없으므로 안내 문구 저장
                st.session_state.raw_text = "정제된 텍스트로 시작하여 원본 텍스트가 없습니다."
                st.session_state.stage = 2 # 바로 2단계로 설정
                st.rerun()

# --- 공통 실행 단계 (버튼 기반) ---

# 단계 2: AI 텍스트 정제 (원본 파일로 시작했을 때만 보임)
if st.session_state.stage == 1:
    st.sidebar.header("2. AI 텍스트 정제")
    if st.sidebar.button("RFP 핵심내용 정제 실행"):
        refined_text = refine_rfp_text(st.session_state.raw_text, run_id=st.session_state.uploaded_filename)
        if refined_text:
            st.session_state.refined_text = refined_text
            st.session_state.stage = 2
            st.rerun()

# 단계 3: 핵심 정보 추출
if st.session_state.stage >= 2:
    if st.session_state.stage == 2:
        st.sidebar.success("✓ 텍스트 준비 완료")
    st.sidebar.header("3. 프로젝트 개요 추출")
    if st.sidebar.button("핵심 정보 추출 실행", disabled=(st.session_state.stage > 2)):
        facts = extract_facts(st.session_state.refined_text, run_id=st.session_state.uploaded_filename)
        if facts:
            st.session_state.facts = facts
            st.session_state.stage = 3
            st.rerun()

# 단계 4: 전략 보고서 생성
if st.session_state.stage >= 3:
    st.sidebar.success("✓ 3. 개요 추출 완료")
    st.sidebar.header("4. 전략 보고서 생성")
    if st.sidebar.button("전략 보고서 생성 실행", disabled=(st.session_state.stage > 3)):
        report = generate_strategic_report(
            st.session_state.refined_text, st.session_state.facts, run_id=st.session_state.uploaded_filename
        )
        if report:
            st.session_state.report = report
            st.session_state.stage = 4
            st.rerun()

# 단계 5: KSF 및 발표 목차 생성
if st.session_state.stage >= 4:
    st.sidebar.success("✓ 4. 전략 보고서 완료")
    st.sidebar.header("5. KSF 및 목차 생성")
    if st.sidebar.button("KSF 및 발표 목차 생성 실행", disabled=(st.session_state.stage > 4)):
        ksf, outline = generate_creative_reports(
            st.session_state.refined_text, st.session_state.report, run_id=st.session_state.uploaded_filename
        )
        if ksf and outline:
            st.session_state.ksf = ksf
            st.session_state.presentation_outline = outline
            st.session_state.stage = 5
            st.rerun()

if st.session_state.stage == 5:
    st.sidebar.success("✓ 5. 모든 분석 완료!")

# --- 4. 메인 화면 UI 렌더링 ---
if st.session_state.stage == 0:
    st.info("사이드바에서 시작점을 선택하고 파일을 업로드하면 분석이 시작됩니다.")

if st.session_state.stage >= 3:
    with st.expander("📊 프로젝트 개요 (AI 자동 추출)", expanded=True):
        facts = st.session_state.facts
        col1, col2 = st.columns(2)
        col1.metric("사업명", facts.get("project_name", "N/A"))
        col2.metric("사업 예산", facts.get("project_budget", "N/A"))
        col1.metric("사업 기간", facts.get("project_duration", "N/A"))
        st.markdown("**추진 배경**")
        st.info(facts.get("project_background", "N/A"))

tabs = st.tabs(["전략 보고서", "핵심 성공 요소", "발표자료 목차", "AI 정제 텍스트", "업로드 원본 텍스트"])

with tabs[0]:
    if 'report' in st.session_state: st.markdown(st.session_state.report)
    else: st.info("사이드바의 '4. 전략 보고서 생성'을 실행해주세요.")
with tabs[1]:
    if 'ksf' in st.session_state: st.markdown(st.session_state.ksf)
    else: st.info("사이드바의 '5. KSF 및 목차 생성'을 실행해주세요.")
with tabs[2]:
    if 'presentation_outline' in st.session_state: st.markdown(st.session_state.presentation_outline)
    else: st.info("사이드바의 '5. KSF 및 목차 생성'을 실행해주세요.")
with tabs[3]:
    if 'refined_text' in st.session_state: 
        st.text_area("AI가 핵심만 추출한 텍스트", st.session_state.refined_text, height=400)
        # [기능 추가] 정제된 텍스트 다운로드 버튼
        st.download_button(
            label="📥 정제된 텍스트 다운로드 (.txt)",
            data=st.session_state.refined_text.encode('utf-8'),
            file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_refined.txt",
            mime="text/plain"
        )
    else: st.info("사이드바에서 텍스트 정제를 실행하거나, 정제된 텍스트를 업로드해주세요.")
with tabs[4]:
    if 'raw_text' in st.session_state: st.text_area("업로드한 파일의 전체 텍스트", st.session_state.raw_text, height=400)
    else: st.info("파일을 먼저 업로드해주세요.")

if st.session_state.stage == 5:
    st.sidebar.header("결과 다운로드")
    excel_data = to_excel(
        st.session_state.facts, st.session_state.report, st.session_state.ksf, st.session_state.presentation_outline
    )
    st.sidebar.download_button(
        label="📥 전체 결과 Excel 다운로드",
        data=excel_data,
        file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

