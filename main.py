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
# [신규] 현재 활성화된 탭(뷰어/편집기 동기화용)을 관리하는 상태
if "active_tab_key" not in st.session_state:
    st.session_state.active_tab_key = 'risk'

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
            st.session_state.active_tab_key = 'risk' # [개선] 완료 시 활성 탭 지정
            st.rerun()

        if st.button("단계 2: 핵심 성공 요소 분석", disabled=(st.session_state.stage < 1 or st.session_state.stage >= 2), type="primary"):
            final_risk_report = st.session_state.reports['risk']
            report = generate_ksf_report(st.session_state.vector_db, final_risk_report)
            st.session_state.reports['ksf'] = report
            st.session_state.stage = 2
            st.session_state.active_tab_key = 'ksf' # [개선] 완료 시 활성 탭 지정
            st.rerun()
            
        if st.button("단계 3: 제안 목차 생성", disabled=(st.session_state.stage < 2 or st.session_state.stage >= 3), type="primary"):
            final_risk_report = st.session_state.reports['risk']
            final_ksf_report = st.session_state.reports['ksf']
            report = generate_outline_report(st.session_state.vector_db, final_risk_report, final_ksf_report)
            st.session_state.reports['outline'] = report
            st.session_state.stage = 3
            st.session_state.active_tab_key = 'outline' # [개선] 완료 시 활성 탭 지정
            st.rerun()

# --- 메인 화면 ---
if st.session_state.stage == 0:
    st.info("⬅️ 왼쪽 사이드바에서 문서를 업로드하고 분석 단계를 시작해주세요.")
else:
    # 2단 레이아웃 생성
    left_col, right_col = st.columns([2, 3])

    # 보고서 옵션 정의
    report_options = {
        "risk": "📊 리스크 분석",
        "ksf": "🔑 핵심 성공 요소 (KSF)",
        "outline": "📑 제안 발표 목차"
    }
    # 현재 단계까지 완료된 보고서만 옵션으로 표시
    available_keys = [k for i, k in enumerate(report_options.keys()) if st.session_state.stage > i]

    # --- 오른쪽: 보고서 뷰어 ---
    with right_col:
        st.header("📄 분석 보고서")
        
        if available_keys:
            # [개선] st.tabs 대신 st.radio를 사용하여 프로그래밍적으로 기본값 제어
            st.radio(
                "표시할 보고서 선택:",
                options=available_keys,
                format_func=lambda k: report_options[k],
                key='active_tab_key', # 이 key가 좌/우를 동기화하는 핵심
                label_visibility="collapsed",
                horizontal=True,
            )
            
            # 선택된 탭(라디오 버튼)에 따라 해당 보고서 내용 표시
            active_key = st.session_state.active_tab_key
            st.markdown(st.session_state.reports.get(active_key, f"오류: '{report_options[active_key]}' 보고서를 찾을 수 없습니다."))

    # --- 왼쪽: 수정 컨트롤러 ---
    with left_col:
        st.header("✍️ 대화형 편집기")
        
        if available_keys:
            # [개선] 현재 활성화된 보고서가 무엇인지 명시적으로 표시
            active_title = report_options[st.session_state.active_tab_key]
            st.info(f"현재 **'{active_title}'** 보고서를 편집하고 있습니다.")

            # 편집기 채팅 기록 표시
            for message in st.session_state.editor_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # 사용자 채팅 입력
            if prompt := st.chat_input("수정 요청 사항을 입력하세요..."):
                active_key = st.session_state.active_tab_key
                st.session_state.editor_messages.append({"role": "user", "content": prompt})

                with st.spinner("보고서를 수정 중입니다..."):
                    current_report = st.session_state.reports[active_key]
                    updated_report = refine_report_with_chat(st.session_state.vector_db, current_report, prompt)
                    st.session_state.reports[active_key] = updated_report
                
                st.session_state.editor_messages.append({
                    "role": "assistant", 
                    "content": f"✅ **{active_title}** 보고서를 수정했습니다."
                })
                
                st.rerun()
        else:
            st.info("먼저 분석 단계를 실행하여 수정할 보고서를 생성해주세요.")
