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
# [오류 해결을 위한 핵심 수정] 필요한 체인들을 직접 import
from langchain.chains import LLMChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.mapreduce import MapReduceDocumentsChain

# 프롬프트 임포트
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

# --- [오류 해결을 위한 핵심 수정] Map-Reduce 체인을 수동으로 구성 ---
@st.cache_data(show_spinner="AI가 긴 RFP 문서를 분석 및 정제 중입니다... (시간이 걸릴 수 있습니다)")
def refine_rfp_text(_full_text, run_id=0):
    if not _full_text:
        return None
    
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])

    # 1. Map 단계에 사용할 체인 (각 조각 처리용)
    map_prompt_template = """
    다음은 RFP 문서의 일부입니다. 이 텍스트에서 아래 항목에 해당하는 핵심 내용만 추출하십시오.
    - 프로젝트 개요 및 핵심 정보 (사업명, 예산, 기간, 배경)
    - 컨설팅 요구사항 (CSR)
    - 제약사항 (COR)
    - 특이하거나 중요한 프로젝트 관리/지원 요구사항 (PMR, PSR)
    - 평가 기준
    목차, 붙임 서식, 일반 계약 조건 등 불필요한 내용은 무시하십시오.
    --- 텍스트 일부 ---
    {text}
    ---
    핵심 내용 추출 결과:
    """
    map_prompt = PromptTemplate.from_template(map_prompt_template)
    map_chain = LLMChain(llm=llm, prompt=map_prompt)

    # 2. Reduce 단계에 사용할 체인 (모든 조각의 결과를 합쳐 최종본 생성용)
    combine_prompt = PromptTemplate.from_template(RFP_REFINEMENT_PROMPT)
    reduce_chain = LLMChain(llm=llm, prompt=combine_prompt)

    # 3. Map 단계의 결과물들을 하나로 묶는 체인
    combine_documents_chain = StuffDocumentsChain(
        llm_chain=reduce_chain,
        document_variable_name="context" # combine_prompt의 변수 이름과 일치
    )

    # 4. Map-Reduce 전체를 관장하는 메인 체인
    map_reduce_chain = MapReduceDocumentsChain(
        llm_chain=map_chain,
        combine_documents_chain=combine_documents_chain,
        document_variable_name="text", # map_prompt의 변수 이름과 일치
        return_intermediate_steps=False
    )

    # 5. 텍스트를 분할하여 체인 실행
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=500)
    docs = text_splitter.create_documents([_full_text])
    
    response = map_reduce_chain.invoke(docs)
    
    return response.get('output_text', "오류: 텍스트 정제에 실패했습니다.")


@st.cache_data(show_spinner="핵심 정보(예산, 기간 등)를 추출 중입니다...")
def extract_facts(_refined_text, run_id=0):
    if not _refined_text:
        return None
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    prompt = PromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
    chain = prompt | llm
    context = _refined_text[:8000]
    response = chain.invoke({"context": context})
    try:
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


