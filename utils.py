# utils.py
import os
import re
import streamlit as st
import fitz
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from prompts import (
    PROJECT_SUMMARY_PROMPT, RISK_ANALYSIS_PROMPT, KSF_ANALYSIS_PROMPT,
    HOLISTIC_PRESENTATION_STORYLINE_PROMPT, HYDE_PROMPT, GRANULAR_REFINEMENT_CHAT_PROMPT,
    TEXT_REFINEMENT_PROMPT
)

API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

# [신규] AI 기반 텍스트 정제 함수
@st.cache_data(show_spinner="AI가 OCR 추출 텍스트를 자동으로 정제하고 있습니다...")
def refine_text_with_ai(text_to_refine):
    """OCR로 추출된 텍스트를 LLM을 사용해 정제합니다."""
    if not text_to_refine or not text_to_refine.strip():
        return ""
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=API_KEY)
        prompt = PromptTemplate.from_template(TEXT_REFINEMENT_PROMPT)
        chain = prompt | llm | StrOutputParser()

        # 긴 텍스트를 처리하기 위해 청크 단위로 나눌 수 있지만,
        # gpt-4o의 컨텍스트가 충분히 크므로 전체를 한번에 처리 시도
        refined_text = chain.invoke({"raw_text": text_to_refine})
        return refined_text
    except Exception as e:
        st.error(f"AI 텍스트 정제 중 오류 발생: {e}")
        st.warning("원본 텍스트를 그대로 사용하여 분석을 진행합니다.")
        return text_to_refine

# [수정] 텍스트 추출 함수가 원본과 정제본을 모두 반환하도록 변경
def extract_text_from_file(uploaded_file):
    """파일에서 텍스트를 추출하고, PDF의 경우 AI 정제를 수행합니다."""
    raw_text = None
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
            raw_text = re.sub(r'\n\s*\n', '\n\n', full_text).strip()
        except Exception as e:
            st.error(f"PDF 텍스트 추출 중 오류: {e}")
            return None, None
    elif uploaded_file.type == "text/plain":
        raw_text = uploaded_file.getvalue().decode("utf-8")
    
    if raw_text:
        # PDF인 경우에만 AI 정제 레이어 호출 (TXT는 원본 그대로 사용)
        if uploaded_file.type == "application/pdf":
            refined_text = refine_text_with_ai(raw_text)
            return raw_text, refined_text
        else:
            # TXT 파일은 정제가 불필요하므로 원본을 그대로 사용
            return raw_text, raw_text
            
    return None, None

@st.cache_resource(show_spinner="문서를 분석하여 AI가 이해할 수 있도록 준비 중입니다...")
def create_vector_db(refined_text):
    if not refined_text: return None
    try:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        chunks = text_splitter.split_text(refined_text)
        doc_chunks = [Document(page_content=t) for t in chunks]
        embeddings = OpenAIEmbeddings(api_key=API_KEY)
        vector_db = FAISS.from_documents(doc_chunks, embeddings)
        return vector_db
    except Exception as e:
        st.error(f"벡터 DB 생성 중 오류: {e}")
        return None

@st.cache_data(show_spinner="사업의 핵심 개요를 추출 중입니다...")
def extract_project_summary(_vector_db):
    if not _vector_db: return "사업 개요 정보를 추출할 수 없습니다."
    try:
        retriever = _vector_db.as_retriever(search_kwargs={'k': 5})
        relevant_docs = retriever.get_relevant_documents("사업명, 사업개요, 추진배경, 사업목표")
        context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
        llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=API_KEY)
        prompt = PromptTemplate.from_template(PROJECT_SUMMARY_PROMPT)
        chain = prompt | llm
        summary = chain.invoke({"context": context}).content
        return summary
    except Exception as e:
        st.error(f"사업 개요 추출 중 오류: {e}")
        return "사업 개요 추출 중 오류가 발생했습니다."

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

@st.cache_data(show_spinner="단계 1: 리스크 분석...")
def generate_risk_report(_vector_db):
    question = "이 RFP를 분석하여, 제안사 입장에서의 잠재적 리스크와 도전 과제를 관리 전략과 함께 설명해줘."
    return run_analysis_with_inputs(_vector_db, RISK_ANALYSIS_PROMPT, question, inputs={})

@st.cache_data(show_spinner="단계 2: KSF 분석...")
def generate_ksf_report(_vector_db, final_risk_report):
    question = "이 RFP와 식별된 리스크를 바탕으로, 경쟁에서 승리하기 위한 핵심 성공 요소(KSF)를 도출해줘."
    return run_analysis_with_inputs(_vector_db, KSF_ANALYSIS_PROMPT, question, inputs={"risk_report": final_risk_report})

@st.cache_data(show_spinner="단계 3: 목차 생성...")
def generate_outline_report(_vector_db, project_summary, final_risk_report, final_ksf_report):
    question = "이 RFP의 전반적인 내용과 목표, 요구사항을 종합하여 발표자료의 흐름을 잡아줘."
    return run_analysis_with_inputs(
        _vector_db,
        HOLISTIC_PRESENTATION_STORYLINE_PROMPT,
        question,
        inputs={
            "project_summary": project_summary,
            "risk_report": final_risk_report,
            "ksf_report": final_ksf_report
        },
        search_k=15
    )

def parse_report_items(report_text):
    pattern = re.compile(r'(?=\n(?:## |\*\*|\* \*\*)\d+\..*?)', re.DOTALL)
    items = pattern.split(report_text)
    parsed_items = [item.strip() for item in items if item and re.search(r'^(?:## |\*\*|\* \*\*)\d+\.', item.strip())]
    header = items[0].strip() if items and not re.search(r'^(?:## |\*\*|\* \*\*)\d+\.', items[0].strip()) else ""
    return header, parsed_items

def refine_report_with_chat(vector_db, locked_items, unlocked_items, user_request):
    retriever = vector_db.as_retriever(search_kwargs={'k': 5})
    search_query = user_request + "\n\n" + "\n".join(unlocked_items)
    relevant_docs = retriever.get_relevant_documents(search_query)
    retrieved_context = "\n\n---\n\n".join([doc.page_content for doc in relevant_docs])
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, openai_api_key=API_KEY)
    prompt = PromptTemplate.from_template(GRANULAR_REFINEMENT_CHAT_PROMPT)
    chain = prompt | llm
    response = chain.invoke({
        "locked_items": "\n".join(locked_items),
        "unlocked_items": "\n".join(unlocked_items),
        "retrieved_context": retrieved_context,
        "user_request": user_request
    })
    return response.content
