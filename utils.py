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
from langchain.chains.question_answering import load_qa_chain
from prompts import SUMMARY_PROMPT_TEMPLATE, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE, EDITOR_PROMPT_TEMPLATE

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

@st.cache_data(show_spinner="AI가 분석 보고서를 생성 중입니다...")
def generate_reports(_vector_db, _full_text, run_id=0):
    if _vector_db is None or _full_text is None:
        return None, None, None
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
        
    # --- <<< 요약 생성 로직 (가장 확실하고 직접적인 방식으로 전면 교체) >>> ---
    # 1. 문서의 맨 앞부분과, 검색된 세부 내용을 합쳐 AI에게 전달할 '문맥(Context)'을 직접 생성
    header_content = _full_text[:4000]
    detail_docs = _vector_db.similarity_search(
        "사업 범위, 주요 요구사항, 사업 수행 조건, 제약사항, 평가 기준", k=5
    )
    detail_content = "\n\n".join([doc.page_content for doc in detail_docs])
    summary_context = f"[문서 시작 부분]\n{header_content}\n\n[문서 주요 내용]\n{detail_content}"

    # 2. 문제를 일으키는 load_qa_chain 대신, 프롬프트와 LLM을 직접 연결하는 간단한 체인 생성
    summary_prompt = PromptTemplate.from_template(SUMMARY_PROMPT_TEMPLATE)
    summary_chain = summary_prompt | llm

    # 3. 체인에 'context'와 'question'을 직접 전달하여 정보 유실 가능성 원천 차단
    summary_response = summary_chain.invoke({
        "context": summary_context,
        "question": "제공된 Context를 바탕으로, 템플릿에 맞춰 상세 요약 보고서를 작성해 주십시오."
    })
    summary = summary_response.content

    # --- KSF 생성 (기존 방식 유지) ---
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = load_qa_chain(llm, chain_type="stuff", prompt=ksf_prompt)
    ksf_docs = _vector_db.similarity_search("이 사업의 핵심 성공 요소를 분석해 주세요.", k=7)
    ksf = ksf_chain.invoke({
        "input_documents": ksf_docs,
        "question": "문서 내용을 바탕으로 핵심 성공 요소를 분석해줘."
    })["output_text"]

    # --- 발표자료 목차 생성 (기존 방식 유지) ---
    outline_retriever = _vector_db.as_retriever()
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

def handle_chat_interaction(user_input, vector_db_in_session, current_summary, current_ksf, current_outline):
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
