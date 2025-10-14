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
from prompts import SUMMARY_JSON_EXTRACT_PROMPT, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE, EDITOR_PROMPT_TEMPLATE

@st.cache_resource(show_spinner="PDF 분석 및 데이터베이스 생성 중...")
def get_vector_db(_uploaded_file):
    try:
        file_bytes = _uploaded_file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = [page.get_text() for page in doc]
        doc.close()
        full_text_raw = "\n\n".join(all_text)
        text = re.sub(r'\n\s*\n', '\n', full_text_raw)
        full_text = text.strip()
    except Exception as e:
        st.error(f"텍스트 추출 중 오류 발생: {e}")
        return None, None
    if not full_text:
        return None, None

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    chunks = text_splitter.split_text(full_text)
    doc_chunks = [Document(page_content=t) for t in chunks]
    embeddings = OpenAIEmbeddings(api_key=st.secrets["OPENAI_GPT_API_KEY"])
    vector_db = FAISS.from_documents(doc_chunks, embeddings)
    
    return vector_db, full_text

def format_summary_from_json(data: dict) -> str:
    """추출된 JSON 데이터를 최종 Markdown 보고서 형식으로 변환합니다."""
    
    # AI가 추출한 '주요 제약사항 및 요구사항' 텍스트를 가져옴
    constraints_and_reqs = data.get("주요_제약사항_및_요구사항", "명시된 제약사항 없음")

    report = f"""
### 1. 사업 개요 및 추진 배경
- **(사업명)**: {data.get("사업명", "찾을 수 없음")}
- **(추진 배경 및 필요성)**: {data.get("추진_배경_및_필요성", "찾을 수 없음")}
- **(사업의 최종 목표)**: {data.get("사업의_최종_목표", "찾을 수 없음")}

### 2. 사업 범위 및 주요 요구사항
- **(주요 사업 범위)**: {data.get("주요_사업_범위", "찾을 수 없음")}
- **(핵심 기능 요구사항)**: {data.get("핵심_기능_요구사항", "찾을 수 없음")}
- **(데이터 및 연동 요구사항)**: {data.get("데이터_및_연동_요구사항", "찾을 수 없음")}

### 3. 사업 수행 조건 및 제약사항
- **(사업 기간)**: {data.get("사업_기간", "찾을 수 없음")}
- **(사업 예산)**: {data.get("사업_예산", "찾을 수 없음")}
- **(주요 제약사항 및 요구사항)**: 
{constraints_and_reqs}

### 4. 제안서 평가 기준
- **(평가 항목 및 배점)**: {data.get("평가_항목_및_배점", "찾을 수 없음")}
- **(정성적 평가 항목 분석)**: {data.get("정성적_평가_항목_분석", "찾을 수 없음")}

### 5. 결론: 제안 전략 수립을 위한 핵심 고려사항
- 위 분석 내용을 바탕으로, 이 사업 수주를 위해 우리 제안사가 반드시 고려해야 할 핵심 성공 요인(Critical Success Factors) 3가지를 제안해 주십시오.
"""
    return report.strip()


@st.cache_data(show_spinner="AI가 분석 보고서를 생성 중입니다...")
def generate_reports(_vector_db, _full_text, run_id=0):
    if _vector_db is None or _full_text is None:
        return None, None, None
    
    extraction_llm = ChatOpenAI(model="gpt-4o", temperature=0.1, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    creative_llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
        
    start_content = _full_text[:4000]
    end_content = _full_text[-4000:]
    middle_docs = _vector_db.similarity_search("사업 범위, 요구사항, 사업수행, 제약, 기술, 품질, 평가", k=7)
    middle_content = "\n\n---\n\n".join([doc.page_content for doc in middle_docs])
    summary_context = f"[문서 시작 부분]\n{start_content}\n\n[문서 핵심 내용 발췌]\n{middle_content}\n\n[문서 끝 부분]\n{end_content}"

    summary_prompt = PromptTemplate.from_template(SUMMARY_JSON_EXTRACT_PROMPT)
    summary_chain = summary_prompt | extraction_llm
    summary_response = summary_chain.invoke({"context": summary_context})
    
    try:
        json_match = re.search(r'\{.*\}', summary_response.content, re.DOTALL)
        if not json_match: raise ValueError("응답에서 JSON 객체를 찾을 수 없음")
        extracted_data = json.loads(json_match.group(0))
        summary = format_summary_from_json(extracted_data)
    except Exception as e:
        st.error(f"요약 정보 처리 중 오류 발생: {e}")
        summary = "요약 보고서 생성에 실패했습니다."

    ksf_docs = _vector_db.similarity_search("이 사업의 핵심 성공 요소를 분석해 주세요.", k=7)
    ksf_context = "\n\n".join([doc.page_content for doc in ksf_docs])
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = ksf_prompt | creative_llm
    ksf_response = ksf_chain.invoke({"context": ksf_context})
    ksf = ksf_response.content

    outline_docs = _vector_db.similarity_search("RFP의 전체 내용을 분석해줘.", k=10)
    context_text = "\n\n".join([doc.page_content for doc in outline_docs])
    outline_prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    outline_chain = outline_prompt | creative_llm
    outline_response = outline_chain.invoke({
        "summary": summary,
        "ksf": ksf,
        "context": context_text
    })
    presentation_outline = outline_response.content

    return summary, ksf, presentation_outline

def handle_chat_interaction(user_input, vector_db_in_session, current_summary, current_ksf, current_outline):
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    retriever = vector_db_in_session.as_retriever()
    prompt = PromptTemplate.from_template(EDITOR_PROMPT_TEMPLATE)
    relevant_docs = retriever.get_relevant_documents(user_input)
    context_text = "\n\n".join([doc.page_content for doc in relevant_docs])

    chain = prompt | llm
    response = chain.invoke({
        "summary": current_summary, 
        "ksf": current_ksf, 
        "outline": current_outline,
        "user_request": user_input, 
        "context": context_text
    })
    return response.content

def to_excel(summary, ksf, outline):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_summary = pd.DataFrame([summary.replace("\n", "\r\n")], columns=["내용"])
        df_summary.to_excel(writer, sheet_name='제안서 요약', index=False)
        df_ksf = pd.DataFrame([ksf.replace("\n", "\r\n")], columns=["내용"])
        df_ksf.to_excel(writer, sheet_name='핵심 성공 요소', index=False)
        df_outline = pd.DataFrame([outline.replace("\n", "\r\n")], columns=["내용"])
        df_outline.to_excel(writer, sheet_name='발표자료 목차', index=False)
    processed_data = output.getvalue()
    return processed_data
