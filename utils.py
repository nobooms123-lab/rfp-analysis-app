import os
import re
import io
import json
import pandas as pd
import streamlit as st
import fitz  # PyMuPDF
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 프롬프트 임포트 (prompts.py 필요)
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
        return uploaded_file.getvalue().decode("utf-8").strip()
    except Exception as e:
        st.error(f"텍스트 파일 처리 오류: {e}")
        return None

def process_pdf_file(uploaded_file):
    try:
        file_bytes = uploaded_file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = [page.get_text() for page in doc]
        doc.close()
        text = "\n".join(all_text)
        return re.sub(r'\n\s*\n', '\n', text).strip()
    except Exception as e:
        st.error(f"PDF 텍스트 추출 오류: {e}")
        return None

# --- RFP 텍스트 정제 ---
@st.cache_data(show_spinner="RFP 정제 중...")
def refine_rfp_text(raw_text, run_id=0):
    if not raw_text:
        return None
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )
    splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=500)
    docs = splitter.create_documents([raw_text])

    map_prompt = PromptTemplate.from_template(
        """
        다음 텍스트에서 불필요한 내용(법적, 형식적, 반복적 내용)만 제거하고 핵심 내용은 유지하세요.

        === 문서 조각 ===
        {text}
        """
    )

    combine_prompt = PromptTemplate.from_template(RFP_REFINEMENT_PROMPT)

    from langchain.chains.summarize import load_summarize_chain
    chain = load_summarize_chain(llm, chain_type="map_reduce",
                                 map_prompt=map_prompt, combine_prompt=combine_prompt)
    response = chain.invoke({"input_documents": docs})
    return response.get("output_text", "정제 실패")

# --- 핵심 정보 추출 ---
@st.cache_data(show_spinner="핵심 정보 추출 중...")
def extract_facts(refined_text, run_id=0):
    if not refined_text:
        return None
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )
    prompt = PromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
    chain = LLMChain(llm=llm, prompt=prompt)
    context = refined_text[:8000]
    response = chain.run({"summary": context})
    try:
        cleaned = re.search(r'\{.*\}', response, re.DOTALL).group(0)
        return json.loads(cleaned)
    except:
        st.error("정보 추출 실패: AI 응답 형식 오류")
        return None

# --- 전략 보고서 생성 ---
@st.cache_data(show_spinner="전략 보고서 생성 중...")
def generate_strategic_report(refined_text, facts, run_id=0):
    if not refined_text or not facts:
        return None
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )
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

# --- KSF 및 발표 목차 ---
@st.cache_data(show_spinner="KSF 및 발표 목차 생성 중...")
def generate_creative_reports(refined_text, summary_report, run_id=0):
    if not refined_text or not summary_report:
        return None, None
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )
    ksf_chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(KSF_PROMPT_TEMPLATE))
    outline_chain = LLMChain(llm=llm, prompt=PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE))
    ksf = ksf_chain.run({"context": refined_text})
    outline = outline_chain.run({"summary": summary_report, "ksf": ksf, "context": refined_text})
    return ksf, outline

# --- Excel 변환 ---
def to_excel(facts, summary, ksf, outline):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if facts:
            pd.DataFrame.from_dict(facts, orient="index", columns=["내용"]).to_excel(writer, sheet_name="프로젝트 개요")
        pd.DataFrame([summary], columns=["전략 보고서"]).to_excel(writer, sheet_name="전략 보고서", index=False)
        pd.DataFrame([ksf], columns=["핵심 성공 요소"]).to_excel(writer, sheet_name="핵심 성공 요소", index=False)
        pd.DataFrame([outline], columns=["발표자료 목차"]).to_excel(writer, sheet_name="발표자료 목차", index=False)
    output.seek(0)
    return output.getvalue()




