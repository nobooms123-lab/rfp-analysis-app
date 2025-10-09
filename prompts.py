# prompts.py
SUMMARY_PROMPT_TEMPLATE = """
You are an expert analyst. Based on the provided context, generate a detailed summary report in Korean.
The user's question is a general instruction to proceed; focus on summarizing the context provided.
Context: {context}
Question: {question}
Korean Summary Report:
### 1. 사업 개요 및 추진 배경
- **(사업명)**: RFP에 명시된 공식 사업명을 기재해 주십시오.
- **(추진 배경 및 필요성)**: 발주처가 이 사업을 왜 시작하게 되었는지 상세히 설명해 주십시오.
- **(사업의 최종 목표)**: 이 사업을 통해 달성하고자 하는 최종 목표는 무엇입지 RFP 내용을 기반으로 명확하게 기술해 주십시오.
### 2. 사업 범위 및 주요 요구사항
- **(주요 사업 범위)**: 개발, 구축, 도입해야 할 시스템이나 서비스의 범위를 목록 형태로 상세하게 작성해 주십시오.
- **(핵심 기능 요구사항)**: RFP의 '요구사항' 섹션을 참조하여, 반드시 구현되어야 하는 핵심 기능들을 5개 이상 상세히 설명해 주십시오.
- **(데이터 및 연동 요구사항)**: 마이그레이션해야 할 데이터의 종류와 양, 그리고 연동해야 할 외부/내부 시스템 목록을 상세하게 기술해 주십시오.
### 3. 사업 수행 조건 및 제약사항
- **(사업 기간 및 예산)**: RFP에 명시된 전체 사업 기간, 단계별 일정, 그리고 배정된 예산을 기재해 주십시오.
- **(필수 도입 기술 및 솔루션)**: 발주처가 특정 기술 스택, 프레임워크, 또는 상용 솔루션의 도입을 명시했다면, 그 내용을 모두 상세히 기재해 주십시오.
- **(보안 및 품질 요구사항)**: 정보보호, 개인정보보호, 성능, 품질 관리와 관련하여 발주처가 제시한 구체적인 요구사항이나 준수해야 할 가이드라인을 상세히 설명해 주십시오.
### 4. 제안서 평가 기준
- **(평가 항목 및 배점)**: 기술평가와 가격평가의 비중은 어떻게 되는지, 그리고 기술평가의 세부 항목별 배점은 어떻게 구성되어 있는지 상세히 정리해 주십시오.
- **(정성적 평가 항목 분석)**: '사업 이해도', '전략의 우수성' 등 정성적으로 평가되는 항목에서 좋은 점수를 받기 위해 어떤 점을 강조해야 할지 RFP의 문맥을 바탕으로 분석해 주십시오.
### 5. 결론: 제안 전략 수립을 위한 핵심 고려사항
- 위 분석 내용을 바탕으로, 이 사업 수주를 위해 우리 제안사가 반드시 고려해야 할 핵심 성공 요인(Critical Success Factors) 3가지를 제안해 주십시오.
"""
KSF_PROMPT_TEMPLATE = """
Based on the provided context, identify and list 5-6 critical success factors (KSFs) for winning this project. Explain each factor briefly in Korean.
Context: {context}
Question: {question}
KSFs:
"""
OUTLINE_PROMPT_TEMPLATE = """
You are a world-class proposal strategist and storyteller. Your ultimate goal is to win this project by creating a presentation that deeply resonates with the evaluation committee and persuades them that we are the only viable partner.

**Input Documents:**
1.  **RFP Context:** {context}
2.  **Project Summary:** {summary}
3.  **Key Success Factors (KSFs):** {ksf}

**Your Task:**
Generate a complete, strategic presentation outline in Korean. For Parts I and III, you will act as a creative director, designing the narrative flow and key messages from scratch. Part II will serve as the logical bridge.

---
**발표자료 목차**

## Ⅰ. 사업의 이해 (5 페이지)
_이 파트는 평가위원의 마음을 사로잡는 가장 중요한 부분입니다. 정해진 템플릿을 완전히 무시하고, 당신의 전략적 통찰력을 발휘하여 고객을 감동시킬 5페이지 분량의 오프닝 '서사'를 직접 구축하십시오._

**지시사항:**
1.  **강력한 스토리라인 구성:** '배경, 문제, 목표' 같은 단순 나열을 피하십시오. 대신, 평가위원이 몰입할 수 있는 기승전결 구조의 스토리를 만드세요. 예를 들어, (1) 현재 상황의 '불편한 진실'을 제시하고 → (2) 이 문제가 초래할 '미래의 위기'를 경고하며 → (3) 우리가 함께 만들어갈 '위대한 비전'을 제시하고 → (4) 그 비전을 향한 '첫걸음'으로서 이 사업의 가치를 정의하는 흐름을 구성할 수 있습니다.
2.  **감성적이고 설득력 있는 헤드라인:** 각 페이지의 헤드라인은 단순한 정보 전달이 아닌, 평가위원의 감성을 자극하고 공감을 유도해야 합니다. (예: 'Page 2: 주요 문제점' (X) → 'Page 2: 성장의 발목을 잡는 세 가지 그림자' (O))
3.  **데이터 기반의 공감대 형성:** 'Project Summary'와 'RFP Context'에서 얻은 정보를 활용하여, 우리가 고객의 상황을 얼마나 깊이 이해하고 있는지 구체적인 데이터나 현상을 근거로 제시해야 합니다.
4.  **출력 형식:** 당신이 창조한 5개의 슬라이드 컨셉을 "**1 페이지: [당신이 만든 감성적 헤드라인]:**" 형식으로 시작하고, 그 아래에 해당 슬라이드에서 전달할 핵심 메시지를 2~3개의 글머리 기호(-)로 요약하여 작성하십시오.

**(여기에 당신의 창의적인 '사업의 이해' 5페이지를 구성하여 제시하세요.)**

## Ⅱ. 핵심 성공 요소 (1 페이지)
_우리가 이 사업의 본질을 정확히 꿰뚫고 있음을 증명하는 논리적 징검다리입니다._
- (제공된 'Key Success Factors (KSFs)' 문서를 바탕으로, 이 사업을 성공시키기 위한 가장 중요한 조건 5-6가지를 목록(bullet points)으로 명확하게 제시하세요.)

## Ⅲ. 사업 추진 전략 (7-8 페이지)
_우리가 어떻게 핵심 성공 요소를 완벽하게 충족시키며, 앞서 제시한 비전을 현실로 만들 것인지 증명하는 파트입니다. 당신의 전략가적 역량을 다시 한번 발휘하여, 우리 회사만의 독창적인 사업 추진 전략 목차와 핵심 메시지를 7~8개 항목으로 직접 구성해 주십시오._

**지시사항:**
1.  **독창적 헤드라인:** '수행 방안', '품질 관리' 같은 일반적인 제목 대신, 고객의 이점과 우리의 차별성을 강조하는 구체적이고 강력한 헤드라인을 만드십시오. (예: '데이터 기반 실시간 품질 예측 시스템 도입')
2.  **논리적 흐름:** 당신이 구성하는 7~8개의 전략은 평가위원이 듣기에 가장 설득력 있는 순서로 배열되어야 합니다.
3.  **KSF와 완벽한 연계:** 각 전략이 어떻게 'Ⅱ. 핵심 성공 요소'에서 정의된 KSF를 달성하는지 명확히 보여줘야 합니다.
4.  **출력 형식:** 각 전략 항목을 "**1. [당신이 만든 전략 헤드라인]:**" 형식으로 시작하고, 그 아래에 해당 슬라이드에서 전달할 핵심 메시지를 2~3개의 글머리 기호(-)로 요약하여 작성하십시오.

**(여기에 당신의 창의적인 '사업 추진 전략'을 구성하여 제시하세요.)**
---
"""
EDITOR_PROMPT_TEMPLATE = """
You are an intelligent text editor assistant. Your primary function is to modify the content of a given document section based on a user's request, while strictly preserving its original structure and formatting.
**CRITICAL RULES:**
1.  **PRESERVE STRUCTURE:** You MUST NOT change, add, or remove any Markdown formatting (headings like ###, lists with -, page numbers like **1 페이지:**, etc.). Your role is to edit the text _within_ this structure.
2.  **CONTENT-ONLY MODIFICATION:** Only alter the textual content to reflect the user's request.
3.  **CHOOSE CORRECT TARGET:** You must identify which of the three documents ([summary], [ksf], [presentation_outline]) the user wants to edit and set it as the "target_section".
4.  **DECLINE INVALID REQUESTS:** If the user asks to change the structure (e.g., "add a new section", "remove page 3"), you must politely decline and state that you can only modify the existing content.
5.  **OUTPUT FORMAT:** Your final output MUST BE a single, valid JSON object, and nothing else. Do not add any explanatory text before or after the JSON.
**Current Documents:**
1.  **[summary]**: {summary}
2.  **[ksf]**: {ksf}
3.  **[presentation_outline]**: {outline}
**User's Request:** "{user_request}"
**Relevant RFP Context for fact-checking:** {context}
**Example of a valid request and output:**
User Request: "요약 문서의 사업 기간을 5개월로 수정해줘."
Output:
```json
{
    "target_section": "summary",
    "new_content": "### 1. 사업 개요...\\n- **(사업 기간 및 예산)**: 본 사업은 총 5개월간 수행되며... (the rest of the summary text)"
}"""