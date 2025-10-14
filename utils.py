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
# 원본 프롬프트 전체를 임포트합니다.
from prompts import FACT_EXTRACTION_PROMPT, STRATEGIC_SUMMARY_PROMPT, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE, EDITOR_PROMPT_TEMPLATE

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

@st.cache_data(show_spinner="핵심 정보(예산, 기간 등)를 추출 중입니다...")
def extract_facts(_full_text, run_id=0):
    if not _full_text:
        return None
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    prompt = PromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
    chain = prompt | llm
    context = _full_text[:8000]

    response = chain.invoke({"context": context})
    try:
        facts = json.loads(response.content)
        return facts
    except json.JSONDecodeError:
        st.error("AI가 반환한 정보 형식이 잘못되었습니다. 다시 시도해주세요.")
        return None

@st.cache_data(show_spinner="AI 컨설턴트가 전략 보고서를 작성 중입니다...")
def generate_strategic_report(_vector_db, facts, run_id=0):
    if _vector_db is None or facts is None:
        return None
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])

    relevant_docs = _vector_db.similarity_search(
        "사업 개요, 추진 배경, 사업 범위, 요구사항, 사업 예산, 사업 기간, 계약 조건, 평가 기준",
        k=15
    )
    context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])

    prompt = PromptTemplate.from_template(STRATEGIC_SUMMARY_PROMPT)
    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "project_name": facts.get("project_name", "문서에 명시되지 않음"),
        "project_duration": facts.get("project_duration", "문서에 명시되지 않음"),
        "project_budget": facts.get("project_budget", "문서에 명시되지 않음"),
        "project_background": facts.get("project_background", "문서에 명시되지 않음")
    })
    return response.content

@st.cache_data(show_spinner="AI 전략가가 핵심 성공 요소와 발표 목차를 구상 중입니다...")
def generate_creative_reports(_vector_db, summary, run_id=0):
    if _vector_db is None or summary is None:
        return None, None
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    creative_context_docs = _vector_db.similarity_search("RFP의 전체적인 내용, 사업 목표, 요구사항, 평가 기준", k=10)
    creative_context = "\n\n---\n\n".join([doc.page_content for doc in creative_context_docs])

    # KSF 생성 (원본 프롬프트 사용)
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = ksf_prompt | llm
    ksf_response = ksf_chain.invoke({"context": creative_context})
    ksf = ksf_response.content

    # 발표자료 목차 생성 (원본 프롬프트 사용)
    outline_prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    outline_chain = outline_prompt | llm
    outline_response = outline_chain.invoke({
        "summary": summary,
        "ksf": ksf,
        "context": creative_context
    })
    presentation_outline = outline_response.content
    return ksf, presentation_outline

def to_excel(facts, summary, ksf, outline):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if facts:
            df_facts = pd.DataFrame.from_dict(facts, orient='index', columns=['내용'])
            df_facts.index.name = '항목'
            df_facts.to_excel(writer, sheet_name='프로젝트 개요')

        df_summary = pd.DataFrame([summary.replace("\n", "\r\n")], columns=["내용"])
        df_summary.to_excel(writer, sheet_name='전략 보고서', index=False)

        df_ksf = pd.DataFrame([ksf.replace("\n", "\r\n")], columns=["내용"])
        df_ksf.to_excel(writer, sheet_name='핵심 성공 요소', index=False)

        df_outline = pd.DataFrame([outline.replace("\n", "\r\n")], columns=["내용"])
        df_outline.to_excel(writer, sheet_name='발표자료 목차', index=False)

    processed_data = output.getvalue()
    return processed_data
