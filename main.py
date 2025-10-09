# main.py (롤백 완료)
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
    # 파일이 바뀌면 session_state를 초기화
    if st.session_state.get("uploaded_filename") != uploaded_file.name:
        st.session_state.clear()
        st.session_state.uploaded_filename = uploaded_file.name

    # 아직 초기 결과물이 없다면 생성
    if "summary" not in st.session_state:
        with st.spinner("AI가 PDF를 분석하고 초기 보고서를 생성 중입니다... (시간이 걸릴 수 있습니다)"):
            summary, ksf, outline = generate_initial_results(uploaded_file)
            
            if summary and ksf and outline:
                st.session_state.summary = summary
                st.session_state.ksf = ksf
                st.session_state.presentation_outline = outline
                st.session_state.messages = []
                # DB는 채팅 시 필요하므로 캐시된 결과를 다시 로드하지 않도록 세션에 저장
                # (주의: DB 재생성을 막기 위한 트릭. generate_initial_results가 캐시되어 있어도 DB 객체는 매번 새로 생성될 수 있음)
                # 이 부분은 개선이 필요할 수 있으나, 현재 구조에서는 채팅 기능 유지를 위해 필요.
                # 더 나은 방법: DB 생성 로직을 분리하고 @st.cache_resource로 캐시한 뒤 main에서 직접 호출
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
                    # 채팅을 위한 DB 재생성 (비효율적이지만 현재 구조에서 가장 간단한 방법)
                    from langchain.text_splitter import RecursiveCharacterTextSplitter
                    from langchain_core.documents import Document
                    import fitz

                    file_bytes = uploaded_file.getvalue()
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    all_text = [page.get_text() for page in doc]
                    doc.close()
                    full_text = "\n\n".join(all_text)
                    
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
                    chunks = text_splitter.split_text(full_text)
                    doc_chunks = [Document(page_content=t) for t in chunks]
                    
                    from langchain_openai import OpenAIEmbeddings
                    from langchain_community.vectorstores import FAISS
                    embeddings = OpenAIEmbeddings(api_key=st.secrets["OPENAI_GPT_API_KEY"])
                    vector_db = FAISS.from_documents(doc_chunks, embeddings)

                    response_text = handle_chat_interaction(
                        user_prompt, vector_db, st.session_state.summary,
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
