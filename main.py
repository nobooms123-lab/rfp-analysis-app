# main.py
import streamlit as st
from utils import (
    extract_text_from_file, create_vector_db, extract_project_summary,
    generate_risk_report, generate_ksf_report, generate_outline_report,
    refine_report_with_chat, parse_report_items
)

st.set_page_config(page_title="대화형 RFP 분석/전략 수립", layout="wide")
st.title("대화형 RFP 분석 및 제안 전략 수립 🚀")

# --- 세션 상태 초기화 ---
if 'stage' not in st.session_state:
    st.session_state.stage = 0
if "reports" not in st.session_state:
    st.session_state.reports = {}
if "editor_messages" not in st.session_state:
    st.session_state.editor_messages = []
if "active_tab_key" not in st.session_state:
    st.session_state.active_tab_key = 'risk'
if "lock_states" not in st.session_state:
    st.session_state.lock_states = {"risk": {}, "ksf": {}, "outline": {}}

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
            report_text = generate_risk_report(st.session_state.vector_db)
            st.session_state.reports['risk'] = report_text
            # [수정] 리스크 보고서 생성 시 잠금 상태를 명시적으로 초기화
            _, items = parse_report_items(report_text)
            st.session_state.lock_states['risk'] = {i+1: False for i in range(len(items))}
            st.session_state.stage = 1
            st.session_state.active_tab_key = 'risk'
            st.rerun()

        if st.button("단계 2: 핵심 성공 요소 분석", disabled=(st.session_state.stage < 1 or st.session_state.stage >= 2), type="primary"):
            report_text = generate_ksf_report(st.session_state.vector_db, st.session_state.reports['risk'])
            st.session_state.reports['ksf'] = report_text
            # [수정] KSF 보고서 생성 시 잠금 상태를 명시적으로 초기화
            _, items = parse_report_items(report_text)
            st.session_state.lock_states['ksf'] = {i+1: False for i in range(len(items))}
            st.session_state.stage = 2
            st.session_state.active_tab_key = 'ksf'
            st.rerun()

        if st.button("단계 3: 제안 목차 생성", disabled=(st.session_state.stage < 2 or st.session_state.stage >= 3), type="primary"):
            report_text = generate_outline_report(
                st.session_state.vector_db,
                st.session_state.project_summary,
                st.session_state.reports['risk'],
                st.session_state.reports['ksf']
            )
            st.session_state.reports['outline'] = report_text
            # [수정] 목차 보고서 생성 시 잠금 상태를 명시적으로 초기화
            _, items = parse_report_items(report_text)
            st.session_state.lock_states['outline'] = {i+1: False for i in range(len(items))}
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

            for i, item_text in enumerate(items):
                item_id = i + 1
                # [수정] value를 세션 상태에서 직접 읽어오도록 변경 (get의 기본값 의존도 감소)
                is_locked = st.checkbox(
                    f"항목 {item_id} 잠금",
                    key=f"lock_{active_key}_{item_id}",
                    value=st.session_state.lock_states[active_key].get(item_id, False)
                )
                st.session_state.lock_states[active_key][item_id] = is_locked
                
                if is_locked:
                    st.markdown(f"<div style='background-color:#f0f2f6; padding: 10px; border-radius: 5px;'>{item_text}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(item_text)
                st.divider()

    with left_col:
        st.header("✍️ 대화형 편집기")
        if available_keys:
            active_key = st.session_state.active_tab_key
            st.info(f"현재 **'{report_options[active_key]}'** 보고서의 **잠금 해제된 항목**을 수정합니다.")
            
            if prompt := st.chat_input("수정 요청 사항을 입력하세요..."):
                header, items = parse_report_items(st.session_state.reports.get(active_key, ""))
                
                # [수정] 잠금/해제 항목을 결정하는 로직을 더 명확하게 변경
                current_lock_states = st.session_state.lock_states[active_key]
                locked_items = [text for i, text in enumerate(items) if current_lock_states.get(i + 1, False)]
                unlocked_items = [text for i, text in enumerate(items) if not current_lock_states.get(i + 1, False)]

                if not unlocked_items:
                    st.warning("수정할 항목이 없습니다. 최소 하나 이상의 항목을 잠금 해제해주세요.")
                else:
                    with st.spinner("선택된 항목을 수정 중입니다..."):
                        updated_unlocked_text = refine_report_with_chat(
                            st.session_state.vector_db, locked_items, unlocked_items, prompt
                        )
                        _, updated_unlocked_items = parse_report_items("\n" + updated_unlocked_text)
                        
                        new_report_items = []
                        unlocked_idx = 0
                        for i in range(len(items)):
                            item_id = i + 1
                            if current_lock_states.get(item_id, False):
                                new_report_items.append(items[i])
                            else:
                                if unlocked_idx < len(updated_unlocked_items):
                                    new_report_items.append(updated_unlocked_items[unlocked_idx])
                                    unlocked_idx += 1
                                else:
                                    new_report_items.append(items[i]) 
                        
                        final_report = header + "\n\n" + "\n\n".join(new_report_items)
                        st.session_state.reports[active_key] = final_report
                        st.success(f"'{report_options[active_key]}' 보고서를 수정했습니다.")
                        st.rerun()
        else:
            st.info("먼저 분석 단계를 실행하여 수정할 보고서를 생성해주세요.")


