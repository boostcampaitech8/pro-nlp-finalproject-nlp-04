"""
오케스트레이터 노드 함수들 - 기획서 생성 워크플로우의 개별 노드들
"""
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path



from agents.plan_core.schemas import (
    StructuredIdea, TableOfContents, TableOfContentsItem, 
    PlanSection, GeneratedPlan,
    BlueprintItem, StructuredInput
)
from agents.plan_core.generator import (
    compose_plan_markdown, generate_section_from_blueprint,
    format_plan_header, format_plan_toc, format_section_content
)

from state.plan import PlanInternalState
from agents.plan_core.logger import get_logger, LogLevel
from agents.plan_core.evaluator import evaluate_research_need
from agents.visual_core import run_visual_for_section, VisualArtifact


# ===========================
# 기획서 생성 노드들 (Blueprint 기반)
# ===========================

def parse_input_node(state: PlanInternalState) -> PlanInternalState:
    """전역 상태에서 필요한 입력값을 내부 상태로 전이 및 초기화"""
    print("[Pipeline] 입력 데이터 확인 및 초기화...")
    
    # IdeaState 및 PlanState(Public) 참조
    idea = state.get("idea", {})
    blueprint = idea.get("blueprint", [])
    
    # tqdm 제거
    total_sections = len(blueprint)

    
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
    # [Fix] 기존 상태가 있으면 초기화하지 않음 (Resume 지원)
    if "current_section_index" not in state:
        state["current_section_index"] = 0
    if "sections" not in state:
        state["sections"] = []
    if "visual_artifacts" not in state:
        state["visual_artifacts"] = []
    
    # plan_status 초기화 (없으면 기본값)
    if "plan_status" not in state:
        state["plan_status"] = "IN_PROGRESS"
    
    state["temp_visual_state"] = {}
    state["final_markdown"] = ""
    # [Fix] output_path 초기화 제거 (agents/plan.py에서 전달된 값 유지)
    if "output_path" not in state:
        state["output_path"] = ""
    
    return state


def initialize_output_node(state: PlanInternalState) -> PlanInternalState:
    """출력 파일 생성 및 헤더/목차 초기화 (Incremental Saving)"""
    
    # [Fix] 이미 파일이 생성되어 있다면 스킵 (반복 실행 시 파일 유지)
    if state.get("output_path") and Path(state["output_path"]).exists():
        print(f"[Pipeline] 기존 출력 파일 유지: {state['output_path']}")
        return state

    print("[Pipeline] 출력 파일 초기화 중...")
    
    project_root = Path(__file__).parent.parent.parent.parent
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"plan_blueprint_{timestamp}.md"
    output_path = output_dir / filename
    
    # 헤더 및 목차 생성
    idea_data = state["idea"]
    toc_items = []
    for i, title in enumerate(idea_data.get("toc", [])):
        parts = title.split(". ", 1)
        toc_items.append(TableOfContentsItem(
            section_number=parts[0] if len(parts) > 1 else str(i + 1),
            title=parts[1] if len(parts) > 1 else title
        ))
    
    # 임시 Plan 객체 생성 (헤더/목차 포맷팅용)
    temp_plan = GeneratedPlan(
        idea=StructuredIdea(
            title=idea_data["toc"][0].split(". ", 1)[-1] if idea_data.get("toc") else "기획서",
            summary=idea_data["rationale"],
            problem="", target_users=[], core_features=[], differentiators=[]
        ),
        toc=TableOfContents(items=toc_items),
        sections=[], # 아직 섹션 없음
        method="blueprint"
    )
    
    # 파일 쓰기 (헤더 + 목차)
    header_str = format_plan_header(temp_plan)
    toc_str = format_plan_toc(temp_plan)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header_str + "\n" + toc_str + "\n")
        
    state["output_path"] = str(output_path)
    print(f"[Pipeline] 파일 생성됨: {output_path}")
    
    return state


def generate_section_node(state: PlanInternalState) -> PlanInternalState:
    """전역 상태를 직접 참조하여 섹션 생성 (Research 평가 포함)"""
    logger = get_logger()
    
    # 전역 컨텍스트 바로 읽기
    idea = state["idea"]
    blueprint = idea.get("blueprint", [])
    current_index = state["current_section_index"]
    
    blueprint_item_dict = blueprint[current_index]
    blueprint_item = BlueprintItem(**blueprint_item_dict)
    
    # =========================================
    # Pre-write: ResearchNeedScore 평가
    # =========================================
    
    # 이미 리서치가 완료된 상태인지 확인 (research.needs_research == False)
    research_state = state.get("research", {})
    research_completed = research_state.get("section_context") == blueprint_item.title and not research_state.get("needs_research", True)
    
    if not research_completed:
        score_result = evaluate_research_need(
            blueprint_item, 
            planning_style=idea.get("planning_style"),
            rationale=idea.get("rationale")
        )
        
        logger.log(LogLevel.INFO, "research_evaluator", 
            f"ResearchNeedScore: {score_result.score:.2f} (needs={score_result.needs_research})", {
                "section": blueprint_item.title,
                "score": score_result.score,
                "needs_research": score_result.needs_research
            })
        
        # 리서치가 필요하면 Supervisor에게 알림 (상태만 반환하고 종료)
        if score_result.needs_research:
            # [Context Enhancement] Research Goal을 context로 사용
            research_context = score_result.research_goal if score_result.research_goal else blueprint_item.title
            
            logger.log(LogLevel.INFO, "research_evaluator", 
                f"Research 요청: {research_context}", {
                    "queries": []
                })
            state["research"] = {
                "needs_research": True,
                "queries": [],
                "section_context": research_context, # Updated to use goal
                "evidence_store": research_state.get("evidence_store", [])
            }
            # [Explicit State] 상태 변경 -> Supervisor가 감지
            state["plan_status"] = "WAITING_FOR_RESEARCH"
            return state  # Supervisor가 RUN_RESEARCH로 라우팅
    
    # =========================================
    # 섹션 생성 (Research 완료 또는 불필요 시)
    # =========================================
    
    # [Log] 섹션 진행 상황 출력
    print(f"\n[입력] 섹션 {current_index+1}: {blueprint_item.title}")
    # 가이드라인은 필요 시 로깅 또는 디버그 출력

    
    # StructuredInput 객체 생성 (기존 generator 함수와 호환 유지)
    structured_input = StructuredInput(
        planning_style=idea["planning_style"],
        rationale=idea["rationale"],
        toc=idea["toc"],
        blueprint=[BlueprintItem(**b) for b in blueprint]
    )
    
    previous_sections = [PlanSection(**s) for s in state["sections"]]
    
    # =====================================================
    # [Research 연동] 리서치 결과를 섹션 생성에 활용
    # 
    # Research Agent 실행 후 state['research']에 저장된 데이터:
    #   - evidence_store (List[str]): Tavily 검색 결과 내용들
    #   - analysis_result (str): 검색 결과 분석 텍스트
    # 
    # generator.generate_section_from_blueprint()의 evidence 파라미터로 전달하면
    # 프롬프트에 "[참고용 리서치 자료]"로 포함되어 팩트 기반 작성 유도
    # =====================================================
    # [Fix] Stale Evidence 방지: 현재 섹션에 대한 리서치인지 확인
    if research_state.get("section_context") != blueprint_item.title:
        evidence_store = []
        analysis_result = ""
    else:
        analysis_result = research_state.get("analysis_result", "")
        evidence_store = research_state.get("evidence_store", [])
    
    # [Log] 리서치 결과 로깅 (섹션 생성 시작 전)
    if evidence_store:
        logger.log(LogLevel.INFO, "plan_generator", 
            f"리서치 결과 수신: {len(evidence_store)}건", {
                "section": blueprint_item.title,
                "analysis_preview": (analysis_result[:100] + "...") if analysis_result else "없음",
                "evidence_count": len(evidence_store)
            })

    # [Log] 섹션 생성 시작 로깅
    logger.log_section_generation(str(current_index + 1), blueprint_item.title, "blueprint")
    
    # evidence 리스트 구성: 분석 결과 + 개별 검색 결과
    evidence_for_prompt = []
    evidence_for_record = []

    if analysis_result:
        evidence_for_prompt.append(f"[분석 요약]\n{analysis_result}")

    if evidence_store:
        for item in evidence_store:
            if isinstance(item, dict):
                # New struct ({title, url, content})
                title = item.get("title", "No Title")
                url = item.get("url", "")
                content = item.get("content", "")
                
                # 프롬프트에는 내용 전달
                evidence_for_prompt.append(f"Title: {title}\nContent: {content}")
                
                # 기록(사이드바)에는 링크 전달
                if url:
                    evidence_for_record.append(f"[{title}]({url})")
                else:
                    evidence_for_record.append(title)
            else:
                # Fallback (legacy string)
                evidence_for_prompt.append(str(item))
                evidence_for_record.append(str(item)[:50] + "...")
    
    section = generate_section_from_blueprint(
        structured_input=structured_input,
        blueprint_item=blueprint_item,
        section_index=current_index,
        previous_sections=previous_sections,
        evidence=evidence_for_prompt,  # Research 결과 전달 (Prompt용)
        evidence_for_record=evidence_for_record # 저장용 (Sidebar용)
    )
    
    print(f"[출력] {section.content[:50].replace('\\n', ' ')}...")

    
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
# 시각화 처리 노드
# ===========================

def process_visual_node(state: PlanInternalState) -> PlanInternalState:
    """
    섹션 생성 후 시각화 처리 (visual_core 헬퍼 사용)
    """
    logger = get_logger()
    
    temp_state = state.get("temp_visual_state", {})
    if not temp_state or not temp_state.get("section_text"):
        logger.log(LogLevel.DEBUG, "visual_processor", "시각화 처리 스킵 (temp_visual_state 없음)", {})
        return state
    
    section_title = temp_state.get("section_title", "")
    logger.log(LogLevel.INFO, "visual_processor", f"시각화 처리 시작: {section_title}", {
        "section_id": temp_state.get("section_id"),
        "text_length": len(temp_state.get("section_text", ""))
    })
    
    # 헬퍼 호출
    artifact = run_visual_for_section(
        section_id=str(temp_state.get("section_id", "")),
        section_title=section_title,
        section_text=temp_state.get("section_text", "")
    )
    
    # 결과 저장
    if artifact:
        # [Safety] visual_artifacts 타입 보장
        if not isinstance(state.get("visual_artifacts"), list):
            state["visual_artifacts"] = []
            
        state["visual_artifacts"].append(artifact)
        
        # [Fix] visual_type은 meta 안에 있음
        visual_type = artifact.get("meta", {}).get("visual_type")
        logger.log(LogLevel.INFO, "visual_processor", f"시각화 생성 완료: {visual_type}", {
            "section_title": section_title,
            "visual_type": visual_type
        })
    else:
        logger.log(LogLevel.INFO, "visual_processor", "시각화 불필요 판정", {"section_title": section_title})
    
    # 클리어
    state["temp_visual_state"] = {}
    return state


def append_section_node(state: PlanInternalState) -> PlanInternalState:
    """생성된 최신 섹션을 파일에 추가 (Incremental Saving)"""
    if not state.get("output_path"):
        print("[Warning] output_path가 없습니다. 섹션 저장을 건너뜁니다.")
        return state
        
    # 최신 섹션 가져오기
    if not state["sections"]:
        return state
        
    last_section_data = state["sections"][-1]
    section = PlanSection(**last_section_data)
    
    # 시각화 가져오기
    visual = None
    if state.get("visual_artifacts"):
        # 현재 섹션 번호에 해당하는 최신 시각화 찾기
        last_visual = state["visual_artifacts"][-1]
        if last_visual.get("section_number") == section.section_number:
            from agents.visual_core.schemas import VisualArtifact
            visual = VisualArtifact(**last_visual)
            
    # 포맷팅
    content_str = format_section_content(section, visual)
    
    # 파일에 추가 (Append)
    with open(state["output_path"], "a", encoding="utf-8") as f:
        f.write(content_str + "\n")
        
    print(f"[Pipeline] 섹션 {section.section_number} 저장 완료.")
    return state


# ===========================
# 라우팅 및 보조 노드
# ===========================

def increment_section_index_node(state: PlanInternalState) -> PlanInternalState:
    state["current_section_index"] += 1

        
    # [Refactor] 종료 조건 판단 (Incremental)
    # 다음 섹션이 없으면 COMPLETED, 있으면 IN_PROGRESS
    blueprint = state["idea"].get("blueprint", [])
    if state["current_section_index"] >= len(blueprint):
        state["plan_status"] = "COMPLETED"
    else:
        state["plan_status"] = "IN_PROGRESS"
        
    return state


def route_next_section(state: PlanInternalState) -> str:
    blueprint = state["idea"]["blueprint"]
    current_index = state["current_section_index"]
    if current_index < len(blueprint):
        return "generate_section"
    return "compose_output"


# ===========================
# 최종 출력 노드
# ===========================

def compose_output_node(state: PlanInternalState) -> PlanInternalState:
    print("[Pipeline] 최종 마크다운 조합 중...")

    
    idea_data = state["idea"]
    
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
    
    # [Fix] Lazy Import to avoid NameError/Circular Import
    from agents.visual_core.schemas import VisualArtifact
    visual_artifacts = [VisualArtifact(**v) for v in state["visual_artifacts"]]
    markdown = compose_plan_markdown(plan, visual_artifacts)
    state["final_markdown"] = markdown
    
    return state


def save_output_node(state: PlanInternalState) -> PlanInternalState:
    """
    최종 저장 단계
    Incremental Saving으로 이미 파일은 완성되었으므로,
    여기서는 최종 확인 및 경로 출력만 담당 (또는 덮어쓰기 옵션)
    """
    output_path = state.get("output_path")
    if output_path:
        print(f"[Pipeline] 모든 섹션 저장 완료. 최종 파일: {output_path}")
    else:
        # Fallback (예외 상황)
        print("[Warning] output_path 없음. 전체 저장 시도.")
        project_root = Path(__file__).parent.parent.parent.parent
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"plan_blueprint_fallback_{timestamp}.md"
        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(state["final_markdown"])
        state["output_path"] = str(output_path)
        print(f"[Pipeline] Fallback 저장 완료: {output_path}")
    
    return state
