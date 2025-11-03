# main.py

import streamlit as st
from utils import (
    extract_text_from_file, create_vector_db,
    generate_risk_report, generate_ksf_report, generate_outline_report,
    refine_report_with_chat
)

st.set_page_config(page_title="대화형 RFP 분석/전략 수립", layout="wide")
st.title("대화형 RFP 분석 및 제안 전략 수립 🚀")

# --- 세션 상태 초기화 ---
if 'stage' not in st.session_state:
    st.session_state.stage = 0 # 0:준비, 1:리스크, 2:KSF, 3:목차
if "messages" not in st.session_state:
    st.session_state.messages = {} # 각 단계별 채팅 기록을 저장할 딕셔너리

# --- 사이드바 ---
with st.sidebar:
    st.header("1. 문서 업로드")
    uploaded_file = st.file_uploader("PDF/TXT 파일", type=["pdf", "txt"], help="새로운 파일을 올리면 모든 분석이 초기화됩니다.")

    if uploaded_file and st.session_state.get("uploaded_filename") != uploaded_file.name:
        st.session_state.clear()
        st.session_state.uploaded_filename = uploaded_file.name
        raw_text = extract_text_from_file(uploaded_file)
        if raw_text:
            st.session_state.vector_db = create_vector_db(raw_text)
            st.session_state.stage = 0
            st.rerun()

    # --- 단계별 실행 버튼 ---
    st.header("2. 분석 단계 실행")
    if st.session_state.get("vector_db"):
        if st.button("단계 1: 리스크 분석", disabled=(st.session_state.stage >= 1), type="primary"):
            report = generate_risk_report(st.session_state.vector_db)
            st.session_state.risk_report = report
            st.session_state.messages['risk'] = [{"role": "assistant", "content": report}]
            st.session_state.stage = 1
            st.rerun()

        if st.button("단계 2: 핵심 성공 요소 분석", disabled=(st.session_state.stage < 1 or st.session_state.stage >= 2), type="primary"):
            final_risk_report = st.session_state.messages['risk'][-1]['content']
            # KSF 분석 시에는 리스크 보고서를 직접 사용하지 않지만, 순서는 중요
            report = generate_ksf_report(st.session_state.vector_db)
            st.session_state.ksf_report = report
            st.session_state.messages['ksf'] = [{"role": "assistant", "content": report}]
            st.session_state.stage = 2
            st.rerun()
            
        if st.button("단계 3: 제안 목차 생성", disabled=(st.session_state.stage < 2 or st.session_state.stage >= 3), type="primary"):
            final_ksf_report = st.session_state.messages['ksf'][-1]['content']
            report = generate_outline_report(st.session_state.vector_db, final_ksf_report)
            st.session_state.outline_report = report
            st.session_state.messages['outline'] = [{"role": "assistant", "content": report}]
            st.session_state.stage = 3
            st.rerun()

# --- 메인 화면 ---
if st.session_state.stage == 0:
    st.info("⬅️ 왼쪽 사이드바에서 문서를 업로드하고 분석 단계를 시작해주세요.")

# 범용 채팅 및 결과 표시 함수
def display_report_and_chat(report_key, title):
    st.header(title)
    
    # 채팅 기록 표시
    if st.session_state.messages.get(report_key):
        for message in st.session_state.messages[report_key]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # 사용자 입력
    if prompt := st.chat_input(f"'{title}' 결과 수정 요청..."):
        # 현재 보고서 내용을 컨텍스트로 사용 (항상 마지막 AI 답변 기준)
        current_report = st.session_state.messages[report_key][-1]['content']
        
        st.session_state.messages[report_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("보고서를 수정 중입니다..."):
                response = refine_report_with_chat(st.session_state.vector_db, current_report, prompt)
                st.markdown(response)
        
        st.session_state.messages[report_key].append({"role": "assistant", "content": response})
        # 최종 수정된 내용을 해당 보고서의 메인 변수에도 업데이트
        st.session_state[f"{report_key}_report"] = response
        st.rerun()

# 단계별 탭 생성 및 콘텐츠 표시
if st.session_state.stage >= 1:
    tab_titles = ["📊 리스크 분석"]
    if st.session_state.stage >= 2:
        tab_titles.append("🔑 핵심 성공 요소 (KSF)")
    if st.session_state.stage >= 3:
        tab_titles.append("📑 제안 발표 목차")
    
    tabs = st.tabs(tab_titles)
    
    with tabs[0]:
        display_report_and_chat('risk', "사업 도전 과제 및 관리 전략")
    
    if st.session_state.stage >= 2:
        with tabs[1]:
            display_report_and_chat('ksf', "핵심 성공 요소 및 차별화 전략")
            
    if st.session_state.stage >= 3:
        with tabs[2]:
            display_report_and_chat('outline', "승리를 위한 제안 발표 스토리라인")
