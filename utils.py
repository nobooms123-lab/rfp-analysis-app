import os
import io
import re
import openai
import streamlit as st
import pandas as pd
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# -----------------------------
# 1. OpenAI API 초기화
# -----------------------------
@st.cache_resource
def init_openai_llm(temperature=0.0, model_name="gpt-4o-mini"):
    """
    OpenAI 기반 LLM 초기화
    """
    openai.api_key = st.secrets["OPENAI_API_KEY"]

    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_key=openai.api_key,
    )
    return llm

# -----------------------------
# 2. 텍스트 정제 함수
# -----------------------------
@st.cache_data
def refine_rfp_text(raw_text, run_id="default"):
    """
    RFP 텍스트 정제 및 핵심 내용 추출
    """
    llm = init_openai_llm(temperature=0)

    prompt = PromptTemplate(
        input_variables=["text"],
        template=(
            "다음은 공공기관 제안요청서(RFP) 원문입니다.\n"
            "핵심 요구사항, 평가 항목, 기술 과업 범위를 중심으로 구조화된 요약을 작성하세요.\n\n"
            "=== 원문 ===\n{text}\n\n"
            "=== 정제된 요약 ==="
        ),
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    refined = chain.run({"text": raw_text})
    return refined.strip()

# -----------------------------
# 3. 주요 사실(데이터) 추출
# -----------------------------
@st.cache_data
def extract_facts(refined_text):
    """
    정제된 문서에서 기관명, 예산, 수행기간 등 주요 항목 추출
    """
    llm = init_openai_llm()

    prompt = PromptTemplate(
        input_variables=["summary"],
        template=(
            "다음 RFP 요약에서 다음 정보를 표 형식으로 추출하세요:\n"
            "① 사업명 ② 발주기관 ③ 총사업비(예산) ④ 사업기간 ⑤ 주요 과업 ⑥ 평가 기준 요약\n\n"
            "=== RFP 요약 ===\n{summary}\n\n"
            "=== 표 형식 출력 ==="
        ),
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    facts = chain.run({"summary": refined_text})
    return facts.strip()

# -----------------------------
# 4. 전략 보고서 초안 생성
# -----------------------------
@st.cache_data
def generate_strategy_report(refined_text):
    """
    RFP 분석 기반의 전략 보고서 초안 생성
    """
    llm = init_openai_llm(temperature=0.3)

    prompt = PromptTemplate(
        input_variables=["summary"],
        template=(
            "아래의 RFP 요약을 바탕으로 제안 전략 보고서 초안을 작성하세요.\n"
            "형식: ① 과업 개요 ② 기술적 접근 전략 ③ 차별화 포인트 ④ 위험 요인 및 대응\n\n"
            "=== RFP 요약 ===\n{summary}\n\n"
            "=== 제안 전략 보고서 초안 ==="
        ),
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    strategy = chain.run({"summary": refined_text})
    return strategy.strip()

# -----------------------------
# 5. Excel 변환 (보고서 내보내기)
# -----------------------------
def convert_to_excel(data_dict):
    """
    여러 텍스트 결과물을 시트별로 Excel로 저장
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, text_content in data_dict.items():
            df = pd.DataFrame({"내용": [text_content]})
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    buffer.seek(0)
    return buffer

    """
    return llm(prompt)

