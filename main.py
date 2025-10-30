import streamlit as st
import json
import re
from utils import get_vector_db, generate_summary, generate_creative_reports, to_excel # handle_chat_interaction

--- 1. 기본 설정 및 초기화 ---
st.set_page_config(page_title="대화형 제안서 분석 도우미", layout="wide")
st.title("RFP 분석 및 제안 전략 수립 도우미")

세션 상태 초기화
if 'stage' not in st.session_state:
st.session_state.stage = 0 # 0: 초기, 1: OCR완료, 2: 요약완료, 3: 전체완료

--- 2. 사이드바 구성 ---
st.sidebar.title("분석 프로세스")
uploaded_file = st.sidebar.file_uploader("1. 분석할 RFP PDF 파일 업로드", type="pdf")

파일이 변경되면 모든 상태 초기화
if uploaded_file and st.session_state.get("uploaded_filename") != uploaded_file.name:
st.session_state.clear()
st.session_state.uploaded_filename = uploaded_file.name
st.session_state.stage = 0

--- 3. 단계별 실행 로직 ---
Stage 0 -> 1: 파일 업로드 시 OCR 수행
if uploaded_file and st.session_state.stage == 0:
st.session_state.vector_db, st.session_state.ocr_text = get_vector_db(uploaded_file)
if st.session_state.vector_db and st.session_state.ocr_text:
st.session_state.stage = 1
st.rerun()

Stage 1: OCR 완료, 요약 생성 대기
if st.session_state.stage >= 1:
st.sidebar.success("✓ 1단계: 텍스트 추출 완료")
if st.sidebar.button("2. 제안사 관점 요약 생성", disabled=(st.session_state.stage > 1)):
run_id = st.session_state.get('run_id', 0)
summary = generate_summary(st.session_state.vector_db, run_id=run_id)
if summary:
st.session_state.summary = summary
st.session_state.stage = 2
st.rerun()

Stage 2: 요약 완료, KSF/목차 생성 대기
if st.session_state.stage >= 2:
st.sidebar.success("✓ 2단계: 요약 생성 완료")
if st.sidebar.button("3. KSF 및 발표 목차 생성", disabled=(st.session_state.stage > 2)):
run_id = st.session_state.get('run_id', 0)
ksf, outline = generate_creative_reports(st.session_state.vector_db, st.session_state.summary, run_id=run_id)
if ksf and outline:
st.session_state.ksf = ksf
st.session_state.presentation_outline = outline
st.session_state.stage = 3
st.rerun()

Stage 3: 모든 작업 완료
if st.session_state.stage == 3:
st.sidebar.success("✓ 3단계: 모든 분석 완료!")

--- 4. 메인 화면 UI 렌더링 ---
if st.session_state.stage == 0:
st.info("사이드바에서 RFP PDF 파일을 업로드하면 분석이 시작됩니다.")

결과 탭 구성
tabs = st.tabs(["제안서 요약", "핵심 성공 요소", "발표자료 목차", "OCR 원본 텍스트"])
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
st.text_area("추출된 전체 텍스트", st.session_state.ocr_text, height=400)
else:
st.info("PDF 파일을 먼저 업로드해주세요.")

다운로드 버튼 (모든 분석 완료 시에만 활성화)
if st.session_state.stage == 3:
st.sidebar.header("결과 다운로드")
excel_data = to_excel(st.session_state.summary, st.session_state.ksf, st.session_state.presentation_outline)
st.sidebar.download_button(
label="📥 전체 결과 Excel 다운로드", data=excel_data,
file_name=f"{st.session_state.uploaded_filename.split('.')[0]}_analysis.xlsx",
mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
