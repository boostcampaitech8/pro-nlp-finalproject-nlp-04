"""
기획서 생성 파이프라인 - Graph 정의
"""
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from state.plan import PlanInternalState
from agents.plan_core.nodes import (
    parse_input_node,
    generate_section_node,
    increment_section_index_node,
    check_needs_visual,
    visual_decide_node,
    visual_generate_node,
    visual_validate_node,
    visual_finalize_node,
    route_visual_validation,
    route_next_section,
    compose_output_node,
    save_output_node,
)
from agents.plan_core.logger import reset_logger

def build_plan_pipeline():
    """
    PlanInternalState를 사용하는 StateGraph 정의
    """
    g = StateGraph(PlanInternalState)
    
    # 노드 추가
    g.add_node("parse_input", parse_input_node)
    g.add_node("generate_section", generate_section_node)
    g.add_node("visual_decide", visual_decide_node)
    g.add_node("visual_generate", visual_generate_node)
    g.add_node("visual_validate", visual_validate_node)
    g.add_node("visual_finalize", visual_finalize_node)
    g.add_node("increment_index", increment_section_index_node)
    g.add_node("compose_output", compose_output_node)
    g.add_node("save_output", save_output_node)
    
    # 엣지 및 흐름 제어
    g.set_entry_point("parse_input")
    g.add_edge("parse_input", "generate_section")
    g.add_edge("generate_section", "visual_decide")
    
    # 시각화 루프 및 조건부 경로
    g.add_conditional_edges(
        "visual_decide",
        check_needs_visual,
        {
            "visual_generate": "visual_generate",
            "next_section": "increment_index"
        }
    )
    
    g.add_edge("visual_generate", "visual_validate")
    
    g.add_conditional_edges(
        "visual_validate",
        route_visual_validation,
        {
            "visual_generate": "visual_generate",
            "visual_finalize": "visual_finalize"
        }
    )
    
    g.add_edge("visual_finalize", "increment_index")
    
    # 다음 섹션 또는 종료 확인
    g.add_conditional_edges(
        "increment_index",
        route_next_section,
        {
            "generate_section": "generate_section",
            "compose_output": "compose_output"
        }
    )
    
    g.add_edge("compose_output", "save_output")
    g.add_edge("save_output", END)
    
    return g.compile()

# 컴파일된 파이프라인
plan_pipeline = build_plan_pipeline()

def invoke_plan_pipeline(initial_state: Dict[str, Any]) -> Dict[str, Any]:
    """외부 헬퍼 (Legacy 호환성 유지)"""
    reset_logger()
    return plan_pipeline.invoke(initial_state, {"recursion_limit": 200})
