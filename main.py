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
if "reports" not in st.session_state:
    st.session_state.reports = {} # 각 단계별 '최종' 보고서 내용을 저장
if "editor_messages" not in st.session_state:
    st.session_state.editor_messages = [] # 왼쪽 편집기 채팅 기록

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

    st.header("2. 분석 단계 실행")
    if st.session_state.get("vector_db"):
        if st.button("단계 1: 리스크 분석", disabled=(st.session_state.stage >= 1), type="primary"):
            report = generate_risk_report(st.session_state.vector_db)
            st.session_state.reports['risk'] = report
            st.session_state.stage = 1
            st.rerun()

        if st.button("단계 2: 핵심 성공 요소 분석", disabled=(st.session_state.stage < 1 or st.session_state.stage >= 2), type="primary"):
            final_risk_report = st.session_state.reports['risk']
            report = generate_ksf_report(st.session_state.vector_db, final_risk_report)
            st.session_state.reports['ksf'] = report
            st.session_state.stage = 2
            st.rerun()
            
        if st.button("단계 3: 제안 목차 생성", disabled=(st.session_state.stage < 2 or st.session_state.stage >= 3), type="primary"):
            final_risk_report = st.session_state.reports['risk']
            final_ksf_report = st.session_state.reports['ksf']
            report = generate_outline_report(st.session_state.vector_db, final_risk_report, final_ksf_report)
            st.session_state.reports['outline'] = report
            st.session_state.stage = 3
            st.rerun()

# --- 메인 화면 ---
if st.session_state.stage == 0:
    st.info("⬅️ 왼쪽 사이드바에서 문서를 업로드하고 분석 단계를 시작해주세요.")
else:
    # 2단 레이아웃 생성
    left_col, right_col = st.columns([2, 3]) # 왼쪽 40%, 오른쪽 60%

    # --- 오른쪽: 보고서 뷰어 ---
    with right_col:
        st.header("📄 분석 보고서")
        
        tab_titles = []
        if st.session_state.stage >= 1: tab_titles.append("📊 리스크 분석")
        if st.session_state.stage >= 2: tab_titles.append("🔑 핵심 성공 요소 (KSF)")
        if st.session_state.stage >= 3: tab_titles.append("📑 제안 발표 목차")
        
        if tab_titles:
            tabs = st.tabs(tab_titles)
            if st.session_state.stage >= 1:
                with tabs[0]:
                    st.markdown(st.session_state.reports.get('risk', "오류: 리스크 보고서를 찾을 수 없습니다."))
            if st.session_state.stage >= 2:
                with tabs[1]:
                    st.markdown(st.session_state.reports.get('ksf', "오류: KSF 보고서를 찾을 수 없습니다."))
            if st.session_state.stage >= 3:
                with tabs[2]:
                    st.markdown(st.session_state.reports.get('outline', "오류: 목차 보고서를 찾을 수 없습니다."))

    # --- 왼쪽: 수정 컨트롤러 ---
    with left_col:
        st.header("✍️ 대화형 편집기")
        
        # 수정 대상 선택
        report_options = {
            "risk": "리스크 분석",
            "ksf": "핵심 성공 요소 (KSF)",
            "outline": "제안 발표 목차"
        }
        available_options = {k: v for i, (k, v) in enumerate(report_options.items()) if st.session_state.stage > i}
        
        if available_options:
            active_report_key = st.radio(
                "수정할 보고서를 선택하세요:",
                options=available_options.keys(),
                format_func=lambda k: available_options[k],
                key='active_editor'
            )

            # 편집기 채팅 기록 표시
            for message in st.session_state.editor_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # 사용자 채팅 입력
            if prompt := st.chat_input("수정 요청 사항을 입력하세요..."):
                # 1. 사용자 요청을 채팅 기록에 추가
                st.session_state.editor_messages.append({"role": "user", "content": prompt})

                # 2. AI에게 수정 작업 요청
                with st.spinner("보고서를 수정 중입니다..."):
                    current_report = st.session_state.reports[active_report_key]
                    updated_report = refine_report_with_chat(st.session_state.vector_db, current_report, prompt)
                    
                    # 3. 수정된 보고서를 세션 상태에 업데이트
                    st.session_state.reports[active_report_key] = updated_report
                
                # 4. 편집기 채팅에 확인 메시지 추가
                st.session_state.editor_messages.append({
                    "role": "assistant", 
                    "content": f"✅ **{available_options[active_report_key]}** 보고서를 수정했습니다. 오른쪽 화면에서 변경사항을 확인하세요."
                })
                
                # 5. 화면 전체를 새로고침하여 오른쪽 뷰어에 변경사항 반영
                st.rerun()
        else:
            st.info("먼저 분석 단계를 실행하여 수정할 보고서를 생성해주세요.")

