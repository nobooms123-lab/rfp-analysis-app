# utils.py (롤백 완료)
import os
import re
import json
import tempfile
import pandas as pd
import io
import streamlit as st
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from prompts import SUMMARY_PROMPT_TEMPLATE, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE, EDITOR_PROMPT_TEMPLATE

# --- 내부 헬퍼 함수들 ---
def _extract_text_from_pdf(uploaded_file):
    try:
        file_bytes = uploaded_file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = [page.get_text() for page in doc]
        doc.close()
        full_text_raw = "\n\n".join(all_text)
        text = re.sub(r'\n\s*\n', '\n', full_text_raw)
        return text.strip()
    except Exception as e:
        st.error(f"텍스트 추출 중 오류 발생: {e}")
        return None

def _create_db_from_text(text_chunks):
    doc_chunks = [Document(page_content=t) for t in text_chunks]
    embeddings = OpenAIEmbeddings(api_key=st.secrets["OPENAI_GPT_API_KEY"])
    vector_db = FAISS.from_documents(doc_chunks, embeddings)
    return vector_db

# --- 한 번에 모든 결과를 생성하는 메인 함수 ---
@st.cache_data(show_spinner=False) # 스피너는 main.py에서 제어
def generate_initial_results(_uploaded_file):
    # 1. 텍스트 추출
    full_text = _extract_text_from_pdf(_uploaded_file)
    if not full_text:
        return None, None, None

    # 2. 텍스트 분할 및 DB 생성
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    chunks = text_splitter.split_text(full_text)
    vector_db = _create_db_from_text(chunks)
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    
    # 3. 요약 생성 (map_reduce)
    summary_chain = load_qa_chain(llm, chain_type="map_reduce")
    summary_docs = vector_db.similarity_search("RFP의 전체 내용을 상세히 요약해 주세요.", k=10)
    summary = summary_chain.invoke({"input_documents": summary_docs, "question": "제공된 RFP 문서의 각 부분을 종합하여, 아래 템플릿에 맞춰 상세한 요약 보고서를 한국어로 작성해 주십시오:\n\n" + SUMMARY_PROMPT_TEMPLATE})["output_text"]

    # 4. KSF 생성 (map_reduce)
    ksf_chain = load_qa_chain(llm, chain_type="map_reduce")
    ksf_docs = vector_db.similarity_search("이 사업의 핵심 성공 요소를 분석해 주세요.", k=10)
    ksf = ksf_chain.invoke({"input_documents": ksf_docs, "question": "제공된 RFP 문서의 내용을 종합적으로 분석하여, 이 사업 수주를 위한 핵심 성공 요소(KSF) 5-6가지를 구체적으로 도출하고 각각에 대해 간략히 설명해 주십시오."})["output_text"]

    # 5. 발표자료 목차 생성 (stuff)
    outline_retriever = vector_db.as_retriever()
    outline_prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    outline_chain = load_qa_chain(llm, chain_type="stuff", prompt=outline_prompt)
    outline_docs = outline_retriever.get_relevant_documents("RFP의 전체 내용을 분석해줘.")
    context_text = "\n\n".join([doc.page_content for doc in outline_docs])
    presentation_outline = outline_chain.invoke({
        "input_documents": outline_docs,
        "question": "RFP 내용, 프로젝트 요약, 핵심 성공 요소를 바탕으로 발표자료 목차를 만들어줘.",
        "summary": summary,
        "ksf": ksf,
        "context": context_text
    })["output_text"]

    return summary, ksf, presentation_outline

# --- 채팅 및 엑셀 변환 함수 (변경 없음) ---
def handle_chat_interaction(user_input, vector_db_in_session, current_summary, current_ksf, current_outline):
    # DB 재생성을 막기 위해 세션의 DB를 직접 사용
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    retriever = vector_db_in_session.as_retriever()
    prompt = PromptTemplate(
        template=EDITOR_PROMPT_TEMPLATE, 
        input_variables=["summary", "ksf", "outline", "user_request", "context"]
    )
    relevant_docs = retriever.get_relevant_documents(user_input)
    context_text = "\n\n".join([doc.page_content for doc in relevant_docs])
    chain = prompt | llm
    response = chain.invoke({
        "summary": current_summary, "ksf": current_ksf, "outline": current_outline, 
        "user_request": user_input, "context": context_text
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
