# main.py

import streamlit as st
from io import StringIO
from utils import extract_text_from_pdf, refine_rfp_text

# --- 1. 기본 설정 및 초기화 ---
st.set_page_config(page_title="RFP 텍스트 정제 도우미", layout="wide")
st.title("RFP 텍스트 정제 도우미")
st.info("PDF나 TXT 형식의 제안요청서를 업로드하여 불필요한 내용을 제거하고 핵심만 추출합니다.")

# 세션 상태 초기화 (Stage 재정의)
if 'stage' not in st.session_state:
    # 0: 초기 -> 1: 원본텍스트 준비 -> 2: 텍스트정제 완료
    st.session_state.stage = 0

def reset_session():
    # 파일이 바뀔 때 세션 상태 초기화
    keys_to_clear = ['stage', 'raw_text', 'refined_text', 'uploaded_filename']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.stage = 0

# --- 2. 사이드바 구성 (입력) ---
st.sidebar.title("작업 순서")

# 입력 방식 선택 탭
pdf_tab, text_tab = st.sidebar.tabs(["📄 PDF 업로드", "✍️ TXT 파일 업로드"])

with pdf_tab:
    uploaded_pdf_file = st.file_uploader("1. PDF 파일 업로드", type="pdf", key="pdf_uploader", on_change=reset_session)
    if uploaded_pdf_file and st.session_state.stage == 0:
        st.session_state.uploaded_filename = uploaded_pdf_file.name
        st.session_state.raw_text = extract_text_from_pdf(uploaded_pdf_file)
        if st.session_state.raw_text:
            st.session_state.stage = 1
            st.rerun()

with text_tab:
    uploaded_txt_file = st.file_uploader("1. TXT 파일 업로드", type="txt", key="txt_uploader", on_change=reset_session)
    if uploaded_txt_file and st.session_state.stage == 0:
        st.session_state.uploaded_filename = uploaded_txt_file.name
        stringio = StringIO(uploaded_txt_file.getvalue().decode("utf-8"))
        st.session_state.raw_text = stringio.read()
        if st.session_state.raw_text:
            st.session_state.stage = 1
            st.rerun()

# --- 3. 단계별 실행 로직 ---

# Stage 1: 원본 텍스트 준비 완료 -> 정제 대기
if st.session_state.stage >= 1:
    st.sidebar.success("✓ 1단계: 원본 텍스트 준비 완료")
    if st.sidebar.button("2. RFP 텍스트 정제 실행", disabled=(st.session_state.stage > 1)):
        refined_text = refine_rfp_text(st.session_state.raw_text)
        if refined_text:
            st.session_state.refined_text = refined_text
            st.session_state.stage = 2
            st.rerun()

# Stage 2: 텍스트 정제 완료
if st.session_state.stage >= 2:
    st.sidebar.success("✓ 2단계: 텍스트 정제 완료")
    st.sidebar.header("결과 다운로드")
    st.sidebar.download_button(
        label="📥 정제된 텍스트 다운로드 (.md)",
        data=st.session_state.refined_text.encode('utf-8'),
        file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_refined.md",
        mime="text/markdown"
    )

# --- 4. 메인 화면 UI 렌더링 ---
if st.session_state.stage < 1:
    st.warning("사이드바에서 분석할 파일을 업로드해주세요.")
else:
    tab1, tab2 = st.tabs(["RFP 원본 텍스트", "정제된 텍스트"])

    with tab1:
        st.text_area("RFP 원본", st.session_state.get("raw_text", ""), height=500)

    with tab2:
        if st.session_state.stage < 2:
            st.info("사이드바에서 'RFP 텍스트 정제 실행' 버튼을 눌러주세요.")
        else:
            st.markdown(st.session_state.get("refined_text", ""))

