"""
기획서 생성 시스템 - 핵심 모듈
"""
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from models.llm import get_llm
from agents.plan_core.schemas import (
    StructuredIdea,
    TableOfContents,
    TableOfContentsItem,
    PlanSection,
    GeneratedPlan,
    BlueprintItem,
    StructuredInput,
)
from prompts.plan_prompts import SECTION_GENERATION_SYSTEM_PROMPT, SECTION_GENERATION_USER_PROMPT
from prompts.edit_prompts import PARTIAL_EDIT_SYSTEM_PROMPT, PARTIAL_EDIT_USER_PROMPT


# ===========================
# Blueprint 기반 생성 함수
# ===========================

def generate_section_from_blueprint(
    structured_input: StructuredInput,
    blueprint_item: BlueprintItem,
    section_index: int,
    previous_sections: List[PlanSection] = None,
    evidence: List[str] = None,
    evidence_for_record: List[str] = None
) -> PlanSection:
    """
    Blueprint 항목을 기반으로 섹션을 생성합니다.
    - guideline + content(참고 컨텍스트) + 이전 섹션 컨텍스트로 LLM 생성
    - evidence가 있으면 프롬프트에 포함하여 팩트 기반 작성 유도
    """
    section_number = str(section_index + 1)
    
    # content가 없으면 LLM으로 생성
    previous_sections = previous_sections or []
    evidence = evidence or []
    
    # 전체 목차
    toc_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(structured_input.toc)])
    
    # 스타일에 따른 페르소나 매핑
    persona_map = {
        "Business": "시니어 비즈니스 전략가",
        "Service": "시니어 서비스 기획자",
        "Technical": "시니어 기술 설계자(Architect)",
        "Marketing": "시니어 마케팅 전략가",
        "Operational": "시니어 운영 프로세스 설계자"
    }
    persona = persona_map.get(structured_input.planning_style, "시니어 기획 전문가")

    # 시스템 프롬프트 생성
    system_prompt = SECTION_GENERATION_SYSTEM_PROMPT.format(
        planning_style=structured_input.planning_style,
        persona=persona,
        rationale=structured_input.rationale,
        toc_text=toc_text
    )

    guideline = blueprint_item.guideline or "자유롭게 작성"
    context_hint = blueprint_item.content or ""
    
    # 유저 프롬프트 생성
    user_prompt = SECTION_GENERATION_USER_PROMPT.format(
        section_number=section_number,
        title=blueprint_item.title,
        guideline=guideline
    )
    
    # 리서치 결과(Evidence) 추가
    if evidence:
        evidence_text = "\n".join(evidence)
        user_prompt += f"\n\n[참고용 리서치 자료] (팩트와 수치를 적극 활용하세요):\n{evidence_text}"
    
    # Blueprint 컨텍스트 추가
    if context_hint:
        user_prompt += f"\n\n[기존 기획 메모] (반드시 더 상세하게 확장할 것):\n{context_hint}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # LLM 호출
    chat = get_llm(max_tokens=8192, reasoning_effort="medium")
    response = chat.invoke(messages)
    
    # 후처리: LLM이 섹션 제목을 포함했을 경우 제거
    content = response.content.strip()
    lines = content.split('\n')
    
    # 첫 몇 줄에서 섹션 제목과 동일하거나 유사한 제목 제거
    title_keywords = blueprint_item.title.lower().replace(' ', '')
    cleaned_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 제목 줄인지 확인
        if stripped.startswith('#'):
            # 제목 텍스트 추출
            title_text = stripped.lstrip('#').strip().lower().replace(' ', '')
            # 섹션 번호나 제목과 유사한 경우 제거
            if (title_keywords in title_text or 
                title_text in title_keywords or
                title_text.startswith(section_number)):
                continue  # 이 줄 건너뛰기
        cleaned_lines.append(line)
    
    content = '\n'.join(cleaned_lines).strip()
    
    return PlanSection(
        section_number=section_number,
        title=blueprint_item.title,
        content=content,
        evidence=evidence_for_record or evidence
    )


def compose_plan_markdown(
    plan: GeneratedPlan,
    visual_artifacts: List["VisualArtifact"] = None
) -> str:
    """
    생성된 기획서를 마크다운 문서로 조합합니다.
    시각화 결과물이 있으면 해당 섹션에 포함합니다.
    """
    from agents.visual_core.schemas import VisualArtifact
    visual_artifacts = visual_artifacts or []
    visual_by_section = {v.section_number: v for v in visual_artifacts}
    
    md_parts = []
    
    # 1. 헤더 (제목, 요약, 메타 등)
    md_parts.append(format_plan_header(plan))
    
    # 2. 목차
    md_parts.append(format_plan_toc(plan))
    
    # 3. 본문 + 시각화
    for section in plan.sections:
        visual = visual_by_section.get(section.section_number)
        md_parts.append(format_section_content(section, visual))
    
    return "\n".join(md_parts)


def format_plan_header(plan: GeneratedPlan) -> str:
    """기획서 헤더 포맷팅 (제목, 요약, 구분선)"""
    parts = []
    parts.append(f"# {plan.idea.title}")
    parts.append("")
    parts.append(f"> {plan.idea.summary}")
    parts.append("")
    parts.append(f"*생성 방법: {plan.method}*")
    parts.append("")
    parts.append("---")
    parts.append("")
    return "\n".join(parts)


def format_plan_toc(plan: GeneratedPlan) -> str:
    """목차 및 가이드라인 포맷팅"""
    parts = []
    
    # 목차
    parts.append("## 목차")
    parts.append("")
    for item in plan.toc.items:
        indent = "  " * (item.section_number.count("."))
        parts.append(f"{indent}- [{item.section_number}. {item.title}](#{item.section_number.replace('.', '')}-{item.title.replace(' ', '-').lower()})")
    parts.append("")
    parts.append("---")
    parts.append("")
    
    # 가이드라인 (선택적)
    has_guidelines = any(item.guideline for item in plan.toc.items)
    if has_guidelines:
        parts.append("## 📋 섹션별 가이드라인")
        parts.append("")
        parts.append("> 이 섹션은 각 챕터 작성 시 사용된 가이드라인입니다.")
        parts.append("")
        for item in plan.toc.items:
            if item.guideline:
                parts.append(f"### {item.section_number}. {item.title}")
                parts.append("")
                parts.append(item.guideline)
                parts.append("")
        parts.append("---")
        parts.append("")
        
    return "\n".join(parts)


def format_section_content(section: PlanSection, visual: "VisualArtifact" = None) -> str:
    """개별 섹션 본문 및 시각화 포맷팅"""
    parts = []
    level = section.section_number.count(".") + 2
    header_prefix = "#" * level
    
    parts.append(f"{header_prefix} {section.section_number}. {section.title}")
    parts.append("")
    parts.append(section.content)
    parts.append("")
    
    # 시각화 삽입
    if visual:
        parts.append(_format_visual_block(visual))
        parts.append("")
        
    return "\n".join(parts)


def _format_visual_block(visual: "VisualArtifact") -> str:
    """시각화 블록을 마크다운으로 포맷"""
    meta = visual.meta
    lines = []
    
    # 시각화 타입별 아이콘
    icons = {
        "table": "📊",
        "diagram": "🔀",
        "image_search": "🔍",
        "image_gen": "🎨"
    }
    icon = icons.get(meta.visual_type, "📌")
    
    # lines.append(f"#### {icon} 시각화: {meta.purpose[:50]}")
    # lines.append("")
    
    # 콘텐츠 또는 placeholder
    if visual.is_placeholder or not meta.content:
        lines.append(f"**{meta.placeholder}**")
    else:
        lines.append(meta.content)
    
    
    # lines.append("")
    # lines.append(f"> **시각화 목적**: {meta.purpose}")
    # lines.append(f"> **형식 선택 이유**: {meta.why_this_format}")
    if meta.data_source:
        lines.append(f"> **데이터 출처**: {meta.data_source}")
    
    return "\n".join(lines)


def generate_partial_edit(
    instruction: str,
    target_text: str,
    prefix_text: str,
    suffix_text: str,
    granularity: str
) -> str:
    """
    기존 텍스트의 일부분(Target)만 수정하여 반환합니다.
    - prefix/suffix Context를 고려하여 자연스럽게 이어지도록 생성
    """
    
    
    system_prompt = PARTIAL_EDIT_SYSTEM_PROMPT.format(granularity=granularity)
    
    user_content = PARTIAL_EDIT_USER_PROMPT.format(
        prefix_text=prefix_text,
        target_text=target_text,
        suffix_text=suffix_text,
        instruction=instruction
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content)
    ]
    
    # LLM 호출
    chat = get_llm(max_tokens=4096, reasoning_effort="medium")
    response = chat.invoke(messages)
    
    return response.content.strip()
