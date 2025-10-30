# utils.py

import os
import re
import streamlit as st
import fitz
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
# 새로 추가/수정된 프롬프트를 import 합니다.
from prompts import RFP_REORGANIZATION_PROMPT, CONTEXT_AWARE_REORGANIZE_PROMPT, CHUNK_SUMMARY_PROMPT

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

# [신규/핵심] RFP 텍스트를 재구성하는 함수
@st.cache_data(show_spinner="AI가 RFP 문서를 주제별로 재구성하고 있습니다...")
def reorganize_rfp_text(raw_text, tpm_limit=28000):
    if not API_KEY or not raw_text:
        return None

    try:
        encoding = tiktoken.encoding_for_model("gpt-4o")
        total_tokens = len(encoding.encode(raw_text))
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.0, openai_api_key=API_KEY)

        # CASE 1: 텍스트가 짧아 한 번에 처리 가능한 경우 (최고 품질)
        if total_tokens <= tpm_limit:
            st.info("문서 전체를 한 번에 분석하여 최상의 품질로 재구성합니다.")
            prompt = PromptTemplate.from_template(RFP_REORGANIZATION_PROMPT)
            chain = prompt | llm
            response = chain.invoke({"raw_text": raw_text})
            return response.content

        # CASE 2: 텍스트가 길어 분할 처리가 필요한 경우 (슬라이딩 윈도우)
        else:
            st.warning(f"문서가 길어({total_tokens} 토큰) 분할하여 처리합니다. 품질 유지를 위해 문맥 인식 방식을 사용합니다.")
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=400)
            chunks = text_splitter.split_text(raw_text)
            
            summary_prompt = PromptTemplate.from_template(CHUNK_SUMMARY_PROMPT)
            reorganize_prompt = PromptTemplate.from_template(CONTEXT_AWARE_REORGANIZE_PROMPT)
            summary_chain = summary_prompt | llm
            reorganize_chain = reorganize_prompt | llm

            # 1. 사전 요약
            summaries = [summary_chain.invoke({"chunk_text": chunk}).content for chunk in chunks]
            
            # 2. 문맥 기반 재구성
            reorganized_chunks = []
            progress_bar = st.progress(0, text="문서를 재구성하는 중...")
            for i, chunk in enumerate(chunks):
                previous_context = summaries[i-1] if i > 0 else "이전 내용 없음"
                next_context = summaries[i+1] if i < len(chunks) - 1 else "다음 내용 없음"
                
                response = reorganize_chain.invoke({
                    "previous_context": previous_context,
                    "next_context": next_context,
                    "current_chunk": chunk
                })
                reorganized_chunks.append(response.content)
                progress_bar.progress((i + 1) / len(chunks), text=f"문서 재구성 중... ({i+1}/{len(chunks)})")
            
            progress_bar.empty()
            return "\n\n".join(reorganized_chunks)

    except Exception as e:
        st.error(f"텍스트 재구성 중 오류 발생: {e}")
        return None



