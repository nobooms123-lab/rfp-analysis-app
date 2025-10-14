# utils.py
import os
import re
import json
import pandas as pd
import io
import streamlit as st
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from prompts import SUMMARY_PROMPT_TEMPLATE, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE, EDITOR_PROMPT_TEMPLATE

@st.cache_resource(show_spinner="PDF 분석 및 데이터베이스 생성 중...")
def get_vector_db(_uploaded_file):
    try:
        file_bytes = _uploaded_file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = [page.get_text() for page in doc]
        doc.close()
        full_text_raw = "\n\n".join(all_text)
        text = re.sub(r'\n\s*\n', '\n', full_text_raw)
        full_text = text.strip()
    except Exception as e:
        st.error(f"텍스트 추출 중 오류 발생: {e}")
        return None, None
    if not full_text:
        return None, None

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    chunks = text_splitter.split_text(full_text)
    doc_chunks = [Document(page_content=t) for t in chunks]
    embeddings = OpenAIEmbeddings(api_key=st.secrets["OPENAI_GPT_API_KEY"])
    vector_db = FAISS.from_documents(doc_chunks, embeddings)
    
    return vector_db, full_text

@st.cache_data(show_spinner="AI가 분석 보고서를 생성 중입니다...")
def generate_reports(_vector_db, _full_text, run_id=0):
    if _vector_db is None or _full_text is None:
        return None, None, None
    
    extraction_llm = ChatOpenAI(model="gpt-4o", temperature=0.1, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    creative_llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
        
    # --- <<< 요약 생성: 속도와 안정성을 모두 잡는 '하이브리드' 방식으로 변경 >>> ---
    # 1. 문서의 시작 부분 추출
    start_content = _full_text[:4000]
    # 2. 문서의 끝 부분 추출
    end_content = _full_text[-4000:]
    # 3. 문서의 중간 핵심 내용 검색
    middle_docs = _vector_db.similarity_search(
        "사업 범위, 주요 요구사항, 사업 수행 조건, 제약사항, 필수 도입 기술, 보안 및 품질 요구사항, 평가 기준",
        k=5
    )
    middle_content = "\n\n---\n\n".join([doc.page_content for doc in middle_docs])

    # 4. 세 부분을 조합하여 AI에게 전달할 최종 Context 생성
    summary_context = f"[문서 시작 부분]\n{start_content}\n\n[문서 핵심 내용 발췌]\n{middle_content}\n\n[문서 끝 부분]\n{end_content}"

    # 5. 단 한 번의 API 호출로 요약 생성
    summary_prompt = PromptTemplate.from_template(SUMMARY_PROMPT_TEMPLATE)
    summary_chain = summary_prompt | extraction_llm
    summary_response = summary_chain.invoke({"context": summary_context})
    summary = summary_response.content

    # --- KSF 생성 ---
    ksf_docs = _vector_db.similarity_search("이 사업의 핵심 성공 요소를 분석해 주세요.", k=7)
    ksf_context = "\n\n".join([doc.page_content for doc in ksf_docs])
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = ksf_prompt | creative_llm
    ksf_response = ksf_chain.invoke({"context": ksf_context})
    ksf = ksf_response.content

    # --- 발표자료 목차 생성 ---
    outline_docs = _vector_db.similarity_search("RFP의 전체 내용을 분석해줘.", k=10)
    context_text = "\n\n".join([doc.page_content for doc in outline_docs])
    outline_prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    outline_chain = outline_prompt | creative_llm
    outline_response = outline_chain.invoke({
        "summary": summary,
        "ksf": ksf,
        "context": context_text
    })
    presentation_outline = outline_response.content

    return summary, ksf, presentation_outline

def handle_chat_interaction(user_input, vector_db_in_session, current_summary, current_ksf, current_outline):
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    retriever = vector_db_in_session.as_retriever()
    prompt = PromptTemplate.from_template(EDITOR_PROMPT_TEMPLATE)
    relevant_docs = retriever.get_relevant_documents(user_input)
    context_text = "\n\n".join([doc.page_content for doc in relevant_docs])

    chain = prompt | llm
    response = chain.invoke({
        "summary": current_summary, 
        "ksf": current_ksf, 
        "outline": current_outline,
        "user_request": user_input, 
        "context": context_text
    })
    return response.content

def to_excel(summary, ksf, outline):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_summary = pd.DataFrame([summary.replace("\n", "\r\n")], columns=["내용"])
        df_summary.to_excel(writer, sheet_name='제안서 요약', index=False)
        df_ksf = pd.DataFrame([ksf.replace("\n", "\r\n")], columns=["내용"])
        df_ksf.to_excel(writer, sheet_name='핵심 성공 요소', index=False)
        df_outline = pd.DataFrame([outline.replace("\n", "\r\n")], columns=["내용"])
        df_outline.to_excel(writer, sheet_name='발표자료 목차', index=False)
    processed_data = output.getvalue()
    return processed_data
