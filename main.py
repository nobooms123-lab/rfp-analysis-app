# main.py (수정 완료)
import streamlit as st
import json
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document # Document 클래스 임포트
from utils import (
    extract_text_from_pdf, create_db_from_text,
    generate_summary, generate_ksf, generate_outline,
    handle_chat_interaction, to_excel
)

# --- 1. 기본 설정 및 페이지 구성 ---
st.set_page_config(page_title="단계별 제안서 분석 도우미", layout="wide")
st.title("단계별 제안서 분석 및 편집 도우미")

# --- 2. 사이드바 구성 ---
st.sidebar.title("설정")
if "OPENAI_GPT_API_KEY" not in st.secrets or not st.secrets["OPENAI_GPT_API_KEY"].startswith('sk-'):
    st.sidebar.error("OpenAI API 키를 .streamlit/secrets.toml에 설정해주세요.")
    st.stop()
st.sidebar.success("API 키 로드 성공")
uploaded_file = st.sidebar.file_uploader("분석할 RFP PDF 파일 업로드", type="pdf")

# --- 3. 세션 상태 초기화 로직 ---
# 새 파일이 업로드되면 모든 상태 초기화
if uploaded_file and st.session_state.get("uploaded_filename") != uploaded_file.name:
    st.session_state.clear()
    st.session_state.uploaded_filename = uploaded_file.name
    st.session_state.step = 0 # 0: 시작 단계

if not uploaded_file:
    st.info("사이드바에서 RFP PDF 파일을 업로드하면 분석이 시작됩니다.")
    st.session_state.clear()

# --- 4. 단계별 실행 로직 ---
if uploaded_file:
    # --- 1단계: 텍스트 추출 ---
    if st.session_state.step == 0:
        st.info("PDF 파일이 업로드되었습니다. 아래 버튼을 눌러 텍스트 추출을 시작하세요.")
        if st.button("1단계: PDF 파일 내용 추출"):
            full_text = extract_text_from_pdf(uploaded_file)
            if full_text:
                st.session_state.full_text = full_text
                st.session_state.step = 1 # 다음 단계로
                st.rerun()

    # --- 1단계 완료 후 & 2단계 시작 전 ---
    if st.session_state.get("step", 0) >= 1:
        with st.expander("1단계: PDF 추출 내용 확인", expanded=(st.session_state.step == 1)):
            st.text_area("추출된 텍스트", st.session_state.full_text, height=200)
            st.download_button(
                label="📥 추출 텍스트 다운로드 (.txt)",
                data=st.session_state.full_text,
                file_name=f"{uploaded_file.name.split('.')[0]}_extracted.txt",
                mime="text/plain"
            )
            if st.session_state.step == 1:
                st.info("텍스트 추출이 완료되었습니다. 이제 제안서 요약을 생성할 수 있습니다.")
                if st.button("2단계: 제안서 요약 생성"):
                    with st.spinner("AI가 제안서를 요약 중입니다..."):
                        # DB 생성 (요약 단계에서 최초 1회 실행)
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
                        chunks = text_splitter.split_text(st.session_state.full_text)
                        
                        # LangChain의 공식 Document 객체를 사용하여 doc_chunks 생성
                        doc_chunks = [Document(page_content=t) for t in chunks]
                        
                        st.session_state.vector_db = create_db_from_text(doc_chunks)
                        
                        # 요약 생성
                        st.session_state.summary = generate_summary(st.session_state.vector_db)
                        st.session_state.step = 2
                        st.rerun()

    # --- 2단계 완료 후 & 3단계 시작 전 ---
    if st.session_state.get("step", 0) >= 2:
        st.markdown("---")
        st.subheader("2. 제안서 요약")
        st.markdown(st.session_state.summary)
        if st.session_state.step == 2:
            st.info("제안서 요약이 완료되었습니다. 이제 핵심 성공 요소를 분석할 수 있습니다.")
            if st.button("3단계: 핵심 성공 요소 분석"):
                with st.spinner("AI가 핵심 성공 요소를 분석 중입니다..."):
                    st.session_state.ksf = generate_ksf(st.session_state.vector_db)
                    st.session_state.step = 3
                    st.rerun()

    # --- 3단계 완료 후 & 4단계 시작 전 ---
    if st.session_state.get("step", 0) >= 3:
        st.markdown("---")
        st.subheader("3. 핵심 성공 요소 (KSF)")
        st.markdown(st.session_state.ksf)
        if st.session_state.step == 3:
            st.info("핵심 성공 요소 분석이 완료되었습니다. 마지막으로 발표자료 목차를 생성합니다.")
            if st.button("4단계: 발표자료 목차 생성"):
                with st.spinner("AI가 창의적인 발표자료 목차를 구성 중입니다..."):
                    st.session_state.presentation_outline = generate_outline(
                        st.session_state.vector_db, st.session_state.summary, st.session_state.ksf
                    )
                    st.session_state.messages = [] # 채팅 기록 초기화
                    st.session_state.step = 4
                    st.rerun()

    # --- 모든 단계 완료 후: 최종 결과물 및 채팅 UI 표시 ---
    if st.session_state.get("step", 0) >= 4:
        st.markdown("---")
        st.success("모든 분석 단계가 완료되었습니다! 이제 아래 결과물을 검토하고 채팅으로 수정할 수 있습니다.")
        
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
                        # (이하 채팅 로직은 기존과 동일)
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
