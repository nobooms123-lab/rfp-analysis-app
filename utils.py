# utils.py (최종 수정본)

import os
import re
import json
import pandas as pd
import io
import streamlit as st
import fitz  # PyMuPDF

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI # 다른 함수에서 사용하므로 유지
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain

# [수정] Gemini 모델 사용을 위한 라이브러리 import
from langchain_google_genai import ChatGoogleGenerativeAI

# 프롬프트 임포트 (prompts.py가 수정되었다고 가정)
from prompts import (
    RFP_REFINEMENT_PROMPT,
    FACT_EXTRACTION_PROMPT,
    STRATEGIC_SUMMARY_PROMPT,
    KSF_PROMPT_TEMPLATE,
    OUTLINE_PROMPT_TEMPLATE
)

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

# --- [수정] 데이터 정제 함수를 "제거(Subtractive)" 방식 + Gemini 모델로 전면 수정 ---
@st.cache_data(show_spinner="AI가 RFP 문서를 분석하며 불필요한 정보를 제거 중입니다... (시간이 걸릴 수 있습니다)")
def refine_rfp_text(_full_text, run_id=0):
    if not _full_text:
        return None

    # [수정] 속도와 성능을 위해 OpenAI 모델 대신 Google Gemini Flash 모델 사용
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            temperature=0,
            google_api_key=st.secrets["GOOGLE_API_KEY"] # secrets.toml에서 키를 읽어옵니다.
        )
    except Exception as e:
        st.error(f"Gemini 모델 초기화 중 오류 발생: {e}. secrets.toml에 GOOGLE_API_KEY가 올바르게 설정되었는지 확인하세요.")
        return None

    # [수정] API 호출 횟수를 줄여 속도를 높이기 위해 chunk_size를 대폭 증가
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=30000, chunk_overlap=1000)
    docs = text_splitter.create_documents([_full_text])

    # Map 프롬프트: 각 텍스트 조각에서 '뻔하고 불필요한' 정보만 제거. 핵심 내용은 그대로 유지.
    map_prompt_template = """
    You are an AI assistant that cleans up a chunk of an RFP document.
    Your goal is to remove only the obviously unnecessary parts while preserving all critical project information.

    [Instructions]
    1.  **PRESERVE CORE CONTENT:** Keep all text related to project background, goals, budget, duration, technical requirements, security requirements, data requirements, project management rules, and evaluation criteria. DO NOT summarize or alter this information.
    2.  **REMOVE GENERIC BOILERPLATE:** Delete common, non-specific text that is not unique to this project. Examples include:
        - Standard legal disclaimers or confidentiality clauses.
        - Generic instructions on how to format or submit a proposal (e.g., "Submit 10 copies in a binder").
        - Repeated page headers, footers, or page numbers.
        - Vague introductory phrases that add no value.
    3.  **DO NOT EXTRACT, BUT CLEAN:** You are not extracting specific sections. You are cleaning the provided text chunk by removing the noise around the important content.

    --- Document Chunk ---
    {text}
    ---
    Cleaned text chunk with boilerplate removed:
    """
    map_prompt = PromptTemplate.from_template(map_prompt_template)

    # Reduce 프롬프트 (prompts.py에서 가져옴): 1차 정제된 조각들을 합치고, 최종 중복 제거 및 구조화
    combine_prompt = PromptTemplate.from_template(RFP_REFINEMENT_PROMPT)

    chain = load_summarize_chain(
        llm,
        chain_type="map_reduce",
        map_prompt=map_prompt,
        combine_prompt=combine_prompt,
    )

    response = chain.invoke({"input_documents": docs})
    return response.get('output_text', "오류: 텍스트 정제에 실패했습니다.")


# --- 이하 함수들은 품질 유지를 위해 기존 모델(GPT)을 그대로 사용 (변경 없음) ---
@st.cache_data(show_spinner="핵심 정보(예산, 기간 등)를 추출 중입니다...")
def extract_facts(_refined_text, run_id=0):
    if not _refined_text:
        return None
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    prompt = PromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
    chain = prompt | llm
    context = _refined_text[:8000] # 간단한 추출 작업이므로 전체 텍스트 불필요
    response = chain.invoke({"context": context})
    try:
        # LLM이 JSON 코드 블록(```json ... ```)을 반환하는 경우도 처리
        cleaned_content = re.search(r'\{.*\}', response.content, re.DOTALL).group(0)
        facts = json.loads(cleaned_content)
        return facts
    except (json.JSONDecodeError, AttributeError):
        st.error("AI가 반환한 정보 형식이 잘못되었습니다. 다시 시도해주세요.")
        return None

@st.cache_data(show_spinner="AI 컨설턴트가 전략 보고서를 작성 중입니다...")
def generate_strategic_report(refined_text, facts, run_id=0):
    if not refined_text or not facts:
        return None
    # [설명] 이 단계는 높은 품질의 분석이 중요하므로 gpt-4o를 유지합니다.
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    prompt = PromptTemplate.from_template(STRATEGIC_SUMMARY_PROMPT)
    chain = prompt | llm
    response = chain.invoke({
        "context": refined_text,
        "project_name": facts.get("project_name", "N/A"),
        "project_duration": facts.get("project_duration", "N/A"),
        "project_budget": facts.get("project_budget", "N/A"),
        "project_background": facts.get("project_background", "N/A")
    })
    return response.content

@st.cache_data(show_spinner="AI 전략가가 핵심 성공 요소와 발표 목차를 구상 중입니다...")
def generate_creative_reports(refined_text, summary_report, run_id=0):
    if not refined_text or not summary_report:
        return None, None
    # [설명] 창의적인 결과물이 중요하므로 gpt-4o를 유지합니다.
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = ksf_prompt | llm
    ksf_response = ksf_chain.invoke({"context": refined_text})
    ksf = ksf_response.content

    outline_prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    outline_chain = outline_prompt | llm
    outline_response = outline_chain.invoke({
        "summary": summary_report,
        "ksf": ksf,
        "context": refined_text
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
        df_summary = pd.DataFrame([summary], columns=["전략 보고서"])
        df_summary.to_excel(writer, sheet_name='전략 보고서', index=False)
        df_ksf = pd.DataFrame([ksf], columns=["핵심 성공 요소"])
        df_ksf.to_excel(writer, sheet_name='핵심 성공 요소', index=False)
        df_outline = pd.DataFrame([outline], columns=["발표자료 목차"])
        df_outline.to_excel(writer, sheet_name='발표자료 목차', index=False)
    processed_data = output.getvalue()
    return processed_data


