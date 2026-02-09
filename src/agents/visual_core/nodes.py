"""
Visual Agent 전용 노드 함수들
"""
from typing import Dict, Any, List
from state.visual import VisualInternalState
from agents.plan_core.logger import get_logger, LogLevel
from agents.visual_core.schemas import Decision, VisualMeta, VisualArtifact
from agents.visual_core.router import decide_node, generate_visual_meta
from agents.visual_core.generator import render_table, render_diagram, render_chart, image_search, image_gen, create_visual_artifact
from agents.visual_core.validator import validate_and_decide_retry

# ===========================
# 시각화 처리 노드 (VisualInternalState 기반)
# ===========================

def parse_request_node(state: VisualInternalState) -> VisualInternalState:
    """
    [진입점] 요청된 visual_request를 분석하거나, context를 정리 (Placeholder)
    """
    print(f"[VisualAgent] 요청 수신: {state['visual_request']}")
    return state

def visual_decide_node(state: VisualInternalState) -> VisualInternalState:
    logger = get_logger()
    
    # Visual Core 로직은 기존 함수 재사용 (입력 포맷 매핑 필요)
    # 기존 decide_node는 dict를 입력받으므로 변환
    temp_state = {
        "section_id": state["target_section_id"],
        "section_title": "", # 필요시 추가
        "section_text": state["context_text"],
        "retry_count": state["retry_count"]
    }
    
    result_state = decide_node(temp_state)
    result_state = generate_visual_meta(result_state)
    
    # 결정 결과 로깅
    logger.log_visual_decision(state["target_section_id"], result_state.get("decision", {}))
    
    # 중요: Decision 정보를 state에 저장 (추후 참조를 위해 visual_type 매핑)
    decision = Decision(**result_state.get("decision", {}))
    
    visual_type = ""
    if decision.needs_chart: visual_type = "chart"
    elif decision.needs_diagram: visual_type = "diagram"
    elif decision.needs_table: visual_type = "table"
    elif decision.needs_image_search: visual_type = "image_search"
    elif decision.needs_image_gen: visual_type = "image_gen"
    
    
    state["visual_type"] = visual_type
    state["visual_meta"] = result_state.get("visual_meta", {})
    
    return state


def visual_generate_node(state: VisualInternalState) -> VisualInternalState:
    logger = get_logger()
    
    # 매핑용 임시 State
    temp_state = {
        "section_id": state["target_section_id"],
        "section_text": state["context_text"],
        "decision": {
            "needs_chart": state["visual_type"] == "chart",
            "needs_diagram": state["visual_type"] == "diagram",
            "needs_table": state["visual_type"] == "table",
            "needs_image_search": state["visual_type"] == "image_search",
            "needs_image_gen": state["visual_type"] == "image_gen"
        },
        "visual_meta": state.get("visual_meta", {})
    }
    
    # Generator 호출 (기존 함수 재사용)
    # 주의: Generator들이 'visual_meta'를 채워서 반환함
    try:
        vt = state["visual_type"]
        if vt == "chart":
            temp_state = render_chart(temp_state)
        elif vt == "diagram":
            temp_state = render_diagram(temp_state)
        elif vt == "table":
            temp_state = render_table(temp_state)
        elif vt == "image_search":
            temp_state = image_search(temp_state)
        elif vt == "image_gen":
            temp_state = image_gen(temp_state)
            
    except Exception as e:
        logger.log(LogLevel.ERROR, "visual_generation", f"시각화 생성 실패: {e}")
        state["code"] = ""
        state["html"] = f"Error: {str(e)}"
        return state
    
    # 생성 결과 추출 (Generator가 code/html 등을 어떻게 반환하는지 확인 필요)
    # 기존 generator.py는 'visual_meta' 안에 'code', 'html_preview' 등을 담음
    meta = temp_state.get("visual_meta", {})
    state["code"] = meta.get("code", "")
    # html_preview가 없으면 caption이라도
    state["html"] = meta.get("html_preview", meta.get("caption", ""))
    
    logger.log_visual_generation(state["target_section_id"], state["visual_type"], True)
    
    return state


def visual_validate_node(state: VisualInternalState) -> VisualInternalState:
    logger = get_logger()
    
    # Validator 호출
    temp_state = {
        "visual_meta": state["visual_meta"],  # Full meta passed
        "retry_count": state["retry_count"]
    }
    
    # Update meta with latest code
    temp_state["visual_meta"]["code"] = state["code"]
    if state["html"]:
         temp_state["visual_meta"]["content"] = state["html"]
    
    
    should_retry, result = validate_and_decide_retry(
        section_text=state["context_text"],
        section_title="", 
        state=temp_state
    )
    
    state["validation_results"] = result.model_dump()
    
    if should_retry:
        state["retry_count"] += 1
        
    logger.log_validation(state["target_section_id"], result.is_valid, result.score, result.reason)
    
    return state


def visual_finalize_node(state: VisualInternalState) -> VisualInternalState:
    # 최종 결과 저장 (Artifact 생성 등)
    # 독립 에이전트이므로 여기서는 따로 할 게 없을 수도 있음 (상위로 반환)
    # 기존 create_visual_artifact 로직을 활용한다면 여기서 Artifact 객체 생성
    
    return state

# Routing Logic
def route_visual_validation(state: VisualInternalState) -> str:
    # 3회까지만 재시도 (하드코딩 or Config)
    if not state["validation_results"].get("is_valid", False):
        if state["retry_count"] < 3:
            return "visual_generate"
    return "visual_finalize"
