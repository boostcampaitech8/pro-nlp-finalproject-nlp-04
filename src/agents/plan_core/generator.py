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
# from agents.plan_core.visual.schemas import VisualMeta, VisualArtifact


# ===========================
# Blueprint 기반 생성 함수
# ===========================

def generate_section_from_blueprint(
    structured_input: StructuredInput,
    blueprint_item: BlueprintItem,
    section_index: int,
    previous_sections: List[PlanSection] = None
) -> PlanSection:
    """
    Blueprint 항목을 기반으로 섹션을 생성합니다.
    - content가 있으면 그대로 반환
    - content가 없으면 guideline + 이전 섹션 컨텍스트로 LLM 생성
    """
    section_number = str(section_index + 1)
    
    # content가 이미 있으면 그대로 사용
    if blueprint_item.content:
        return PlanSection(
            section_number=section_number,
            title=blueprint_item.title,
            content=blueprint_item.content
        )
    
    # content가 없으면 LLM으로 생성
    previous_sections = previous_sections or []
    
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
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=SECTION_GENERATION_USER_PROMPT.format(
            section_number=section_number,
            title=blueprint_item.title,
            guideline=guideline
        ))
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
        content=content
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
    
    # 제목
    md_parts.append(f"# {plan.idea.title}")
    md_parts.append("")
    md_parts.append(f"> {plan.idea.summary}")
    md_parts.append("")
    md_parts.append(f"*생성 방법: {plan.method}*")
    md_parts.append("")
    md_parts.append("---")
    md_parts.append("")
    
    # 목차
    md_parts.append("## 목차")
    md_parts.append("")
    for item in plan.toc.items:
        indent = "  " * (item.section_number.count("."))
        md_parts.append(f"{indent}- [{item.section_number}. {item.title}](#{item.section_number.replace('.', '')}-{item.title.replace(' ', '-').lower()})")
    md_parts.append("")
    md_parts.append("---")
    md_parts.append("")
    
    # 가이드라인 (방법 B - Blueprint에서도 사용 가능)
    has_guidelines = any(item.guideline for item in plan.toc.items)
    if has_guidelines:
        md_parts.append("## 📋 섹션별 가이드라인")
        md_parts.append("")
        md_parts.append("> 이 섹션은 각 챕터 작성 시 사용된 가이드라인입니다.")
        md_parts.append("")
        for item in plan.toc.items:
            if item.guideline:
                md_parts.append(f"### {item.section_number}. {item.title}")
                md_parts.append("")
                md_parts.append(item.guideline)
                md_parts.append("")
        md_parts.append("---")
        md_parts.append("")
    
    # 본문 + 시각화
    for section in plan.sections:
        level = section.section_number.count(".") + 2
        header_prefix = "#" * level
        md_parts.append(f"{header_prefix} {section.section_number}. {section.title}")
        md_parts.append("")
        md_parts.append(section.content)
        md_parts.append("")
        
        # 시각화 삽입
        if section.section_number in visual_by_section:
            visual = visual_by_section[section.section_number]
            md_parts.append(_format_visual_block(visual))
            md_parts.append("")
    
    return "\n".join(md_parts)


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
    
    lines.append(f"#### {icon} 시각화: {meta.purpose[:50]}")
    lines.append("")
    
    # 콘텐츠 또는 placeholder
    if visual.is_placeholder or not meta.content:
        lines.append(f"**{meta.placeholder}**")
    else:
        lines.append(meta.content)
    
    
    lines.append("")
    lines.append(f"> **시각화 목적**: {meta.purpose}")
    lines.append(f"> **형식 선택 이유**: {meta.why_this_format}")
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

