# main.py
import streamlit as st
import json
import re
from utils import generate_initial_results, handle_chat_interaction, to_excel

# --- 1. 기본 설정 및 페이지 구성 ---
st.set_page_config(page_title="대화형 제안서 분석 도우미", layout="wide")
st.title("대화형 제안서 분석 및 편집 도우미")

# --- 2. 사이드바 구성 ---
st.sidebar.title("설정")
if "OPENAI_GPT_API_KEY" not in st.secrets or not st.secrets["OPENAI_GPT_API_KEY"].startswith('sk-'):
    st.sidebar.error("OpenAI API 키를 .streamlit/secrets.toml에 설정해주세요.")
    st.stop()
st.sidebar.success("API 키 로드 성공")
uploaded_file = st.sidebar.file_uploader("분석할 RFP PDF 파일 업로드", type="pdf")

# --- 3. 핵심 로직: 파일 처리 및 초기 분석 (한번에 실행) ---
if uploaded_file:
    if st.session_state.get("uploaded_filename") != uploaded_file.name:
        st.session_state.clear()
        st.session_state.uploaded_filename = uploaded_file.name

    if "summary" not in st.session_state:
        with st.spinner("AI가 PDF를 분석하고 초기 보고서를 생성 중입니다... (시간이 걸릴 수 있습니다)"):
            summary, ksf, outline, vector_db = generate_initial_results(uploaded_file)
            
            if summary and ksf and outline and vector_db:
                st.session_state.summary = summary
                st.session_state.ksf = ksf
                st.session_state.presentation_outline = outline
                st.session_state.vector_db = vector_db # 생성된 DB를 세션에 저장
                st.session_state.messages = []
                st.sidebar.success("초기 분석이 완료되었습니다!")
                st.rerun()
            else:
                st.error("분석 중 오류가 발생했습니다. 파일을 다시 확인하거나 다른 파일로 시도해주세요.")
                st.stop()
else:
    st.info("사이드바에서 RFP PDF 파일을 업로드하면 분석이 시작됩니다.")
    st.session_state.clear()

# --- 4. 메인 화면 UI 렌더링 (결과 생성 후) ---
if "summary" in st.session_state:
    col_chat, col_results = st.columns([2, 3])
    
    with col_results:
        st.subheader("최종 결과물")
        excel_data = to_excel(st.session_state.summary, st.session_state.ksf, st.session_state.presentation_outline)
        st.download_button(
            label="📥 전체 결과 Excel로 다운로드", data=excel_data,
            file_name=f"{uploaded_file.name.split('.')[0]}_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        tab1, tab2, tab3 = st.tabs(["제안서 요약", "핵심 성공 요소", "발표자료 목차"])
        with tab1: st.markdown(st.session_state.summary)
        with tab2: st.markdown(st.session_state.ksf)
        with tab3: st.markdown(st.session_state.presentation_outline)

    with col_chat:
        st.subheader("질의 및 수정 요청")
        for message in st.session_state.get("messages", []):
            with st.chat_message(message["role"]): st.markdown(message["content"])
        
        if user_prompt := st.chat_input("수정할 내용을 입력하세요..."):
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"): st.markdown(user_prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("요청을 분석하고 문서를 수정하는 중..."):
                    response_text = handle_chat_interaction(
                        user_prompt, st.session_state.vector_db, st.session_state.summary,
                        st.session_state.ksf, st.session_state.presentation_outline
                    )
                    try:
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if not json_match: raise ValueError("응답에서 JSON 객체를 찾을 수 없음")
                        response_data = json.loads(json_match.group(0))
                        target = response_data["target_section"]
                        valid_targets = ["summary", "ksf", "presentation_outline"]
                        if target not in valid_targets: raise ValueError(f"잘못된 수정 대상: {target}")
                        st.session_state[target] = response_data["new_content"]
                        success_message = f"✅ **'{target.upper()}'** 섹션이 업데이트되었습니다."
                        st.markdown(success_message)
                        st.session_state.messages.append({"role": "assistant", "content": success_message})
                        st.rerun()
                    except Exception as e:
                        error_message = f"응답 처리 오류: {e}\n\nAI 응답: {response_text}"
                        st.error(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
