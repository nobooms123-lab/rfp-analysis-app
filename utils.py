import streamlit as st
from openai import OpenAI
import logging

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------
# 1️⃣ OpenAI LLM 초기화 함수
# ------------------------------------
@st.cache_resource
def init_openai_llm(temperature: float = 0.2, model: str = "gpt-4o-mini"):
    """
    OpenAI LLM 초기화
    - Streamlit secrets에서 API 키 로드
    - temperature와 모델명 지정 가능
    """
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
        client = OpenAI(api_key=api_key)
        logger.info(f"✅ OpenAI 클라이언트 초기화 완료 (model={model})")
        return lambda prompt: client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        ).choices[0].message.content

    except Exception as e:
        logger.error(f"❌ OpenAI 모델 초기화 중 오류: {e}")
        st.error("OpenAI 모델 초기화 중 오류 발생. secrets.toml 설정을 확인하세요.")
        raise e


# ------------------------------------
# 2️⃣ RFP 텍스트 정제 함수
# ------------------------------------
@st.cache_data(show_spinner="RFP 텍스트 정제 중...")
def refine_rfp_text(raw_text: str, run_id: str = "default"):
    """
    입력받은 RFP 텍스트를 GPT 모델로 정제
    """
    try:
        llm = init_openai_llm(temperature=0)
        prompt = f"""
        아래의 RFP 원문을 명확하고 간결하게 정리해줘.
        문장 표현은 공식 보고서 수준으로 다듬되, 의미는 유지해야 해.

        원문:
        {raw_text}
        """
        refined = llm(prompt)
        return refined.strip()

    except Exception as e:
        logger.error(f"❌ RFP 텍스트 정제 실패: {e}")
        st.error("RFP 텍스트 정제 중 오류가 발생했습니다. 로그를 확인하세요.")
        return "오류: 텍스트 정제 실패"


# ------------------------------------
# 3️⃣ 요약 기능 예시
# ------------------------------------
@st.cache_data(show_spinner="요약 생성 중...")
def summarize_text(raw_text: str):
    """
    텍스트 요약 함수 예시
    """
    llm = init_openai_llm(temperature=0)
    prompt = f"""
    다음 내용을 3문장 이내로 핵심만 요약해줘:
    {raw_text}
    """
    return llm(prompt)
