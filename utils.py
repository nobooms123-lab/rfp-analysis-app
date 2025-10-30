# utils.py

import os
import re
import pandas as pd
import io
import streamlit as st
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from prompts import BIDDER_VIEW_SUMMARY_PROMPT, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("OpenAI API 키가 설정되지 않았습니다. st.secrets 또는 환경변수를 확인해주세요.")

@st.cache_resource(show_spinner="PDF 분석 및 데이터베이스 생성 중...")
def get_vector_db(_uploaded_file):
    if not API_KEY:
        return None, None
    try:
        file_bytes = _uploaded_file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = [page.get_text() for page in doc]
        doc.close()
        full_text_raw = "\n\n".join(all_text)
        text = re.sub(r'\n\s*\n', '\n', full_text_raw)
        full_text = text.strip()
    except Exception as e:
        st.error(f"PDF 텍스트 추출 중 오류 발생: {e}")
        return None, None

    if not full_text:
        st.warning("PDF에서 텍스트를 추출할 수 없습니다.")
        return None, None

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    chunks = text_splitter.split_text(full_text)
    doc_chunks = [Document(page_content=t) for t in chunks]
    
    embeddings = OpenAIEmbeddings(api_key=API_KEY)
    vector_db = FAISS.from_documents(doc_chunks, embeddings)
    
    return vector_db, full_text

# [신규 추가] 텍스트 입력을 받아 벡터 DB를 생성하는 함수
@st.cache_resource(show_spinner="텍스트 분석 및 데이터베이스 생성 중...")
def get_vector_db_from_text(text_input):
    if not API_KEY or not text_input:
        return None
    
    try:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        chunks = text_splitter.split_text(text_input)
        doc_chunks = [Document(page_content=t) for t in chunks]
        
        embeddings = OpenAIEmbeddings(api_key=API_KEY)
        vector_db = FAISS.from_documents(doc_chunks, embeddings)
        
        return vector_db
    except Exception as e:
        st.error(f"텍스트 처리 중 오류 발생: {e}")
        return None

# --- Part 1: 제안서 요약 생성 ---
@st.cache_data(show_spinner="AI 컨설턴트가 제안사 관점에서 RFP를 분석 중입니다...")
def generate_summary(_vector_db):
    if _vector_db is None or not API_KEY:
        return None
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=API_KEY)
    relevant_docs = _vector_db.similarity_search(
        "사업 개요, 추진 배경, 사업 범위, 요구사항, 사업 예산, 사업 기간, 계약 조건, 평가 기준", k=15)
    context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
    
    prompt = PromptTemplate.from_template(BIDDER_VIEW_SUMMARY_PROMPT)
    chain = prompt | llm
    response = chain.invoke({"context": context})
    
    return response.content

# --- Part 2: KSF 및 목차 생성 ---
@st.cache_data(show_spinner="AI 전략가가 핵심 성공 요소와 발표 목차를 구상 중입니다...")
def generate_creative_reports(_vector_db, summary):
    if _vector_db is None or summary is None or not API_KEY:
        return None, None
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=API_KEY)
    creative_context_docs = _vector_db.similarity_search("RFP의 전체적인 내용, 사업 목표, 요구사항, 평가 기준", k=10)
    creative_context = "\n\n---\n\n".join([doc.page_content for doc in creative_context_docs])
    
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = ksf_prompt | llm
    ksf_response = ksf_chain.invoke({"context": creative_context})
    ksf = ksf_response.content
    
    outline_prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    outline_chain = outline_prompt | llm
    outline_response = outline_chain.invoke({"summary": summary, "ksf": ksf, "context": creative_context})
    presentation_outline = outline_response.content
    
    return ksf, presentation_outline

# --- Part 3: Excel 변환 ---
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




