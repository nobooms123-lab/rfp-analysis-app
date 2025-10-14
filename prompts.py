# prompts.py

SUMMARY_PROMPT_TEMPLATE = """
[CRITICAL INSTRUCTION]
You are a highly precise information extraction agent. Your ONLY task is to read the entire document provided in the 'Context' below and fill in the values for each item in the 'Korean Summary Report' template.
- Extract the information VERBATIM from the document as much as possible.
- If, and only if, you cannot find the specific information after reading the entire document, you MUST write "문서에서 해당 정보 찾을 수 없음".
- Do not summarize, interpret, or add any information that is not explicitly in the document.

[EXCLUSION RULE]
You must **ignore administrative and formatting instructions** for writing the proposal itself. Focus only on the project's substance.
- **Examples to Exclude:** Instructions on how to submit documents, required proposal table of contents, page limits, printing methods, submission deadlines, contact information, etc.

**Context:** 
{context}

**Korean Summary Report:**
(이제 위 Context 문서 전체를 읽고, 아래 템플릿의 각 항목에 해당하는 정보를 정확히 추출하여 기입하십시오.)

### 1. 사업 개요 및 추진 배경
- **(사업명)**: 
- **(추진 배경 및 필요성)**: 
- **(사업의 최종 목표)**: 

### 2. 사업 범위 및 주요 요구사항
- **(주요 사업 범위)**: 
- **(핵심 기능 요구사항)**: 
- **(데이터 및 연동 요구사항)**: 

### 3. 사업 수행 조건 및 제약사항
- **(사업 기간)**: 
- **(사업 예산)**: 
- **(주요 제약사항)**: (사업 수행 시 반드시 지켜야 할 제약사항이나 특수 조건이 있다면 명시하고, 없다면 '명시된 제약사항 없음'으로 기재)
    - **(필수 도입 기술 및 솔루션)**: 
    - **(보안 및 품질 요구사항)**: 

### 4. 제안서 평가 기준
- **(평가 항목 및 배점)**: 
- **(정성적 평가 항목 분석)**: 

### 5. 결론: 제안 전략 수립을 위한 핵심 고려사항
- (위 추출 내용을 바탕으로, 이 사업 수주를 위해 반드시 고려해야 할 핵심 성공 요인(Critical Success Factors) 3가지를 제안해 주십시오.)
"""

KSF_PROMPT_TEMPLATE = """
[CRITICAL INSTRUCTION]
You are an expert business analyst. Your goal is to identify the true strategic factors for winning the project. You MUST answer based SOLELY on the provided 'Context'. Do not use any external knowledge or make assumptions.

[EXCLUSION RULE]
You must **ignore administrative and formatting instructions** for writing the proposal itself. Focus only on what is strategically important to win the project.
- **Examples to Exclude:** Instructions on how to submit documents, required proposal table of contents, page limits, contract terms, etc. These are not strategic success factors.

**Context:**
{context}

**핵심 성공 요소 (KSF):**
(이제 위 Context를 바탕으로, 이 사업 수주를 위한 '핵심 성공 요소(KSF)'를 5~6가지 찾아 목록으로 만들고, 한국어로 간략하게 설명하십시오.)
"""

OUTLINE_PROMPT_TEMPLATE = """
[CRITICAL INSTRUCTION]
You are a world-class proposal strategist. Your task is to create a presentation outline based SOLELY on the documents provided below ('RFP Context', 'Project Summary', 'Key Success Factors'). Do not invent new features or strategies not supported by the input documents. Your creativity should be in how you frame and present the information, not in creating new information.

**Input Documents:**
1.  **RFP Context:** {context}
2.  **Project Summary:** {summary}
3.  **Key Success Factors (KSFs):** {ksf}

**Your Task:**
Generate a complete, strategic presentation outline in Korean.
---
**발표자료 목차**
## Ⅰ. 사업의 이해 (5 페이지)
_이 파트는 평가위원의 마음을 사로잡는 가장 중요한 부분입니다. 당신의 전략적 통찰력을 발휘하여 고객을 감동시킬 5페이지 분량의 오프닝 '서사'를 직접 구축하십시오._
**지시사항:**
1.  **사업 유형 판단 (가장 중요):** 'RFP Context'를 분석하여 이 사업이 **(A) 완전히 새로운 시스템을 구축**하는 것인지, **(B) 기존 시스템을 개선/교체**하는 것인지 먼저 판단하십시오. 이 판단은 스토리라인의 기반이 됩니다.
2.  **판단에 따른 맞춤형 스토리라인 구성:**
    *   **(A) '신규 시스템 구축'으로 판단될 경우:** '기회'와 '미래 비전' 중심의 서사를 만드십시오.
    *   **(B) '기존 시스템 고도화'로 판단될 경우:** '문제 해결'과 '혁신' 중심의 서사를 만드십시오.
3.  **감성적 헤드라인:** 각 페이지의 헤드라인은 평가위원의 공감을 유도해야 합니다.
4.  **데이터 기반 공감대 형성:** 'Project Summary'와 'RFP Context'의 정보를 활용하여, 우리가 고객의 상황을 깊이 이해하고 있음을 구체적인 근거로 제시해야 합니다.
5.  **출력 형식:** 5개 슬라이드 컨셉을 "**1 페이지: [당신이 만든 감성적 헤드라인]:**" 형식으로 시작하고, 그 아래에 핵심 메시지를 2~3개의 글머리 기호(-)로 요약하여 작성하십시오.
**(여기에 당신의 창의적인 '사업의 이해' 5페이지를 구성하여 제시하세요.)**
## Ⅱ. 핵심 성공 요소 (1 페이지)
_우리가 이 사업의 본질을 정확히 꿰뚫고 있음을 증명하는 논리적 징검다리입니다._
- (제공된 'Key Success Factors (KSFs)' 문서를 바탕으로, 이 사업을 성공시키기 위한 가장 중요한 조건 5-6가지를 목록(bullet points)으로 명확하게 제시하세요.)
## Ⅲ. 사업 추진 전략 (7-8 페이지)
_우리가 어떻게 핵심 성공 요소를 완벽하게 충족시키며, 앞서 제시한 비전을 현실로 만들 것인지 증명하는 파트입니다. 당신의 전략가적 역량을 다시 한번 발휘하여, 우리 회사만의 독창적인 사업 추진 전략 목차와 핵심 메시지를 7-8개 항목으로 직접 구성해 주십시오._
**지시사항:**
1.  **독창적 헤드라인:** '수행 방안', '품질 관리' 같은 일반적인 제목 대신, 고객의 이점과 우리의 차별성을 강조하는 구체적이고 강력한 헤드라인을 만드십시오.
2.  **논리적 흐름:** 당신이 구성하는 7~8개의 전략은 평가위원이 듣기에 가장 설득력 있는 순서로 배열되어야 합니다.
3.  **KSF와 완벽한 연계:** 각 전략이 어떻게 'Ⅱ. 핵심 성공 요소'에서 정의된 KSF를 달성하는지 명확히 보여줘야 합니다.
4.  **출력 형식:** 각 전략 항목을 "**1. [당신이 만든 전략 헤드라인]:**" 형식으로 시작하고, 그 아래에 해당 슬라이드에서 전달할 핵심 메시지를 2~3개의 글머리 기호(-)로 요약하여 작성하십시오.
**(여기에 당신의 창의적인 '사업 추진 전략'을 구성하여 제시하세요.)**
---
"""
EDITOR_PROMPT_TEMPLATE = """
You are an intelligent text editor assistant. Your primary function is to modify the content of a given document section based on a user's request, while strictly preserving its original structure and formatting.
**CRITICAL RULES:**
1.  **PRESERVE STRUCTURE:** You MUST NOT change, add, or remove any Markdown formatting.
2.  **CONTENT-ONLY MODIFICATION:** Only alter the textual content to reflect the user's request.
3.  **FACT-CHECKING:** Your modifications MUST be consistent with the provided "Relevant RFP Context".
4.  **CHOOSE CORRECT TARGET:** You must identify which of the three documents ([summary], [ksf], [presentation_outline]) the user wants to edit and set it as the "target_section".
5.  **OUTPUT FORMAT:** Your final output MUST BE a single, valid JSON object.
**Current Documents:**
1.  **[summary]**: {summary}
2.  **[ksf]**: {ksf}
3.  **[presentation_outline]**: {outline}
**User's Request:** "{user_request}"
**Relevant RFP Context for fact-checking:** {context}
"""
