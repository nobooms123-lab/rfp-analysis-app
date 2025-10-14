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
from prompts import SUMMARY_PROMPT_TEMPLATE, REFINE_PROMPT_TEMPLATE, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE, EDITOR_PROMPT_TEMPLATE

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
    
    extraction_llm = ChatOpenAI(model="gpt-4o", temperature=0.1, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    creative_llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
        
    # --- <<< 요약 생성: RateLimitError를 해결하기 위해 'refine' 방식으로 변경 >>> ---
    # 1. 전체 텍스트를 refine 체인이 처리할 수 있도록 작은 조각으로 나눔
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=200)
    summary_doc_chunks = [Document(page_content=t) for t in text_splitter.split_text(_full_text)]

    # 2. refine 체인에 사용할 초기 프롬프트와 업데이트 프롬프트를 정의
    question_prompt = PromptTemplate.from_template(SUMMARY_PROMPT_TEMPLATE)
    refine_prompt = PromptTemplate.from_template(REFINE_PROMPT_TEMPLATE)

    # 3. refine 체인을 생성
    refine_chain = load_qa_chain(
        llm=extraction_llm,
        chain_type="refine",
        question_prompt=question_prompt,
        refine_prompt=refine_prompt,
        return_intermediate_steps=False,
    )
    # 4. 체인을 실행하여 문서 전체를 순차적으로 처리
    summary_response = refine_chain.invoke({"input_documents": summary_doc_chunks, "question": "DUMMY_QUESTION"})
    summary = summary_response["output_text"]

    # --- KSF 생성 ---
    ksf_docs = _vector_db.similarity_search("이 사업의 핵심 성공 요소를 분석해 주세요.", k=7)
    ksf_context = "\n\n".join([doc.page_content for doc in ksf_docs])
    ksf_prompt = PromptTemplate.from_template(KSF_PROMPT_TEMPLATE)
    ksf_chain = ksf_prompt | creative_llm
    ksf_response = ksf_chain.invoke({"context": ksf_context})
    ksf = ksf_response.content

    # --- 발표자료 목차 생성 ---
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
