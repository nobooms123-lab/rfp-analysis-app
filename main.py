# main.py

import streamlit as st
from utils import extract_text_from_file, create_vector_db, generate_all_reports

st.set_page_config(page_title="RFP 자동 분석 보고서", layout="wide")
st.title("RFP 자동 분석 보고서 📄")
st.info("RFP 파일을 업로드하고 '분석 시작' 버튼을 누르면, 전문가 관점의 심층 분석 보고서 3종이 자동 생성됩니다.")

# --- 1. 사이드바: 파일 업로드 및 제어 ---
with st.sidebar:
    st.header("1. 분석 대상 파일")
    uploaded_file = st.file_uploader(
        "PDF 또는 TXT 형식의 RFP 파일을 업로드하세요.",
        type=["pdf", "txt"]
    )

    # [수정] 파일이 업로드되면 텍스트를 즉시 추출하고 세션에 저장
    if uploaded_file:
        # 파일이 변경되면 기존 분석 결과 초기화
        if st.session_state.get("uploaded_filename") != uploaded_file.name:
            keys_to_clear = ['vector_db', 'risk_report', 'ksf_report', 'outline_report', 'analysis_done', 'raw_text', 'source_file_type']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.session_state.uploaded_filename = uploaded_file.name
            # [추가] 원본 텍스트와 파일 타입을 세션에 저장
            st.session_state.raw_text = extract_text_from_file(uploaded_file)
            st.session_state.source_file_type = uploaded_file.type

    # [추가] OCR 텍스트 다운로드 버튼 (PDF 파일일 경우에만 표시)
    if st.session_state.get("source_file_type") == "application/pdf" and st.session_state.get("raw_text"):
        st.download_button(
            label="📥 OCR 원본 텍스트 다운로드",
            data=st.session_state.raw_text.encode('utf-8'),
            file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_ocr.txt",
            mime="text/plain"
        )

    st.header("2. 분석 실행")
    # [수정] 버튼 활성화 조건을 'uploaded_file' 존재 여부로 변경
    if st.button("분석 시작", type="primary", disabled=(not uploaded_file or st.session_state.get('analysis_done', False))):
        # [수정] 세션에 저장된 raw_text를 사용
        if st.session_state.get("raw_text"):
            st.session_state.vector_db = create_vector_db(st.session_state.raw_text)
            
            if st.session_state.vector_db:
                # 3가지 리포트 생성
                risk, ksf, outline = generate_all_reports(st.session_state.vector_db)
                st.session_state.risk_report = risk
                st.session_state.ksf_report = ksf
                st.session_state.outline_report = outline
                st.session_state.analysis_done = True
                st.rerun()
        else:
            st.error("파일에서 텍스트를 추출하지 못했습니다. 다른 파일을 시도해주세요.")


# --- 2. 메인 화면: 분석 결과 표시 ---
if not st.session_state.get("analysis_done"):
    st.warning("왼쪽 사이드바에서 파일을 업로드하고 '분석 시작' 버튼을 눌러주세요.")
else:
    tab1, tab2, tab3 = st.tabs([
        "📊 리스크 분석",
        "🔑 핵심 성공 요소 (KSF)",
        "📑 발표자료 목차 초안"
    ])

    with tab1:
        st.header("제안사 관점의 사업 리스크 분석")
        st.markdown(st.session_state.risk_report)

    with tab2:
        st.header("핵심 성공 요소(KSF) 및 실행 전략")
        st.markdown(st.session_state.ksf_report)

    with tab3:
        st.header("제안 발표자료 목차 초안")
        st.markdown(st.session_state.outline_report)


