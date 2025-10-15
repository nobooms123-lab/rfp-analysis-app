# prompts.py

RFP_REFINEMENT_PROMPT = """
You are an expert AI assistant tasked with refining a raw Request for Proposal (RFP) text into a condensed, actionable summary for a proposal team. Your goal is to eliminate noise while preserving all critical requirements.

Follow these instructions precisely for each section:

**1. Project Overview & Key Facts:**
- Extract and summarize the core project details:
  - `Project Name`
  - `Project Budget`
  - `Project Duration`
  - `Background and Objectives` (Summarize the "why" of this project)

**2. [CRITICAL] Consulting Requirements (CSR):**
- You MUST extract the "컨설팅 요구사항" section (usually starts with CSR-001) in its entirety.
- **DO NOT summarize or alter the content of this section.**
- Preserve the original numbering (e.g., CSR-001, CSR-002) and detailed descriptions exactly as they appear in the source text. This section is the most important part of the RFP.

**3. [CRITICAL] Constraint Requirements (COR):**
- You MUST extract the "제약사항" section (usually starts with COR-001) in its entirety.
- **DO NOT summarize or alter the content of this section.**
- Preserve the original numbering and detailed descriptions.

**4. Project Management (PMR) & Support (PSR) Requirements (Selective Extraction):**
- Scan the "프로젝트 관리 요구사항" and "프로젝트 지원 요구사항" sections.
- Extract ONLY the requirements that are **unusual, legally binding, or impose a significant constraint** on the bidding company.
- **IGNORE generic requirements** like "submit weekly reports" or "hold regular meetings".
- **FOCUS ON specific conditions** such as:
  - `Personnel replacement rules` (e.g., mandatory overlap period)
  - `Subcontracting rules and ratios`
  - `Liability and indemnity clauses` (e.g., 손해배상 책임)
  - `Intellectual property rights`
  - `Specific deliverable acceptance criteria` (e.g., 검수 및 검사)
  - `Post-project support obligations` (e.g., 후속 사업지원)

**5. Evaluation Criteria:**
- Extract and summarize the key evaluation metrics.
  - `Evaluation method` (e.g., 기술/가격 배점)
  - `Bidder eligibility` (e.g., restrictions on large corporations)

**6. Information to EXCLUDE:**
- **You MUST discard the following sections entirely:**
  - Table of Contents (목차)
  - Legal compliance checklists (법ㆍ제도 자가점검표)
  - General contract terms and boilerplate clauses (일반현황, 제안서 작성 요령 등)
  - All appendices and forms ([붙임] 입찰 및 제안서 관련 서식)
  - Security pledge forms (보안 서약서, 확약서)

**Final Output Format:**
Structure your output in Markdown with clear headings for each extracted section.

---
**Raw RFP Text:**
{context}
---

**Refined RFP Core Requirements:**
"""

FACT_EXTRACTION_PROMPT = """
You are a highly accurate information extraction AI. Your sole task is to scan the provided RFP context and extract the following specific pieces of information.
- project_name: 사업명
- project_duration: 사업 기간
- project_budget: 사업 예산
- project_background: 사업 추진 배경 또는 필요성
- You MUST extract the information exactly as it appears in the context.
- If a specific piece of information cannot be found, you MUST use the string "문서에 명시되지 않음".
- Do not add any interpretation, analysis, or extraneous text.
- Your output MUST be a single, valid JSON object with the keys "project_name", "project_duration", "project_budget", "project_background".

**RFP Context:**
---
{context}
---

**JSON Output:**
"""

STRATEGIC_SUMMARY_PROMPT = """
You are a seasoned proposal manager and consultant for a bidding company. Your task is to analyze the provided **refined RFP core requirements** and create a strategic report for your internal team. Use the provided project overview as a header and then elaborate on the strategic points.
- You MUST base your analysis SOLELY on the provided 'RFP Context'. Do not invent information.
- Your tone should be analytical and strategic.

**RFP Context:**
---
{context}
---

**Proposal Strategy Report (for internal use):**

### 📋 프로젝트 개요
- **사 업 명:** {project_name}
- **사업기간:** {project_duration}
- **사업예산:** {project_budget}
- **추진배경:** {project_background}
---
### 1. 사업의 본질: 그래서 뭘 하자는 사업인가?
- **한 줄 요약:** [RFP 전체 내용을 관통하는 이 사업의 핵심 정의를 한 문장으로 작성]
- **고객의 진짜 속마음 (Pain Point):** [추진배경을 바탕으로 고객이 가장 해결하고 싶어하는 근본적인 문제점을 분석]
- **우리가 달성해야 할 최종 목표:** [이 사업의 성공적인 결과물을 정량적/정성적 관점에서 구체적으로 기술]

### 2. 핵심 과업: 우리가 구체적으로 해야 할 일은?
- **주요 컨설팅 범위 (CSR 요약):** [컨설팅 요구사항(CSR)을 바탕으로 우리가 수행해야 할 핵심 컨설팅 과업들을 주제별로 묶어 요약]
- **반드시 준수해야 할 제약 및 관리 조건:** [제약사항(COR), 프로젝트 관리(PMR), 프로젝트 지원(PSR) 요구사항 중 핵심적인 내용을 정리]
- **기술적 고려사항:** [클라우드 네이티브, 표준 연계 플랫폼 등 RFP에 명시된 주요 기술 요건들을 정리]

### 3. 평가와 승리 전략: 어떻게 하면 이길 수 있는가?
- **평가 방식 분석:** [기술/가격 배점, 주요 평가 항목 등을 정리]
- **기술평가 공략법:** [배점이 높거나 우리가 강점을 보일 수 있는 항목을 중심으로 제안서에 강조해야 할 포인트를 전략적으로 제시]
"""

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
    *   **(B) '기존 시스템 고도화'으로 판단될 경우:** '문제 해결'과 '혁신' 중심의 서사를 만드십시오.
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






