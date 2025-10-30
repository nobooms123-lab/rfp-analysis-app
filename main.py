# main.py

import streamlit as st
from io import StringIO
# 함수 이름을 reorganize_rfp_text로 변경
from utils import extract_text_from_pdf, reorganize_rfp_text

# --- 1. 기본 설정 및 초기화 ---
st.set_page_config(page_title="RFP 재구성 도우미", layout="wide")
st.title("RFP 문서 재구성 도우미")
st.info("PDF나 TXT 형식의 제안요청서를 업로드하여, 내용을 주제별로 재구성하고 정리합니다.")

if 'stage' not in st.session_state:
    # 0: 초기 -> 1: 원본텍스트 준비 -> 2: 재구성 완료
    st.session_state.stage = 0

def reset_session():
    keys_to_clear = ['stage', 'raw_text', 'reorganized_text', 'uploaded_filename']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.stage = 0

# --- 2. 사이드바 구성 (입력) ---
st.sidebar.title("작업 순서")
pdf_tab, text_tab = st.sidebar.tabs(["📄 PDF 업로드", "✍️ TXT 파일 업로드"])

# ... (파일 업로드 로직은 이전과 동일) ...
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
if st.session_state.stage >= 1:
    st.sidebar.success("✓ 1단계: 원본 텍스트 준비 완료")
    if st.sidebar.button("2. RFP 문서 재구성 실행", disabled=(st.session_state.stage > 1)):
        # 함수 호출 변경
        reorganized_text = reorganize_rfp_text(st.session_state.raw_text)
        if reorganized_text:
            st.session_state.reorganized_text = reorganized_text # 세션 상태 변수명 변경
            st.session_state.stage = 2
            st.rerun()

if st.session_state.stage >= 2:
    st.sidebar.success("✓ 2단계: 문서 재구성 완료")
    st.sidebar.header("결과 다운로드")
    st.sidebar.download_button(
        label="📥 재구성된 텍스트 다운로드 (.md)",
        data=st.session_state.reorganized_text.encode('utf-8'),
        file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_reorganized.md",
        mime="text/markdown"
    )

# --- 4. 메인 화면 UI 렌더링 ---
if st.session_state.stage < 1:
    st.warning("사이드바에서 분석할 파일을 업로드해주세요.")
else:
    tab1, tab2 = st.tabs(["RFP 원본 텍스트", "재구성된 텍스트"])

    with tab1:
        st.text_area("RFP 원본", st.session_state.get("raw_text", ""), height=500)

    with tab2:
        if st.session_state.stage < 2:
            st.info("사이드바에서 'RFP 문서 재구성 실행' 버튼을 눌러주세요.")
        else:
            st.markdown(st.session_state.get("reorganized_text", ""))


