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
    g.add_node("increment_index", increment_section_index_node)
    g.add_node("compose_output", compose_output_node)
    g.add_node("save_output", save_output_node)
    
    # Init
    g.set_entry_point("parse_input")
    g.add_edge("parse_input", "generate_section")
    
    # Edge: Generate Section -> Increment Index (No more visual loop)
    g.add_edge("generate_section", "increment_index")
    
    # Route Next Section
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
