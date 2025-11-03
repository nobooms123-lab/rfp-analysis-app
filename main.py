# main.py
import streamlit as st
from utils import (
    extract_text_from_file, create_vector_db, extract_project_summary,
    generate_risk_report, generate_ksf_report, generate_outline_report,
    refine_report_with_chat, parse_report_items
)

st.set_page_config(page_title="대화형 RFP 분석/전략 수립", layout="wide")
st.title("대화형 RFP 분석 및 제안 전략 수립 🚀")

# --- 세션 상태 초기화 (lock_states 제거) ---
if 'stage' not in st.session_state:
    st.session_state.stage = 0
if "reports" not in st.session_state:
    st.session_state.reports = {}
if "active_tab_key" not in st.session_state:
    st.session_state.active_tab_key = 'risk'

# --- 사이드바 ---
with st.sidebar:
    st.header("1. 문서 업로드")
    uploaded_file = st.file_uploader("PDF/TXT 파일", type=["pdf", "txt"], help="새로운 파일을 올리면 모든 분석이 초기화됩니다.")

    if uploaded_file and st.session_state.get("uploaded_filename") != uploaded_file.name:
        st.session_state.clear()
        st.session_state.uploaded_filename = uploaded_file.name
        
        raw_text, refined_text = extract_text_from_file(uploaded_file)
        
        if refined_text:
            st.session_state.raw_text = raw_text
            st.session_state.refined_text = refined_text
            st.session_state.source_file_type = uploaded_file.type
            
            st.session_state.vector_db = create_vector_db(st.session_state.refined_text)
            st.session_state.project_summary = extract_project_summary(st.session_state.vector_db)
            st.session_state.stage = 0
        st.rerun()

    if st.session_state.get("source_file_type") == "application/pdf" and st.session_state.get("raw_text"):
        st.download_button(
            label="📥 (참고용) OCR 원본 텍스트 다운로드",
            data=st.session_state.raw_text.encode('utf-8'),
            file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_extracted_raw.txt",
            mime="text/plain",
            help="AI가 자동으로 정제하기 전의, PDF에서 추출된 원본 텍스트입니다."
        )

    if st.session_state.get("project_summary"):
        with st.expander("사업 핵심 개요", expanded=True):
            st.markdown(st.session_state.project_summary)

    st.header("2. 분석 단계 실행")
    if st.session_state.get("vector_db"):
        if st.button("단계 1: 리스크 분석", disabled=(st.session_state.stage >= 1), type="primary"):
            st.session_state.reports['risk'] = generate_risk_report(st.session_state.vector_db)
            st.session_state.stage = 1
            st.session_state.active_tab_key = 'risk'
            st.rerun()

        if st.button("단계 2: 핵심 성공 요소 분석", disabled=(st.session_state.stage < 1 or st.session_state.stage >= 2), type="primary"):
            st.session_state.reports['ksf'] = generate_ksf_report(st.session_state.vector_db, st.session_state.reports['risk'])
            st.session_state.stage = 2
            st.session_state.active_tab_key = 'ksf'
            st.rerun()

        if st.button("단계 3: 제안 목차 생성", disabled=(st.session_state.stage < 2 or st.session_state.stage >= 3), type="primary"):
            st.session_state.reports['outline'] = generate_outline_report(
                st.session_state.vector_db,
                st.session_state.project_summary,
                st.session_state.reports['risk'],
                st.session_state.reports['ksf']
            )
            st.session_state.stage = 3
            st.session_state.active_tab_key = 'outline'
            st.rerun()

# --- 메인 화면 ---
if st.session_state.stage == 0:
    st.info("⬅️ 왼쪽 사이드바에서 문서를 업로드하고 분석 단계를 시작해주세요.")
else:
    left_col, right_col = st.columns([2, 3])
    report_options = {"risk": "📊 리스크 분석", "ksf": "🔑 KSF", "outline": "📑 목차"}
    available_keys = [k for i, k in enumerate(report_options.keys()) if st.session_state.stage > i]
    
    with right_col:
        st.header("📄 분석 보고서")
        if available_keys:
            st.radio(
                "표시할 보고서 선택:", options=available_keys,
                format_func=lambda k: report_options[k], key='active_tab_key',
                label_visibility="collapsed", horizontal=True,
            )
            active_key = st.session_state.active_tab_key
            report_text = st.session_state.reports.get(active_key, "")
            header, items = parse_report_items(report_text)
            
            if header:
                st.markdown(header)
                st.divider()

            # [수정됨] 체크박스 및 관련 UI 로직 완전 제거
            for item_text in items:
                st.markdown(item_text)
                st.divider()

    with left_col:
        st.header("✍️ 대화형 편집기")
        if available_keys:
            active_key = st.session_state.active_tab_key
            # [수정됨] 안내 메시지 변경
            st.info(f"현재 **'{report_options[active_key]}'** 보고서 **전체**를 대상으로 수정합니다.")
            
            if prompt := st.chat_input("수정 요청 사항을 입력하세요..."):
                original_report = st.session_state.reports.get(active_key, "")
                
                # [수정됨] 잠금/해제 로직 제거, 보고서 전체를 수정하도록 변경
                with st.spinner("보고서 전체를 수정 중입니다..."):
                    new_full_report = refine_report_with_chat(
                        st.session_state.vector_db, original_report, prompt
                    )
                    st.session_state.reports[active_key] = new_full_report
                    st.success(f"'{report_options[active_key]}' 보고서를 수정했습니다.")
                    st.rerun()
        else:
            st.info("먼저 분석 단계를 실행하여 수정할 보고서를 생성해주세요.")
