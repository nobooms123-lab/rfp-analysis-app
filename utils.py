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
from langchain.chains.summarize import load_summarize_chain

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

# --- [최종 수정] 데이터 정제 함수 재설계 ---
@st.cache_data(show_spinner="AI가 긴 RFP 문서를 분석 및 정제 중입니다... (시간이 걸릴 수 있습니다)")
def refine_rfp_text(_full_text, run_id=0):
    if not _full_text:
        return None
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=500)
    docs = text_splitter.create_documents([_full_text])

    # [재설계 1] Map 프롬프트: AI를 '섹션 복사기'로 만듦
    map_prompt_template = """
    당신은 RFP 문서에서 지정된 섹션을 원문 그대로 복사하는 AI입니다.

    [지시사항]
    아래 "대상 섹션 목록"에 있는 제목의 섹션을 발견하면, 그 섹션의 **제목과 내용 전체를 단 한 글자도 빠짐없이 그대로 복사**하십시오.
    **절대 요약하거나 내용을 변경하지 마십시오.**
    만약 대상 섹션이 없다면, 아무것도 출력하지 마십시오.

    [대상 섹션 목록]
    - 사업명
    - 사업기간
    - 수요기관
    - 추진배경 및 필요성
    - 주요 사업내용
    - 소요예산
    - 컨설팅 요구사항
    - 데이터 요구사항
    - 보안 요구사항
    - 제약사항
    - 프로젝트 관리 요구사항
    - 프로젝트 지원 요구사항
    - 입찰 방식
    - 제안서 평가 방법
    - 제안서 기술평가 기준 및 배점 한도

    --- 문서 조각 ---
    {text}
    ---

    복사된 섹션 내용:
    """
    map_prompt = PromptTemplate.from_template(map_prompt_template)
    
    # [재설계 2] Reduce 프롬프트: AI를 '문서 조립기'로 만듦
    combine_prompt_template = """
    당신은 여러 조각으로 나뉘어 추출된 RFP 섹션들을 하나의 완전한 문서로 재조립하는 AI입니다.

    [지시사항]
    아래 "추출된 조각 모음"에 있는 텍스트들을 사용하여, 다음 규칙에 따라 최종 문서를 만드십시오.
    1.  각 내용을 논리적인 순서에 따라 재배열하십시오. (예: 사업 개요 -> 배경 -> 사업 내용 -> 요구사항 순)
    2.  여러 조각으로 나뉜 동일한 섹션(예: '컨설팅 요구사항')이 있다면, 그 내용들을 모두 합쳐 하나의 완전한 섹션으로 만드십시오.
    3.  완전히 동일하게 중복되는 문장은 제거하십시오.
    4.  최종 결과물은 한국어로 된 명확한 제목과 함께 정리된 마크다운 형식이어야 합니다.

    --- 추출된 조각 모음 ---
    {text}
    ---
    
    재조립된 최종 RFP 핵심 요약본:
    """
    combine_prompt = PromptTemplate.from_template(combine_prompt_template)

    chain = load_summarize_chain(
        llm,
        chain_type="map_reduce",
        map_prompt=map_prompt,
        combine_prompt=combine_prompt,
        document_variable_name="text"
    )

    response = chain.invoke({"input_documents": docs})
    
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




