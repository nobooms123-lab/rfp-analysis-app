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
    # 이전 프롬프트를 새로운 프롬프트로 교체
    ADVANCED_PRESENTATION_OUTLINE_PROMPT,
    HYDE_PROMPT
)

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

# --- extract_text_from_file, create_vector_db, run_analysis_with_hyde 함수는 이전과 동일 ---
def extract_text_from_file(uploaded_file):
    # ... (이전 코드와 동일) ...
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
    # ... (이전 코드와 동일) ...
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

def run_analysis_with_hyde(vector_db, final_prompt_template, user_question, search_k=10):
    # ... (이전 코드와 동일) ...
    hyde_llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=API_KEY)
    hyde_prompt = PromptTemplate.from_template(HYDE_PROMPT)
    hyde_chain = hyde_prompt | hyde_llm
    hypothetical_document = hyde_chain.invoke({"question": user_question}).content
    retriever = vector_db.as_retriever(search_kwargs={'k': search_k})
    relevant_docs = retriever.get_relevant_documents(hypothetical_document)
    context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
    final_llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=API_KEY)
    final_prompt = PromptTemplate.from_template(final_prompt_template)
    final_chain = final_prompt | final_llm
    response = final_chain.invoke({"context": context})
    return response.content

# [수정됨] 목차 생성을 위한 별도 분석 함수
def run_outline_analysis(vector_db, ksf_report, user_question, search_k=15):
    """KSF 보고서를 추가 입력으로 받아 목차를 생성하는 함수"""
    # 1. HyDE를 사용하여 RFP 원본에서 관련 내용 검색
    hyde_llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=API_KEY)
    hyde_prompt = PromptTemplate.from_template(HYDE_PROMPT)
    hyde_chain = hyde_prompt | hyde_llm
    hypothetical_document = hyde_chain.invoke({"question": user_question}).content
    retriever = vector_db.as_retriever(search_kwargs={'k': search_k})
    relevant_docs = retriever.get_relevant_documents(hypothetical_document)
    context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])

    # 2. 검색된 RFP 내용과 KSF 보고서를 합쳐 최종 답변 생성
    final_llm = ChatOpenAI(model="gpt-4o", temperature=0.3, openai_api_key=API_KEY)
    final_prompt = PromptTemplate.from_template(ADVANCED_PRESENTATION_OUTLINE_PROMPT)
    final_chain = final_prompt | final_llm
    # [핵심] invoke에 ksf_report를 추가로 전달
    response = final_chain.invoke({"context": context, "ksf_report": ksf_report})
    return response.content

# [수정됨] 3가지 분석을 '연계하여' 실행하는 메인 함수
def generate_all_reports(vector_db):
    if not vector_db:
        return None, None, None
    
    risk_question = "이 사업 RFP를 분석하여, 제안사 입장에서의 잠재적 리스크와 독소 조항을 식별해줘."
    ksf_question = "이 사업 RFP를 분석하여, 경쟁에서 승리하기 위한 핵심 성공 요소(KSF) 3~5가지를 도출해줘."
    outline_question = "이 사업 RFP의 전반적인 내용과 목표, 요구사항을 종합적으로 요약해줘." # 목차 생성을 위한 일반적인 검색어

    # 1. 리스크와 KSF를 먼저 분석 (병렬 또는 순차 가능)
    with st.spinner("1/3. 제안사 관점의 리스크를 분석 중입니다..."):
        risk_report = run_analysis_with_hyde(
            vector_db, RISK_ANALYSIS_PROMPT, risk_question
        )

    with st.spinner("2/3. 핵심 성공 요소를 도출 중입니다..."):
        ksf_report = run_analysis_with_hyde(
            vector_db, KSF_ANALYSIS_PROMPT, ksf_question
        )

    # 3. KSF 분석 결과를 바탕으로 목차 생성
    with st.spinner("3/3. KSF 기반 발표자료 목차 초안을 작성 중입니다..."):
        outline_report = run_outline_analysis(
            vector_db,
            ksf_report, # [핵심] KSF 결과를 입력으로 전달
            outline_question
        )
        
    return risk_report, ksf_report, outline_report




