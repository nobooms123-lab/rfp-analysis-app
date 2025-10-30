# utils.py

import os
import re
import streamlit as st
import fitz
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
# 새로 추가된 프롬프트를 import 합니다.
from prompts import CHUNK_SUMMARY_PROMPT, CONTEXT_AWARE_REFINE_PROMPT

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("OpenAI API 키가 설정되지 않았습니다. st.secrets 또는 환경변수를 확인해주세요.")

# PDF 텍스트 추출 함수 (기존과 동일)
@st.cache_data(show_spinner="PDF에서 텍스트를 추출 중입니다...")
def extract_text_from_pdf(_uploaded_file):
    # ... (이전과 동일한 코드) ...
    try:
        file_bytes = _uploaded_file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text_parts = []
        for page in doc:
            blocks = page.get_text("blocks", sort=True)
            blocks.sort(key=lambda b: (b[1], b[0]))
            page_text = "\n".join([b[4] for b in blocks if b[4].strip()])
            all_text_parts.append(page_text)
        doc.close()
        full_text_raw = "\n\n".join(all_text_parts)
        text = re.sub(r'\n\s*\n', '\n\n', full_text_raw)
        return text.strip()
    except Exception as e:
        st.error(f"PDF 텍스트 추출 중 오류 발생: {e}")
        return None

# [대폭 수정] 문맥 인식 슬라이딩 윈도우 방식의 정제 함수
@st.cache_data(show_spinner="AI가 RFP 문맥을 분석하며 정제 중입니다... (시간이 더 걸립니다)")
def refine_rfp_text(raw_text):
    if not API_KEY or not raw_text:
        return None
    
    try:
        # 텍스트 분할기 설정
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=400)
        chunks = text_splitter.split_text(raw_text)
        
        st.info(f"문서가 길어 {len(chunks)}개 조각으로 나누어, 문맥을 고려하며 정제합니다.")
        
        llm_summary = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=API_KEY)
        llm_refine = ChatOpenAI(model="gpt-4o", temperature=0.1, openai_api_key=API_KEY)
        
        summary_prompt = PromptTemplate.from_template(CHUNK_SUMMARY_PROMPT)
        refine_prompt = PromptTemplate.from_template(CONTEXT_AWARE_REFINE_PROMPT)

        summary_chain = summary_prompt | llm_summary
        refine_chain = refine_prompt | llm_refine

        # --- 1. 사전 요약 단계 ---
        summaries = []
        progress_bar = st.progress(0, text="1/2 단계: 각 부분의 사전 요약 생성 중...")
        for i, chunk in enumerate(chunks):
            summary = summary_chain.invoke({"chunk_text": chunk}).content
            summaries.append(summary)
            progress_bar.progress((i + 1) / len(chunks), text=f"1/2 단계: 사전 요약 생성 중... ({i+1}/{len(chunks)})")
        
        # --- 2. 문맥 기반 정제 단계 ---
        refined_chunks = []
        progress_bar.progress(0, text="2/2 단계: 문맥을 기반으로 본문 정제 중...")
        for i, chunk in enumerate(chunks):
            previous_context = summaries[i-1] if i > 0 else "이전 내용 없음"
            next_context = summaries[i+1] if i < len(chunks) - 1 else "다음 내용 없음"
            
            response = refine_chain.invoke({
                "previous_context": previous_context,
                "next_context": next_context,
                "current_chunk": chunk
            })
            refined_chunks.append(response.content)
            progress_bar.progress((i + 1) / len(chunks), text=f"2/2 단계: 본문 정제 중... ({i+1}/{len(chunks)})")
        
        progress_bar.empty()

        # --- 3. 최종 결합 ---
        return "\n\n".join(refined_chunks)

    except Exception as e:
        st.error(f"텍스트 정제 중 오류 발생: {e}")
        return None



