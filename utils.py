# utils.py

import os
import re
import streamlit as st
import fitz
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from prompts import RISK_ANALYSIS_PROMPT, KSF_ANALYSIS_PROMPT, PRESENTATION_OUTLINE_PROMPT

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("OpenAI API 키가 설정되지 않았습니다. st.secrets 또는 환경변수를 확인해주세요.")

# 텍스트 추출 함수 (이전과 동일)
def extract_text_from_file(uploaded_file):
    # ... (이전 RAG 버전의 코드와 동일) ...
    if uploaded_file.type == "application/pdf":
        try:
            file_bytes = uploaded_file.getvalue()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            full_text = ""
            for page in doc:
                blocks = page.get_text("blocks", sort=True)
                blocks.sort(key=lambda b: (b[1], b[0]))
                full_text += "\n".join([b[4] for b in blocks if b[4].strip()]) + "\n\n"
            doc.close()
            return re.sub(r'\n\s*\n', '\n\n', full_text).strip()
        except Exception as e:
            st.error(f"PDF 텍스트 추출 중 오류: {e}")
            return None
    elif uploaded_file.type == "text/plain":
        return uploaded_file.getvalue().decode("utf-8")
    return None

# 벡터 DB 생성 함수 (이전과 동일)
@st.cache_resource(show_spinner="문서를 분석하여 AI가 이해할 수 있도록 준비 중입니다...")
def create_vector_db(text):
    # ... (이전 RAG 버전의 코드와 동일) ...
    if not text: return None
    try:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        chunks = text_splitter.split_text(text)
        doc_chunks = [Document(page_content=t) for t in chunks]
        embeddings = OpenAIEmbeddings(api_key=API_KEY)
        vector_db = FAISS.from_documents(doc_chunks, embeddings)
        return vector_db
    except Exception as e:
        st.error(f"벡터 DB 생성 중 오류: {e}")
        return None

# 범용 분석 함수
def run_analysis(vector_db, prompt_template, search_query, search_k=10):
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=API_KEY)
    prompt = PromptTemplate.from_template(prompt_template)
    chain = prompt | llm
    
    retriever = vector_db.as_retriever(search_kwargs={'k': search_k})
    relevant_docs = retriever.get_relevant_documents(search_query)
    context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
    
    response = chain.invoke({"context": context})
    return response.content

# 3가지 분석을 순차적으로 실행하는 메인 함수
def generate_all_reports(vector_db):
    if not vector_db:
        return None, None, None
    
    # 각 분석에 사용할 검색어와 프롬프트를 정의
    # 검색어는 각 분석의 목적에 맞게 관련 정보를 잘 찾을 수 있도록 설정
    with st.spinner("1/3. 제안사 관점의 리스크를 분석 중입니다..."):
        risk_report = run_analysis(
            vector_db,
            RISK_ANALYSIS_PROMPT,
            "사업 수행의 위험 요소, 계약 조건, 제약 사항, 과업 범위, 책임 및 의무"
        )

    with st.spinner("2/3. 핵심 성공 요소를 도출 중입니다..."):
        ksf_report = run_analysis(
            vector_db,
            KSF_ANALYSIS_PROMPT,
            "사업 목표, 추진 배경, 평가 기준, 핵심 요구사항, 기대 효과"
        )

    with st.spinner("3/3. 발표자료 목차 초안을 작성 중입니다..."):
        outline_report = run_analysis(
            vector_db,
            PRESENTATION_OUTLINE_PROMPT,
            "사업의 이해, 사업 추진 전략, 사업 범위, 목표, 요구사항, 제안 요청 내용",
            search_k=15 # 목차는 더 넓은 범위의 정보가 필요하므로 k값을 늘림
        )
        
    return risk_report, ksf_report, outline_report


