# utils.py (Gemini 1.5 Flash 통합 및 인증 최종 수정 버전)

import os
import re
import json
import pandas as pd
import io
import streamlit as st
import fitz  # PyMuPDF

# [필수 임포트]
from google.oauth2 import service_account 
from langchain_google_vertexai import ChatVertexAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain

# 프롬프트 임포트 (prompts.py 파일이 있다고 가정)
from prompts import (
    RFP_REFINEMENT_PROMPT,
    FACT_EXTRACTION_PROMPT,
    STRATEGIC_SUMMARY_PROMPT,
    KSF_PROMPT_TEMPLATE,
    OUTLINE_PROMPT_TEMPLATE
)

# --- Vertex AI LLM 초기화 헬퍼 함수 ---
@st.cache_resource
def init_gemini_llm(temperature: float):
    """Gemini LLM 인스턴스를 초기화하고 캐시합니다."""
    try:
        if "GOOGLE_CREDENTIALS_JSON" not in st.secrets or "GOOGLE_PROJECT_ID" not in st.secrets:
            st.error("Streamlit Secret에 GOOGLE_PROJECT_ID 또는 GOOGLE_CREDENTIALS_JSON이 설정되지 않았습니다.")
            return None
        
        # 1. 환경 변수 충돌 방지: Google의 기본 인증 시도를 막습니다. (TransportError 1차 방어)
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            
        # 2. Secret에서 JSON 문자열을 읽고 인증 정보 객체 생성 준비
        credentials_info = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
        
        # 3. [수정] TransportError 우회 및 Setter 오류 해결: JSON 데이터에 universe_domain을 직접 추가
        if "universe_domain" not in credentials_info:
            credentials_info["universe_domain"] = 'googleapis.com'

        credentials = service_account.Credentials.from_service_account_info(credentials_info)

        # 4. Vertex AI LLM 초기화 시 인증 정보를 명시적으로 전달합니다.
        llm = ChatVertexAI(
            project=st.secrets["GOOGLE_PROJECT_ID"],
            model_name="gemini-1.5-flash-001",
            temperature=temperature,
            location="us-central1",
            credentials=credentials
        )
        return llm
    except Exception as e:
        st.error(f"Vertex AI 모델 초기화 중 오류 발생: {e}. Secrets 설정을 확인하세요.")
        return None

# --- 파일 처리 함수들 (변경 없음) ---
def process_text_file(uploaded_file):
    try:
        full_text = uploaded_file.getvalue().decode("utf-8")
        return full_text.strip()
    except Exception as e:
        st.error(f"텍스트 파일 처리 중 오류 발생: {e}")
        return None

def process_pdf_file(uploaded_file):
    try:
        file_bytes = uploaded_file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = [page.get_text() for page in doc]
        doc.close()
        full_text_raw = "\n\n".join(all_text)
        text = re.sub(r'\n\s*\n', '\n', full_text_raw)
        return text.strip()
    except Exception as e:
        st.error(f"PDF 텍스트 추출 중 오류 발생: {e}")
        return None

# --- 1. 데이터 정제 함수 (Gemini) ---
@st.cache_data(show_spinner="AI가 RFP 문서를 분석하며 불필요한 정보를 제거 중입니다... (시간이 걸릴 수 있습니다)")
def refine_rfp_text(_full_text, run_id=0):
    if not _full_text:
        return None
    
    # LLM 초기화 (temperature=0)
    llm = init_gemini_llm(temperature=0)
    if not llm: return None

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=30000, chunk_overlap=1000)
    docs = text_splitter.create_documents([_full_text])

    # Map 단계 프롬프트 (정제)
    map_prompt_template = """
    You are an AI assistant that cleans up a chunk of an RFP document. Your task is to extract only the core requirements, scope, background, objectives, and evaluation criteria, strictly removing all generic boilerplate, standard legal text, and non-essential introductory material.
    --- Document Chunk ---
    {text}
    ---
    Cleaned text chunk with boilerplate removed:
    """
    map_prompt = PromptTemplate.from_template(map_prompt_template)
    
    # Reduce 단계 프롬프트 (최종 통합)
    combine_prompt = PromptTemplate.from_template(RFP_REFINEMENT_PROMPT)

    chain = load_summarize_chain(
        llm,
        chain_type="map_reduce",
        map_prompt=map_prompt,
        combine_prompt=combine_prompt,
    )
    response = chain.invoke({"input_documents": docs})
    return response.get('output_text', "오류: 텍스트 정제에 실패했습니다.")


# --- 2. 핵심 정보 추출 함수 (Gemini) ---
@st.cache_data(show_spinner="핵심 정보(예산, 기간 등)를 추출 중입니다...")
def extract_facts(_refined_text, run_id=0):
    if not _refined_text:
        return None
        
    # LLM 초기화 (temperature=0)
    llm = init_gemini_llm(temperature=0)
    if not llm: return None

    prompt = PromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
    chain = prompt | llm
    context = _refined_text[:12000] 
    response = chain.invoke({"context": context})
    
    try:
        # LLM 출력에서 JSON 객체만 추출
        cleaned_content = re.search(r'\{.*\}', response.content, re.DOTALL).group(0)
        facts = json.loads(cleaned_content)
        return facts
    except (json.JSONDecodeError, AttributeError):
        st.error(f"AI가 반환한 정보 형식이 잘못되었습니다. 응답 내용: {response.content[:200]}...")
        return None

# --- 3. 전략 보고서 생성 함수 (Gemini) ---
@st.cache_data(show_spinner="AI 컨설턴트가 전략 보고서를 작성 중입니다...")
def generate_strategic_report(refined_text, facts, run_id=0):
    if not refined_text or not facts:
        return None

    # LLM 초기화 (temperature=0.2)
    llm = init_gemini_llm(temperature=0.2)
    if not llm: return None

    prompt = PromptTemplate.from_template(STRATEGIC_SUMMARY_PROMPT)
    chain = prompt | llm
    
    response = chain.invoke({
        "context": refined_text, "project_name": facts.get("project_name", "N/A"),
        "project_duration": facts.get("project_duration", "N/A"), "project_budget": facts.get("project_budget", "N/A"),
        "project_background": facts.get("project_background", "N/A")
    })
    return response.content

# --- 4. KSF 및 발표 목차 생성 함수 (Gemini) ---
@st.cache_data(show_spinner="AI 전략가가 핵심 성공 요소와 발표 목차를 구상 중입니다...")
def generate_creative_reports(refined_text, summary_report, run_id=0):
    if not refined_text or not summary_report:
        return None, None

    # LLM 초기화 (temperature=0.7)
    llm = init_gemini_llm(temperature=0.7)
    if not llm: return None
    
    # 1. KSF 생성
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = ksf_prompt | llm
    ksf_response = ksf_chain.invoke({"context": refined_text})
    ksf = ksf_response.content
    
    # 2. 발표 목차 생성
    outline_prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    outline_chain = outline_prompt | llm
    outline_response = outline_chain.invoke({
        "summary": summary_report, "ksf": ksf, "context": refined_text
    })
    presentation_outline = outline_response.content
    
    return ksf, presentation_outline

# --- 데이터 정리 및 Excel 내보내기 함수 (변경 없음) ---
def to_excel(facts, summary, ksf, outline):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if facts:
            df_facts = pd.DataFrame.from_dict(facts, orient='index', columns=['내용'])
            df_facts.index.name = '항목'
            df_facts.to_excel(writer, sheet_name='프로젝트 개요')
        df_summary = pd.DataFrame([summary], columns=["전략 보고서"])
        df_summary.to_excel(writer, sheet_name='전략 보고서', index=False)
        df_ksf = pd.DataFrame([ksf], columns=["핵심 성공 요소"])
        df_ksf.to_excel(writer, sheet_name='핵심 성공 요소', index=False)
        df_outline = pd.DataFrame([outline], columns=["발표자료 목차"])
        df_outline.to_excel(writer, sheet_name='발표자료 목차', index=False)
    processed_data = output.getvalue()
    return processed_data


