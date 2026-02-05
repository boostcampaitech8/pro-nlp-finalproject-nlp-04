"""
오케스트레이터 노드 함수들 - 기획서 생성 워크플로우의 개별 노드들
"""
from __future__ import annotations
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

_pbar = None

from agents.plan.schemas import (
    StructuredIdea, TableOfContents, TableOfContentsItem, 
    PlanSection, GeneratedPlan,
    BlueprintItem, StructuredInput
)
from agents.plan.generator import (
    compose_plan_markdown, generate_section_from_blueprint
)
from agents.plan.visual.schemas import Decision, VisualMeta, VisualArtifact
from agents.plan.visual.router import decide_node, generate_visual_meta, route_next
from agents.plan.visual.generator import render_table, render_diagram, render_chart, image_search, image_gen, create_visual_artifact
from agents.plan.visual.validator import validate_and_decide_retry
from state.plan import PlanPipelineState, SectionProcessState
from agents.plan.logger import get_logger, LogLevel


# ===========================
# 기획서 생성 노드들 (Blueprint 기반)
# ===========================

def parse_input_node(state: PlanPipelineState) -> PlanPipelineState:
    """외부 에이전트 입력을 파싱하여 state에 저장"""
    print("[Pipeline] 구조화된 입력 파싱 중...")
    structured_input = state["structured_input"]
    
    # tqdm 초기화
    global _pbar
    total_sections = len(structured_input.get("blueprint", []))
    if total_sections > 0:
        _pbar = tqdm(total=total_sections, desc="기획서 생성 진행율", unit="section")
    
    # toc 변환 (문자열 목록 -> TableOfContents)
    toc_items = []
    for i, title in enumerate(structured_input["toc"]):
        # "1. 서비스 개요" 형태에서 숫자와 제목 분리
        parts = title.split(". ", 1)
        section_number = parts[0] if len(parts) > 1 else str(i + 1)
        section_title = parts[1] if len(parts) > 1 else title
        toc_items.append({
            "section_number": section_number,
            "title": section_title,
            "guideline": None
        })
    
    state["toc"] = {"items": toc_items}
    state["current_section_index"] = 0
    state["sections"] = []
    state["visual_artifacts"] = []
    state["method"] = "blueprint"
    
    return state


def generate_section_node(state: PlanPipelineState) -> PlanPipelineState:
    """Blueprint 기반 섹션 생성"""
    logger = get_logger()
    
    structured_input = StructuredInput(**state["structured_input"])
    current_index = state["current_section_index"]
    blueprint_item = structured_input.blueprint[current_index]
    
    # tqdm 업데이트 (입력 표시)
    global _pbar
    if _pbar:
        _pbar.set_description(f"작성 중: {blueprint_item.title}")
        guideline_text = (blueprint_item.guideline[:100] + "...") if blueprint_item.guideline and len(blueprint_item.guideline) > 100 else (blueprint_item.guideline or "없음")
        tqdm.write(f"\n[입력] 섹션 {current_index+1}: {blueprint_item.title} (가이드라인: {guideline_text})")
    else:
        print(f"  [{current_index+1}/{len(structured_input.blueprint)}] {blueprint_item.title}")
        
    logger.log_section_generation(str(current_index + 1), blueprint_item.title, "blueprint")
    
    previous_sections = [PlanSection(**s) for s in state["sections"]]
    
    section = generate_section_from_blueprint(
        structured_input=structured_input,
        blueprint_item=blueprint_item,
        section_index=current_index,
        previous_sections=previous_sections
    )
    
    # tqdm 업데이트 (출력 요약 표시)
    if _pbar:
        content_snippet = section.content[:50].replace("\n", " ") + "..."
        tqdm.write(f"[출력] {content_snippet}")
        _pbar.set_postfix(last_output=section.title)
    
    state["sections"].append(section.model_dump())
    
    # 시각화 처리를 위한 상태 설정
    state["current_visual_state"] = {
        "section_id": section.section_number,
        "section_title": section.title,
        "section_text": section.content,
        "retry_count": 0
    }
    return state


# ===========================
# 시각화 처리 노드들
# ===========================

def visual_decide_node(state: PlanPipelineState) -> PlanPipelineState:
    """시각화 필요성 판단"""
    logger = get_logger()
    
    visual_state = state["current_visual_state"]
    visual_state = decide_node(visual_state)
    visual_state = generate_visual_meta(visual_state)
    
    # 로그 기록
    logger.log_visual_decision(
        visual_state["section_id"],
        visual_state.get("decision", {})
    )
    
    state["current_visual_state"] = visual_state
    return state


def visual_generate_node(state: PlanPipelineState) -> PlanPipelineState:
    """시각화 생성"""
    logger = get_logger()
    
    visual_state = state["current_visual_state"]
    decision = Decision(**visual_state.get("decision", {}))
    
    visual_type = None
    success = True
    error = None
    
    try:
        # 우선순위: 차트(가장 중요) > 다이어그램 > 표
        if decision.needs_chart:
            visual_type = "chart"
            visual_state = render_chart(visual_state)
        elif decision.needs_diagram:
            visual_type = "diagram"
            visual_state = render_diagram(visual_state)
        elif decision.needs_table:
            visual_type = "table"
            visual_state = render_table(visual_state)
        elif decision.needs_image_search:
            visual_type = "image_search"
            visual_state = image_search(visual_state)
        elif decision.needs_image_gen:
            visual_type = "image_gen"
            visual_state = image_gen(visual_state)
    except Exception as e:
        success = False
        error = str(e)
        logger.log(LogLevel.ERROR, "visual_generation", f"시각화 생성 실패: {e}", {
            "section_id": visual_state["section_id"],
            "visual_type": visual_type
        })
    
    if visual_type:
        logger.log_visual_generation(visual_state["section_id"], visual_type, success, error)
    
    state["current_visual_state"] = visual_state
    return state


def visual_validate_node(state: PlanPipelineState) -> PlanPipelineState:
    """시각화 검증"""
    logger = get_logger()
    
    visual_state = state["current_visual_state"]
    
    should_retry, result = validate_and_decide_retry(
        section_text=visual_state["section_text"],
        section_title=visual_state["section_title"],
        state=visual_state
    )
    
    # 로그 기록
    logger.log_validation(
        visual_state["section_id"],
        result.is_valid,
        result.score,
        result.reason
    )
    
    visual_state["validation_result"] = result.model_dump()
    visual_state["should_retry"] = should_retry
    
    if should_retry:
        visual_state["retry_count"] = visual_state.get("retry_count", 0) + 1
        logger.log(LogLevel.WARNING, "validation", f"재시도 필요 (시도 {visual_state['retry_count']}회)", {
            "section_id": visual_state["section_id"],
            "retry_count": visual_state["retry_count"]
        })
    
    state["current_visual_state"] = visual_state
    return state


def visual_finalize_node(state: PlanPipelineState) -> PlanPipelineState:
    """시각화 결과 저장"""
    visual_state = state["current_visual_state"]
    
    # 시각화가 있으면 artifact 생성
    if visual_state.get("visual_meta"):
        artifact = create_visual_artifact(
            section_number=visual_state["section_id"],
            state=visual_state
        )
        if artifact:
            state["visual_artifacts"].append(artifact.model_dump())
    
    return state


# ===========================
# 섹션 반복 라우팅
# ===========================

def route_visual_validation(state: PlanPipelineState) -> str:
    """검증 결과에 따라 재시도 또는 다음 단계"""
    visual_state = state["current_visual_state"]
    if visual_state.get("should_retry", False):
        return "visual_generate"
    return "visual_finalize"


def increment_section_index_node(state: PlanPipelineState) -> PlanPipelineState:
    """섹션 인덱스 증가 노드"""
    state["current_section_index"] = state.get("current_section_index", 0) + 1
    
    # 진행률 업데이트
    global _pbar
    if _pbar:
        _pbar.update(1)
        
    return state


def check_needs_visual(state: PlanPipelineState) -> str:
    """시각화 필요 여부 확인"""
    visual_state = state["current_visual_state"]
    decision = Decision(**visual_state.get("decision", {}))
    
    if any([decision.needs_table, decision.needs_diagram, decision.needs_chart, 
            decision.needs_image_search, decision.needs_image_gen]):
        return "visual_generate"
    return "next_section"


def route_next_section(state: PlanPipelineState) -> str:
    """다음 섹션이 있으면 계속, 없으면 최종 출력"""
    structured_input = StructuredInput(**state["structured_input"])
    current_index = state.get("current_section_index", 0)
    
    if current_index < len(structured_input.blueprint):
        return "generate_section"
    return "compose_output"


# ===========================
# 최종 출력 노드
# ===========================

def compose_output_node(state: PlanPipelineState) -> PlanPipelineState:
    """최종 마크다운 조합"""
    print("[Pipeline] 최종 마크다운 생성 중...")
    
    # 진행률 종료
    global _pbar
    if _pbar:
        _pbar.close()
        _pbar = None
    
    structured_input = StructuredInput(**state["structured_input"])
    toc = TableOfContents(**state["toc"])
    sections = [PlanSection(**s) for s in state["sections"]]
    
    # StructuredIdea 대체 생성 (Blueprint에서 추출)
    idea = StructuredIdea(
        title=structured_input.toc[0].split(". ", 1)[-1] if structured_input.toc else "기획서",
        summary=structured_input.rationale,
        problem="",
        target_users=[],
        core_features=[],
        differentiators=[]
    )
    
    plan = GeneratedPlan(
        idea=idea,
        toc=toc,
        sections=sections,
        method="blueprint"
    )
    
    visual_artifacts = [VisualArtifact(**v) for v in state.get("visual_artifacts", [])]
    
    markdown = compose_plan_markdown(plan, visual_artifacts)
    state["final_markdown"] = markdown
    
    return state


def save_output_node(state: PlanPipelineState) -> PlanPipelineState:
    """파일 저장"""
    # 프로젝트 루트 경로 찾기 (src의 상위 디렉토리)
    project_root = Path(__file__).parent.parent.parent.parent
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)

    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"plan_blueprint_{timestamp}.md"
    output_path = output_dir / filename
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(state["final_markdown"])
    
    state["output_path"] = str(output_path)
    print(f"[Pipeline] 저장 완료: {output_path}")
    
    return state
