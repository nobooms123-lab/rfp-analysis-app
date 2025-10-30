# utils.py

import os
import re
import streamlit as st
import fitz  # PyMuPDF
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from prompts import RFP_REFINEMENT_PROMPT

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("OpenAI API 키가 설정되지 않았습니다. st.secrets 또는 환경변수를 확인해주세요.")

# PDF에서 텍스트만 추출하는 기능으로 단순화
@st.cache_data(show_spinner="PDF에서 텍스트를 추출 중입니다...")
def extract_text_from_pdf(_uploaded_file):
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

# RFP 텍스트를 정제하는 핵심 함수
@st.cache_data(show_spinner="AI가 RFP 원본 텍스트를 핵심 내용 위주로 정제 중입니다...")
def refine_rfp_text(raw_text):
    if not API_KEY or not raw_text:
        return None
    
    try:
        # 정제 작업은 일관성이 중요하므로 temperature를 낮게 설정
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1, openai_api_key=API_KEY)
        
        prompt = PromptTemplate.from_template(RFP_REFINEMENT_PROMPT)
        chain = prompt | llm
        response = chain.invoke({"raw_text": raw_text})
        
        return response.content
    except Exception as e:
        st.error(f"텍스트 정제 중 오류 발생: {e}")
        return None


