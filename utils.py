# utils.py

import os
import re
import streamlit as st
import fitz
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from prompts import (
    RISK_ANALYSIS_PROMPT, KSF_ANALYSIS_PROMPT, HOLISTIC_PRESENTATION_STORYLINE_PROMPT,
    HYDE_PROMPT, REFINEMENT_CHAT_PROMPT
)

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("OpenAI API 키가 설정되지 않았습니다. st.secrets 또는 환경변수를 확인해주세요.")

def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        try:
            file_bytes = uploaded_file.getvalue()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            full_text = ""
            for page in doc:
                blocks = page.get_text("blocks", sort=True)
                blocks.sort(key=lambda b: (b[1], b[0]))
                full_text += "\n".join([b[4] for b in blocks if b[4].strip()]) + "\n\n"
            doc.close()
            return re.sub(r'\n\s*\n', '\n\n', full_text).strip()
        except Exception as e:
            st.error(f"PDF 텍스트 추출 중 오류: {e}")
            return None
    elif uploaded_file.type == "text/plain":
        return uploaded_file.getvalue().decode("utf-8")
    return None

@st.cache_resource(show_spinner="문서를 분석하여 AI가 이해할 수 있도록 준비 중입니다...")
def create_vector_db(text):
    if not text: return None
    try:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        chunks = text_splitter.split_text(text)
        doc_chunks = [Document(page_content=t) for t in chunks]
        embeddings = OpenAIEmbeddings(api_key=API_KEY)
        vector_db = FAISS.from_documents(doc_chunks, embeddings)
        return vector_db
    except Exception as e:
        st.error(f"벡터 DB 생성 중 오류: {e}")
        return None

def run_analysis_with_inputs(vector_db, prompt_template, search_query, inputs, search_k=10):
    hyde_llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=API_KEY)
    hyde_prompt = PromptTemplate.from_template(HYDE_PROMPT)
    hyde_chain = hyde_prompt | hyde_llm
    hypothetical_document = hyde_chain.invoke({"question": search_query}).content
    
    retriever = vector_db.as_retriever(search_kwargs={'k': search_k})
    relevant_docs = retriever.get_relevant_documents(hypothetical_document)
    
    inputs['context'] = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])

    final_llm = ChatOpenAI(model="gpt-4o", temperature=0.3, openai_api_key=API_KEY)
    final_prompt = PromptTemplate.from_template(prompt_template)
    final_chain = final_prompt | final_llm
    
    response = final_chain.invoke(inputs)
    return response.content

@st.cache_data(show_spinner="단계 1: 제안사 관점의 리스크를 분석 중입니다...")
def generate_risk_report(_vector_db):
    question = "이 RFP를 분석하여, 제안사 입장에서의 잠재적 리스크와 도전 과제를 관리 전략과 함께 설명해줘."
    return run_analysis_with_inputs(_vector_db, RISK_ANALYSIS_PROMPT, question, inputs={})

@st.cache_data(show_spinner="단계 2: 핵심 성공 요소를 도출 중입니다...")
def generate_ksf_report(_vector_db, final_risk_report):
    question = "이 RFP와 식별된 리스크를 바탕으로, 경쟁에서 승리하기 위한 핵심 성공 요소(KSF)를 도출해줘."
    return run_analysis_with_inputs(_vector_db, KSF_ANALYSIS_PROMPT, question, inputs={"risk_report": final_risk_report})

@st.cache_data(show_spinner="단계 3: 제안 발표 목차를 생성 중입니다...")
def generate_outline_report(_vector_db, final_risk_report, final_ksf_report):
    question = "이 RFP의 전반적인 내용과 목표, 요구사항을 종합하여 발표자료의 흐름을 잡아줘."
    return run_analysis_with_inputs(
        _vector_db,
        HOLISTIC_PRESENTATION_STORYLINE_PROMPT,
        question,
        inputs={"risk_report": final_risk_report, "ksf_report": final_ksf_report},
        search_k=15
    )

def refine_report_with_chat(vector_db, report_context, user_request):
    retriever = vector_db.as_retriever(search_kwargs={'k': 5})
    relevant_docs = retriever.get_relevant_documents(user_request)
    retrieved_context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, openai_api_key=API_KEY)
    prompt = PromptTemplate.from_template(REFINEMENT_CHAT_PROMPT)
    chain = prompt | llm
    response = chain.invoke({
        "report_context": report_context,
        "retrieved_context": retrieved_context,
        "user_request": user_request
    })
    return response.content

