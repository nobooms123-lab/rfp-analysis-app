# utils.py (Streamlit + OpenAI용 안정화 버전)

import re
import io
import json
import pandas as pd
import streamlit as st
import fitz  # PyMuPDF
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from prompts import (
    RFP_REFINEMENT_PROMPT,
    FACT_EXTRACTION_PROMPT,
    STRATEGIC_SUMMARY_PROMPT,
    KSF_PROMPT_TEMPLATE,
    OUTLINE_PROMPT_TEMPLATE
)

# --- 파일 처리 ---
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
        text = re.sub(r'\n\s*\n', '\n', "\n\n".join(all_text))
        return text.strip()
    except Exception as e:
        st.error(f"PDF 텍스트 추출 중 오류 발생: {e}")
        return None

# --- LLM 초기화 ---
@st.cache_resource
def init_openai_llm(model="gpt-4o-mini", temperature=0):
    return ChatOpenAI(model=model, temperature=temperature, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])

# --- 1. RFP 텍스트 정제 ---
@st.cache_data(show_spinner="AI가 RFP 문서를 분석하며 불필요한 정보를 제거 중입니다...")
def refine_rfp_text(_full_text, run_id=0):
    if not _full_text:
        return None
    llm = init_openai_llm()
    splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=500)
    docs = splitter.create_documents([_full_text])

    map_prompt = PromptTemplate.from_template("""
You are an AI assistant that cleans up a chunk of an RFP document.
Remove generic boilerplate and keep all project-critical content.

--- Document Chunk ---
{text}
---
Cleaned text:
""")
    combine_prompt = PromptTemplate.from_template(RFP_REFINEMENT_PROMPT)
    chain = load_summarize_chain(llm, chain_type="map_reduce", map_prompt=map_prompt, combine_prompt=combine_prompt)
    response = chain.invoke({"input_documents": docs})
    return response.get('output_text', "오류: 텍스트 정제에 실패했습니다.")

# --- 2. 핵심 정보 추출 ---
@st.cache_data(show_spinner="핵심 정보(예산, 기간 등)를 추출 중입니다...")
def extract_facts(refined_text, run_id=0):
    if not refined_text:
        return None
    llm = init_openai_llm(model="gpt-3.5-turbo")
    prompt = PromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
    chain = LLMChain(llm=llm, prompt=prompt)
    context = refined_text[:8000]
    response = chain.run({"summary": context})
    try:
        facts = json.loads(re.search(r'\{.*\}', response, re.DOTALL).group(0))
        return facts
    except:
        st.error("AI가 반환한 정보 형식이 잘못되었습니다.")
        return None

# --- 3. 전략 보고서 ---
@st.cache_data(show_spinner="AI 컨설턴트가 전략 보고서를 작성 중입니다...")
def generate_strategic_report(refined_text, facts, run_id=0):
    if not refined_text or not facts:
        return None
    llm = init_openai_llm(model="gpt-4o", temperature=0.2)
    prompt = PromptTemplate.from_template(STRATEGIC_SUMMARY_PROMPT)
    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.run({
        "context": refined_text,
        "project_name": facts.get("project_name", "N/A"),
        "project_duration": facts.get("project_duration", "N/A"),
        "project_budget": facts.get("project_budget", "N/A"),
        "project_background": facts.get("project_background", "N/A")
    })
    return response

# --- 4. KSF & 발표 목차 ---
@st.cache_data(show_spinner="AI 전략가가 핵심 성공 요소와 발표 목차를 구상 중입니다...")
def generate_creative_reports(refined_text, summary_report, run_id=0):
    if not refined_text or not summary_report:
        return None, None
    llm = init_openai_llm(model="gpt-4o", temperature=0.7)
    ksf_chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(KSF_PROMPT_TEMPLATE))
    ksf = ksf_chain.run({"context": refined_text})
    outline_chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE))
    outline = outline_chain.run({"summary": summary_report, "ksf": ksf, "context": refined_text})
    return ksf, outline

# --- 5. Excel 내보내기 ---
def to_excel(facts, summary, ksf, outline):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        if facts:
            df_facts = pd.DataFrame.from_dict(facts, orient='index', columns=['내용'])
            df_facts.index.name = '항목'
            df_facts.to_excel(writer, sheet_name='프로젝트 개요')
        pd.DataFrame([summary], columns=["전략 보고서"]).to_excel(writer, sheet_name='전략 보고서', index=False)
        pd.DataFrame([ksf], columns=["핵심 성공 요소"]).to_excel(writer, sheet_name='핵심 성공 요소', index=False)
        pd.DataFrame([outline], columns=["발표자료 목차"]).to_excel(writer, sheet_name='발표자료 목차', index=False)
    buffer.seek(0)
    return buffer.getvalue()


