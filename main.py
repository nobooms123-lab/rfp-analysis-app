# main.py

import streamlit as st
# get_vector_db_from_text 함수를 새로 import 합니다.
from utils import get_vector_db, get_vector_db_from_text, generate_summary, generate_creative_reports, to_excel

# --- 1. 기본 설정 및 초기화 ---
st.set_page_config(page_title="RFP 분석 및 제안 전략 도우미", layout="wide")
st.title("RFP 분석 및 제안 전략 수립 도우미")

# 세션 상태 초기화
if 'stage' not in st.session_state:
    st.session_state.stage = 0  # 0: 초기, 1: 분석준비완료, 2: 요약완료, 3: 전체완료
if 'source_type' not in st.session_state:
    st.session_state.source_type = None # 입력 소스 추적 (pdf 또는 text)

# --- 2. 사이드바 구성 (입력 방식 선택) ---
st.sidebar.title("분석 프로세스")

# 입력 방식을 선택하기 위한 탭 생성
pdf_tab, text_tab = st.sidebar.tabs(["📄 PDF 업로드", "✍️ 텍스트 입력"])

# --- 2-1. PDF 업로드 탭 ---
with pdf_tab:
    uploaded_file = st.file_uploader("1. 분석할 RFP PDF 파일 업로드", type="pdf")

    # 새 PDF 파일이 업로드되면 모든 상태 초기화
    if uploaded_file and st.session_state.get("uploaded_filename") != uploaded_file.name:
        st.session_state.clear() # 모든 세션 상태 초기화
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.stage = 0
        st.session_state.source_type = "pdf" # 소스 타입을 pdf로 지정

    # Stage 0 -> 1: PDF 파일 업로드 시 OCR 및 벡터 DB 생성 수행
    if st.session_state.source_type == "pdf" and uploaded_file and st.session_state.stage == 0:
        st.session_state.vector_db, st.session_state.ocr_text = get_vector_db(uploaded_file)
        if st.session_state.vector_db and st.session_state.ocr_text:
            st.session_state.stage = 1
            st.rerun()

# --- 2-2. 텍스트 입력 탭 ---
with text_tab:
    input_text = st.text_area("1. 분석할 RFP 텍스트를 붙여넣으세요.", height=300)
    
    if st.button("텍스트로 분석 시작"):
        if input_text:
            st.session_state.clear() # 모든 세션 상태 초기화
            st.session_state.source_type = "text" # 소스 타입을 text로 지정
            st.session_state.uploaded_filename = "text_input.txt" # 다운로드 파일명용
            
            # Stage 0 -> 1: 텍스트로 벡터 DB 생성 수행
            st.session_state.vector_db = get_vector_db_from_text(input_text)
            if st.session_state.vector_db:
                st.session_state.ocr_text = input_text # 입력 텍스트를 ocr_text로 저장
                st.session_state.stage = 1
                st.rerun()
        else:
            st.warning("분석할 텍스트를 입력해주세요.")

# --- 3. 단계별 실행 로직 (공통) ---

# Stage 1: 분석 준비 완료, 요약 생성 대기
if st.session_state.stage >= 1:
    st.sidebar.success("✓ 1단계: 분석 준비 완료")

    # [개선] OCR 텍스트 다운로드 기능 추가 (PDF로 입력했을 경우에만 표시)
    if st.session_state.source_type == "pdf":
        st.sidebar.download_button(
            label="📥 OCR 텍스트 다운로드",
            data=st.session_state.ocr_text.encode('utf-8'),
            file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_ocr.txt",
            mime="text/plain"
        )
    
    if st.sidebar.button("2. 제안사 관점 요약 생성", disabled=(st.session_state.stage > 1)):
        summary = generate_summary(st.session_state.vector_db)
        if summary:
            st.session_state.summary = summary
            st.session_state.stage = 2
            st.rerun()

# Stage 2: 요약 완료, KSF/목차 생성 대기
if st.session_state.stage >= 2:
    st.sidebar.success("✓ 2단계: 요약 생성 완료")
    if st.sidebar.button("3. KSF 및 발표 목차 생성", disabled=(st.session_state.stage > 2)):
        ksf, outline = generate_creative_reports(st.session_state.vector_db, st.session_state.summary)
        if ksf and outline:
            st.session_state.ksf = ksf
            st.session_state.presentation_outline = outline
            st.session_state.stage = 3
            st.rerun()

# Stage 3: 모든 작업 완료
if st.session_state.stage == 3:
    st.sidebar.success("✓ 3단계: 모든 분석 완료!")
    st.sidebar.header("결과 다운로드")
    excel_data = to_excel(st.session_state.summary, st.session_state.ksf, st.session_state.presentation_outline)
    st.sidebar.download_button(
        label="📥 전체 결과 Excel 다운로드",
        data=excel_data,
        file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- 4. 메인 화면 UI 렌더링 ---
if st.session_state.stage == 0:
    st.info("사이드바에서 PDF를 업로드하거나 텍스트를 입력하면 분석이 시작됩니다.")

# 결과 탭 구성 (분석 준비 완료 후 항상 보이도록)
if st.session_state.stage >= 1:
    tabs = st.tabs(["제안서 요약", "핵심 성공 요소", "발표자료 목차", "입력 원본 텍스트"])

    with tabs[0]:
        if 'summary' in st.session_state:
            st.markdown(st.session_state.summary)
        else:
            st.info("2단계 '제안사 관점 요약 생성'을 실행해주세요.")

    with tabs[1]:
        if 'ksf' in st.session_state:
            st.markdown(st.session_state.ksf)
        else:
            st.info("3단계 'KSF 및 발표 목차 생성'을 실행해주세요.")

    with tabs[2]:
        if 'presentation_outline' in st.session_state:
            st.markdown(st.session_state.presentation_outline)
        else:
            st.info("3단계 'KSF 및 발표 목차 생성'을 실행해주세요.")

    with tabs[3]:
        if 'ocr_text' in st.session_state:
            st.text_area("추출/입력된 전체 텍스트", st.session_state.ocr_text, height=400)
        else:
            st.info("PDF 파일을 업로드하거나 텍스트를 입력해주세요.")
