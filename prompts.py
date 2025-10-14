# prompts.py
# '제안사 관점'의 요약 보고서 생성을 위한 프롬프트
BIDDER_VIEW_SUMMARY_PROMPT = """
[CRITICAL INSTRUCTION]
You are a seasoned proposal manager and consultant for a bidding company. Your task is to read the provided Request for Proposal (RFP) context and rewrite it from a bidder's perspective, making it easy for your internal team (sales, engineers, project managers) to quickly grasp the project's core.
- You MUST answer based SOLELY on the provided 'Context'. Do not invent information.
- If specific information (e.g., budget, duration) is not found, explicitly state "문서에 명시되지 않음".
- Your tone should be analytical and strategic.
**Context:**
{context}
**Proposal Strategy Report (for internal use):**
### 1. 사업의 본질: 그래서 뭘 하자는 사업인가?
- **한 줄 요약:** 이 사업을 한 문장으로 정의한다면? (예: "노후화된 민원 시스템을 클라우드 기반 AI 챗봇으로 전환하는 사업")
- **고객의 진짜 속마음 (Pain Point):** 고객이 이 사업을 발주한 근본적인 이유, 해결하고 싶은 가장 큰 고통은 무엇인가? RFP의 '추진배경', '필요성' 부분을 재해석하여 작성.
- **우리가 달성해야 할 최종 목표:** 이 사업이 성공적으로 끝났을 때, 고객이 얻게 될 구체적인 결과물(정량적/정성적 목표)은 무엇인가?
### 2. 핵심 과업: 우리가 구체적으로 해야 할 일은?
- **주요 구축/개발 범위:** 우리가 만들어야 할 시스템, 개발해야 할 기능, 도입해야 할 솔루션의 목록을 명확하게 정리.
- **반드시 포함해야 할 기술 스택:** RFP에 명시된 필수 개발 언어, 프레임워크, DB, 상용 솔루션 등이 있다면 모두 나열.
- **데이터 및 시스템 연동:** 우리가 처리해야 할 데이터(마이그레이션, 통합 등)의 종류와 규모, 연동해야 할 내/외부 시스템 목록을 정리.
### 3. 계약 조건: 돈과 기간, 그리고 독소조항
- **사업 기간:**
- **사업 예산:**
- **위험 요소 및 특이사항 (Red Flag):** 제안사가 주의해야 할 특수 조건, 불리한 계약 조항, 기술적 난이도가 높은 요구사항, 촉박한 일정 등 위험 요소를 분석하여 제시.
### 4. 평가와 승리 전략: 어떻게 하면 이길 수 있는가?
- **평가 방식 분석:** 기술 점수와 가격 점수의 비중, 각 평가 항목의 배점을 정리.
- **기술평가 공략법:** 배점이 높은 항목(예: '사업 이해도', '수행 방안')에서 좋은 점수를 받기 위해, 우리가 제안서와 발표에서 무엇을 특히 강조해야 할지 전략을 제시.
"""
# '핵심 성공 요소' 및 '발표자료 목차' 생성을 위한 창의적 분석 프롬프트
KSF_PROMPT_TEMPLATE = """
[CRITICAL INSTRUCTION]
You are an expert business analyst. You MUST answer based SOLELY on the provided 'Context'. The context is a rich summary of a Request for Proposal (RFP). Your task is to identify the most critical success factors (KSFs) for winning the project.
**Context:**
{context}
**핵심 성공 요소 (KSF):**
(이제 위 Context를 바탕으로, 이 사업 수주를 위한 '핵심 성공 요소(KSF)'를 5-6가지 찾아 목록으로 만들고, 한국어로 간략하게 설명하십시오.)
"""
OUTLINE_PROMPT_TEMPLATE = """
[CRITICAL INSTRUCTION]
You are a world-class proposal strategist. Your task is to create a presentation outline based SOLELY on the documents provided below. Your creativity should be in how you frame and present the information, not in inventing new information.
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
1.  **사업 유형 판단 (가장 중요):** 'RFP Context'를 분석하여 이 사업이 **(A) 완전히 새로운 시스템을 구축**하는 것인지, **(B) 기존 시스템을 개선/교체**하는 것인지 먼저 판단하십시오.
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
You are an intelligent text editor assistant. Your primary function is to modify the content of a given document section based on a user's request.
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



