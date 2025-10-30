# utils.py

import os
import re
import streamlit as st
import fitz
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from prompts import RFP_REFINEMENT_PROMPT
import tiktoken # tiktoken 라이브러리 import

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

# [수정됨] 토큰 수를 제한하여 텍스트를 정제하는 함수
@st.cache_data(show_spinner="AI가 RFP 텍스트를 정제 중입니다...")
def refine_rfp_text(raw_text, max_tokens=28000): # 최대 토큰 수를 인자로 받음 (기본값 28,000)
    if not API_KEY or not raw_text:
        return None
    
    try:
        # gpt-4o 모델에 대한 인코더를 가져옵니다.
        encoding = tiktoken.encoding_for_model("gpt-4o")
        
        # 원본 텍스트의 토큰 수를 계산합니다.
        tokens = encoding.encode(raw_text)
        
        processed_text = raw_text
        
        # 만약 토큰 수가 제한을 초과하면
        if len(tokens) > max_tokens:
            # max_tokens 만큼 토큰을 잘라냅니다.
            truncated_tokens = tokens[:max_tokens]
            # 잘라낸 토큰을 다시 텍스트로 디코딩합니다.
            processed_text = encoding.decode(truncated_tokens)
            
            # 사용자에게 정보가 잘렸음을 알립니다.
            st.warning(f"입력 텍스트가 너무 깁니다 (총 {len(tokens)} 토큰). "
                       f"비용 관리를 위해 앞부분 {max_tokens} 토큰만 사용하여 정제를 진행합니다. "
                       "문서 뒷부분의 중요 정보가 누락될 수 있습니다.")

        # (이후 로직은 단순 정제 방식과 동일)
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1, openai_api_key=API_KEY)
        prompt = PromptTemplate.from_template(RFP_REFINEMENT_PROMPT)
        chain = prompt | llm
        response = chain.invoke({"raw_text": processed_text})
        
        return response.content
        
    except Exception as e:
        st.error(f"텍스트 정제 중 오류 발생: {e}")
        return None



