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
# --- 변경점: 새로운 프롬프트 임포트 ---
from prompts import FACT_EXTRACTION_PROMPT, STRATEGIC_SUMMARY_PROMPT, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE

# --- 기존 함수 유지: PDF 파싱 및 벡터DB 생성 ---
@st.cache_resource(show_spinner="PDF 분석 및 데이터베이스 생성 중...")
def get_vector_db(_uploaded_file):
    # ... (기존 코드와 동일)
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

# --- 신규 함수: 1단계 - 사실 정보 추출 ---
@st.cache_data(show_spinner="핵심 정보(예산, 기간 등)를 추출 중입니다...")
def extract_facts(_full_text, run_id=0):
    if not _full_text:
        return None
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    prompt = PromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
    chain = prompt | llm
    
    # 전체 텍스트의 앞부분(보통 주요 정보가 위치)을 우선적으로 사용
    context = _full_text[:8000] # Use first 8000 chars for efficiency
    
    response = chain.invoke({"context": context})
    try:
        # LLM이 반환한 JSON 문자열을 파싱
        facts = json.loads(response.content)
        return facts
    except json.JSONDecodeError:
        st.error("AI가 반환한 정보 형식이 잘못되었습니다. 다시 시도해주세요.")
        return None

# --- 함수명 변경 및 수정: 2단계 - 전략 보고서 생성 ---
@st.cache_data(show_spinner="AI 컨설턴트가 전략 보고서를 작성 중입니다...")
def generate_strategic_report(_vector_db, run_id=0):
    if _vector_db is None:
        return None
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    
    relevant_docs = _vector_db.similarity_search(
        "사업 개요, 추진 배경, 사업 범위, 요구사항, 사업 예산, 사업 기간, 계약 조건, 평가 기준",
        k=15
    )
    context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
    
    # --- 변경점: STRATEGIC_SUMMARY_PROMPT 사용 ---
    prompt = PromptTemplate.from_template(STRATEGIC_SUMMARY_PROMPT)
    chain = prompt | llm
    response = chain.invoke({"context": context})
    return response.content

# --- 기존 함수 유지: KSF 및 목차 생성 ---
@st.cache_data(show_spinner="AI 전략가가 핵심 성공 요소와 발표 목차를 구상 중입니다...")
def generate_creative_reports(_vector_db, summary, run_id=0):
    # ... (기존 코드와 동일, summary는 이제 전략 보고서가 됨)
    if _vector_db is None or summary is None:
        return None, None
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    creative_context_docs = _vector_db.similarity_search("RFP의 전체적인 내용, 사업 목표, 요구사항, 평가 기준", k=10)
    creative_context = "\n\n---\n\n".join([doc.page_content for doc in creative_context_docs])
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = ksf_prompt | llm
    ksf_response = ksf_chain.invoke({"context": creative_context})
    ksf = ksf_response.content
    outline_prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    outline_chain = outline_prompt | llm
    outline_response = outline_chain.invoke({
        "summary": summary, "ksf": ksf, "context": creative_context
    })
    presentation_outline = outline_response.content
    return ksf, presentation_outline

# --- 함수 수정: 엑셀 다운로드에 '프로젝트 개요' 시트 추가 ---
def to_excel(facts, summary, ksf, outline):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 1. 프로젝트 개요 시트 추가
        if facts:
            df_facts = pd.DataFrame.from_dict(facts, orient='index', columns=['내용'])
            df_facts.index.name = '항목'
            df_facts.to_excel(writer, sheet_name='프로젝트 개요')

        # 2. 기존 시트들 추가
        df_summary = pd.DataFrame([summary.replace("\n", "\r\n")], columns=["내용"])
        df_summary.to_excel(writer, sheet_name='전략 보고서', index=False)
        df_ksf = pd.DataFrame([ksf.replace("\n", "\r\n")], columns=["내용"])
        df_ksf.to_excel(writer, sheet_name='핵심 성공 요소', index=False)
        df_outline = pd.DataFrame([outline.replace("\n", "\r\n")], columns=["내용"])
        df_outline.to_excel(writer, sheet_name='발표자료 목차', index=False)
    
    processed_data = output.getvalue()
    return processed_data
