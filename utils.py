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
from prompts import (
    RISK_ANALYSIS_PROMPT,
    KSF_ANALYSIS_PROMPT,
    PRESENTATION_OUTLINE_PROMPT,
    HYDE_PROMPT
)

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("OpenAI API 키가 설정되지 않았습니다. st.secrets 또는 환경변수를 확인해주세요.")

def extract_text_from_file(uploaded_file):
    """PDF 또는 TXT 파일에서 텍스트를 추출합니다."""
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

@st.cache_resource(show_spinner="문서를 분석하여 AI가 이해할 수 있도록 준비 중입니다...")
def create_vector_db(text):
    """텍스트를 받아 벡터 데이터베이스를 생성합니다."""
    if not text:
        return None
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

def run_analysis_with_hyde(vector_db, final_prompt_template, user_question, search_k=10):
    """HyDE 전략을 사용하여 특정 질문에 대한 분석을 수행합니다."""
    
    # 1. HyDE: 가상 답변 생성 단계
    # 검색 품질을 높이기 위해 빠르고 저렴한 모델을 사용할 수도 있습니다.
    hyde_llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=API_KEY)
    hyde_prompt = PromptTemplate.from_template(HYDE_PROMPT)
    hyde_chain = hyde_prompt | hyde_llm
    hypothetical_document = hyde_chain.invoke({"question": user_question}).content

    # 2. 생성된 가상 답변으로 DB 검색 (Retrieval 품질 향상)
    retriever = vector_db.as_retriever(search_kwargs={'k': search_k})
    relevant_docs = retriever.get_relevant_documents(hypothetical_document)
    context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])

    # 3. 검색된 실제 정보로 최종 답변 생성
    final_llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=API_KEY)
    final_prompt = PromptTemplate.from_template(final_prompt_template)
    final_chain = final_prompt | final_llm
    response = final_chain.invoke({"context": context})
    
    return response.content

def generate_all_reports(vector_db):
    """3가지 분석을 순차적으로 실행하는 메인 함수"""
    if not vector_db:
        return None, None, None
    
    # 각 분석의 목적을 명확한 '질문' 형태로 정의
    risk_question = "이 사업 제안요청서(RFP)를 분석하여, 제안사 입장에서 발생할 수 있는 기술적, 일정, 예산, 계약 관련 잠재적 리스크와 독소 조항을 모두 식별하고 설명해줘."
    ksf_question = "이 사업 제안요청서(RFP)를 분석하여, 경쟁에서 승리하고 사업을 성공시키기 위한 핵심 성공 요소(KSF) 3~5가지를 구체적인 실행 전략과 함께 도출해줘."
    outline_question = "이 사업 제안요청서(RFP)의 내용을 기반으로, '1. 사업의 이해 (5페이지)', '2. 사업 추진 전략 (9페이지)' 구조에 맞춰 각 페이지에 들어갈 핵심 메시지를 2줄씩 요약하여 발표자료 목차 초안을 작성해줘."

    with st.spinner("1/3. 제안사 관점의 리스크를 분석 중입니다... (HyDE 적용)"):
        risk_report = run_analysis_with_hyde(
            vector_db,
            RISK_ANALISYS_PROMPT,
            risk_question
        )

    with st.spinner("2/3. 핵심 성공 요소를 도출 중입니다... (HyDE 적용)"):
        ksf_report = run_analysis_with_hyde(
            vector_db,
            KSF_ANALYSIS_PROMPT,
            ksf_question
        )

    with st.spinner("3/3. 발표자료 목차 초안을 작성 중입니다... (HyDE 적용)"):
        outline_report = run_analysis_with_hyde(
            vector_db,
            PRESENTATION_OUTLINE_PROMPT,
            outline_question,
            search_k=15 # 목차는 더 넓은 범위의 정보가 필요하므로 k값을 늘림
        )
        
    return risk_report, ksf_report, outline_report


