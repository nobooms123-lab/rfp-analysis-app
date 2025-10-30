# prompts.py

# 현재 코드에서는 사용되지 않음 (향후 기능 확장용)
FACT_EXTRACTION_PROMPT = """
You are a highly accurate information extraction AI. Your sole task is to scan the provided RFP context and extract the following specific pieces of information.
*   project_name: 사업명
*   project_duration: 사업 기간
*   project_budget: 사업 예산
*   project_background: 사업 추진 배경 또는 필요성
*   You MUST extract the information exactly as it appears in the context.
*   If a specific piece of information cannot be found, you MUST use the string "문서에 명시되지 않음".
*   Do not add any interpretation, analysis, or extraneous text.
*   Your output MUST be a single, valid JSON object with the keys "project_name", "project_duration", "project_budget", "project_background".

**RFP Context:**
***
{context}
***

**JSON Output:**
"""

# utils.py의 generate_summary 함수에서 사용
BIDDER_VIEW_SUMMARY_PROMPT = """
You are a seasoned proposal manager and consultant for a bidding company. Your task is to read the provided Request for Proposal (RFP) context and create a strategic report for your internal team (sales, engineers, project managers).

*   You MUST answer based SOLELY on the provided 'Context'. Do not invent information.
*   Your tone should be analytical and strategic.

**RFP Context:**
***
{context}
***

**Proposal Strategy Report (for internal use):**

### 1. 사업의 본질: 그래서 뭘 하자는 사업인가?
*   **한 줄 요약:** 
*   **고객의 진짜 속마음 (Pain Point):** 
*   **우리가 달성해야 할 최종 목표:** 

### 2. 핵심 과업: 우리가 구체적으로 해야 할 일은?
*   **주요 구축/개발 범위:** 
*   **반드시 포함해야 할 기술 스택:** 
*   **데이터 및 시스템 연동:** 

### 3. 계약 조건: 돈과 기간, 그리고 독소조항
*   **사업 기간:** 
*   **사업 예산:** 
*   **위험 요소 및 특이사항 (Red Flag):** 

### 4. 평가와 승리 전략: 어떻게 하면 이길 수 있는가?
*   **평가 방식 분석:** 
*   **기술평가 공략법:** 
"""

# utils.py의 generate_creative_reports 함수에서 사용
KSF_PROMPT_TEMPLATE = """
You are a top-tier strategy consultant. Based on the provided RFP context, identify the 3 to 5 most critical Key Success Factors (KSFs) to win this project. 
Present them as a bulleted list with a brief explanation for each. Focus on what will truly differentiate the winning proposal.

**RFP Context:**
***
{context}
***

**Key Success Factors (KSFs):**
*   **KSF 1:** [KSF 제목]
    *   [설명]
*   **KSF 2:** [KSF 제목]
    *   [설명]
*   **KSF 3:** [KSF 제목]
    *   [설명]
"""

# utils.py의 generate_creative_reports 함수에서 사용
OUTLINE_PROMPT_TEMPLATE = """
You are an expert presentation designer. Create a compelling presentation outline for the project proposal based on the provided RFP Summary, Key Success Factors (KSFs), and the original RFP Context. 
The outline should be logical, persuasive, and directly address the client's needs.

**RFP Summary:**
{summary}

**Key Success Factors (KSFs):**
{ksf}

**Original RFP Context:**
{context}

**Presentation Outline:**

### 1. 프로젝트에 대한 깊은 이해 (Understanding)
    - 제안 배경 및 목적의 완벽한 이해
    - 고객의 Pain Point 및 핵심 요구사항 분석

### 2. 우리의 핵심 제안 (Our Solution)
    - 제안 개요: 프로젝트 성공을 위한 우리의 약속
    - 차별화된 제안 전략 (KSF 기반)
    - 상세 구현 방안 (기술, 아키텍처 등)

### 3. 성공적인 프로젝트 수행 전략 (Execution Plan)
    - 프로젝트 관리 방안 (일정, 인력, 리스크 관리)
    - 품질 보증 및 테스트 계획
    - 기술 지원 및 교육 계획

### 4. 제안사 역량 및 비전 (Our Capability)
    - 유사 프로젝트 수행 경험
    - 우리 회사만의 강점과 비전

### 5. Q&A
"""




