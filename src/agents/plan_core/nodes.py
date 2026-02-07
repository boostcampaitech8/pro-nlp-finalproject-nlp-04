"""
오케스트레이터 노드 함수들 - 기획서 생성 워크플로우의 개별 노드들
"""
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

_pbar = None

from agents.plan_core.schemas import (
    StructuredIdea, TableOfContents, TableOfContentsItem, 
    PlanSection, GeneratedPlan,
    BlueprintItem, StructuredInput
)
from agents.plan_core.generator import (
    compose_plan_markdown, generate_section_from_blueprint
)

from state.plan import PlanInternalState, SectionProcessState
from agents.plan_core.logger import get_logger, LogLevel


# ===========================
# 기획서 생성 노드들 (Blueprint 기반)
# ===========================

def parse_input_node(state: PlanInternalState) -> PlanInternalState:
    """전역 상태에서 필요한 입력값을 내부 상태로 전이 및 초기화"""
    print("[Pipeline] 입력 데이터 확인 및 초기화...")
    
    # IdeaState 및 PlanState(Public) 참조
    idea = state.get("idea", {})
    plan_public = state.get("plan", {})
    blueprint = plan_public.get("blueprint", [])
    
    # tqdm 초기화
    global _pbar
    total_sections = len(blueprint)
    if total_sections > 0:
        _pbar = tqdm(total=total_sections, desc="기획서 생성 진행율", unit="section")
    
    # toc 변환 (문자열 목록 -> TableOfContents)
    toc_items = []
    for i, title in enumerate(idea.get("toc", [])):
        parts = title.split(". ", 1)
        section_number = parts[0] if len(parts) > 1 else str(i + 1)
        section_title = parts[1] if len(parts) > 1 else title
        toc_items.append({
            "section_number": section_number,
            "title": section_title,
            "guideline": None
        })
    
    # PlanInternalState 필드 업데이트
    # (GlobalState를 상속받으므로 직접 할당)
    state["current_section_index"] = 0
    state["sections"] = []
    state["visual_artifacts"] = []
    state["temp_visual_state"] = {}
    state["final_markdown"] = ""
    state["output_path"] = ""
    
    return state


def generate_section_node(state: PlanInternalState) -> PlanInternalState:
    """전역 상태를 직접 참조하여 섹션 생성"""
    logger = get_logger()
    
    # 전역 컨텍스트 바로 읽기
    idea = state["idea"]
    plan_public = state["plan"]
    blueprint = plan_public["blueprint"]
    current_index = state["current_section_index"]
    
    blueprint_item_dict = blueprint[current_index]
    blueprint_item = BlueprintItem(**blueprint_item_dict)
    
    # tqdm 업데이트
    global _pbar
    if _pbar:
        _pbar.set_description(f"작성 중: {blueprint_item.title}")
        guideline_text = (blueprint_item.guideline[:100] + "...") if blueprint_item.guideline and len(blueprint_item.guideline) > 100 else (blueprint_item.guideline or "없음")
        tqdm.write(f"\n[입력] 섹션 {current_index+1}: {blueprint_item.title} (가이드라인: {guideline_text})")
    
    logger.log_section_generation(str(current_index + 1), blueprint_item.title, "blueprint")
    
    # StructuredInput 객체 생성 (기존 generator 함수와 호환 유지)
    structured_input = StructuredInput(
        planning_style=idea["planning_style"],
        rationale=idea["rationale"],
        toc=idea["toc"],
        blueprint=[BlueprintItem(**b) for b in blueprint]
    )
    
    previous_sections = [PlanSection(**s) for s in state["sections"]]
    
    section = generate_section_from_blueprint(
        structured_input=structured_input,
        blueprint_item=blueprint_item,
        section_index=current_index,
        previous_sections=previous_sections
    )
    
    if _pbar:
        content_snippet = section.content[:50].replace("\n", " ") + "..."
        tqdm.write(f"[출력] {content_snippet}")
        _pbar.set_postfix(last_output=section.title)
    
    state["sections"].append(section.model_dump())
    
    # 시각화 처리를 위한 임시 상태 설정
    state["temp_visual_state"] = {
        "section_id": section.section_number,
        "section_title": section.title,
        "section_text": section.content,
        "retry_count": 0
    }
    return state






# ===========================
# 라우팅 및 보조 노드
# ===========================

def increment_section_index_node(state: PlanInternalState) -> PlanInternalState:
    state["current_section_index"] += 1
    global _pbar
    if _pbar:
        _pbar.update(1)
    return state


def route_next_section(state: PlanInternalState) -> str:
    blueprint = state["plan"]["blueprint"]
    current_index = state["current_section_index"]
    if current_index < len(blueprint):
        return "generate_section"
    return "compose_output"


# ===========================
# 최종 출력 노드
# ===========================

def compose_output_node(state: PlanInternalState) -> PlanInternalState:
    print("[Pipeline] 최종 마크다운 조합 중...")
    global _pbar
    if _pbar:
        _pbar.close()
        _pbar = None
    
    idea_data = state["idea"]
    plan_public = state["plan"]
    
    # TableOfContents 생성 (문자열 리스트 기반)
    toc_items = []
    for i, title in enumerate(idea_data["toc"]):
        parts = title.split(". ", 1)
        toc_items.append(TableOfContentsItem(
            section_number=parts[0] if len(parts) > 1 else str(i + 1),
            title=parts[1] if len(parts) > 1 else title
        ))
    
    plan = GeneratedPlan(
        idea=StructuredIdea(
            title=idea_data["toc"][0].split(". ", 1)[-1] if idea_data["toc"] else "기획서",
            summary=idea_data["rationale"],
            problem="", target_users=[], core_features=[], differentiators=[]
        ),
        toc=TableOfContents(items=toc_items),
        sections=[PlanSection(**s) for s in state["sections"]],
        method="blueprint"
    )
    
    visual_artifacts = [VisualArtifact(**v) for v in state["visual_artifacts"]]
    markdown = compose_plan_markdown(plan, visual_artifacts)
    state["final_markdown"] = markdown
    
    return state


def save_output_node(state: PlanInternalState) -> PlanInternalState:
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
