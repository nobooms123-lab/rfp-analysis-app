# utils.py
import os
import re
import json
import tempfile
import pandas as pd
import io
import streamlit as st
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from prompts import SUMMARY_PROMPT_TEMPLATE, KSF_PROMPT_TEMPLATE, OUTLINE_PROMPT_TEMPLATE, EDITOR_PROMPT_TEMPLATE

# --- 1단계 함수: PDF에서 텍스트만 추출 ---
@st.cache_data(show_spinner="PDF 파일에서 텍스트를 추출하고 있습니다...")
def extract_text_from_pdf(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    try:
        # hi_res 전략은 OCR을 포함하여 이미지 기반 PDF도 처리하려고 시도합니다.
        loader = UnstructuredPDFLoader(tmp_file_path, mode="elements", strategy="hi_res", languages=['kor', 'eng'])
        pages = loader.load()
        full_text_raw = "\n\n".join([p.page_content for p in pages])
        
        # 텍스트 정제
        text = re.sub(r'--- Page \d+ ---', '', full_text_raw)
        text = re.sub(r'·+\d+', '', text)
        text = re.sub(r'-\s*\d+\s*-', '', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()
    except Exception as e:
        st.error(f"텍스트 추출 중 오류 발생: {e}")
        return None
    finally:
        os.remove(tmp_file_path)

# --- DB 생성 함수 (분리) ---
@st.cache_resource(show_spinner="추출된 텍스트로 벡터 데이터베이스를 생성 중입니다...")
def create_db_from_text(_text_chunks):
    embeddings = OpenAIEmbeddings(api_key=st.secrets["OPENAI_GPT_API_KEY"])
    vector_db = FAISS.from_documents(_text_chunks, embeddings)
    return vector_db

# --- 2, 3, 4단계 개별 함수 ---
# (선제적 조치) 대용량 PDF 처리를 위해 chain_type을 "map_reduce"로 변경하여 안정성 확보
def generate_summary(vector_db):
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    # map_reduce 방식을 사용하도록 변경
    chain = load_qa_chain(llm, chain_type="map_reduce")
    # 더 많은 청크(k=10)를 가져와 종합적인 분석을 유도
    docs = vector_db.similarity_search("RFP의 전체 내용을 상세히 요약해 주세요.", k=10)
    # map_reduce에 맞는 명확한 지시사항을 question에 포함
    result = chain.invoke({"input_documents": docs, "question": "제공된 RFP 문서의 각 부분을 종합하여, 아래 템플릿에 맞춰 상세한 요약 보고서를 한국어로 작성해 주십시오:\n\n" + SUMMARY_PROMPT_TEMPLATE})
    return result["output_text"]

def generate_ksf(vector_db):
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    # map_reduce 방식을 사용하도록 변경
    chain = load_qa_chain(llm, chain_type="map_reduce")
    docs = vector_db.similarity_search("이 사업의 핵심 성공 요소를 분석해 주세요.", k=10)
    result = chain.invoke({"input_documents": docs, "question": "제공된 RFP 문서의 내용을 종합적으로 분석하여, 이 사업 수주를 위한 핵심 성공 요소(KSF) 5-6가지를 구체적으로 도출하고 각각에 대해 간략히 설명해 주십시오."})
    return result["output_text"]

def generate_outline(vector_db, summary, ksf):
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    # 발표자료 목차는 전체적인 맥락이 매우 중요하므로 stuff 방식을 유지.
    # 이미 요약된 summary와 ksf를 사용하므로 입력 텍스트가 줄어들어 메모리 부담이 적음.
    retriever = vector_db.as_retriever()
    prompt = PromptTemplate.from_template(OUTLINE_PROMPT_TEMPLATE)
    chain = load_qa_chain(llm, chain_type="stuff", prompt=prompt)
    docs = retriever.get_relevant_documents("RFP의 전체 내용을 분석해줘.")
    context_text = "\n\n".join([doc.page_content for doc in docs])
    result = chain.invoke({
        "input_documents": docs,
        "question": "RFP 내용, 프로젝트 요약, 핵심 성공 요소를 바탕으로 발표자료 목차를 만들어줘.",
        "summary": summary,
        "ksf": ksf,
        "context": context_text
    })
    return result["output_text"]

# --- 기존 함수들은 그대로 유지 ---
def handle_chat_interaction(user_input, vector_db, current_summary, current_ksf, current_outline):
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=st.secrets["OPENAI_GPT_API_KEY"])
    retriever = vector_db.as_retriever()
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
