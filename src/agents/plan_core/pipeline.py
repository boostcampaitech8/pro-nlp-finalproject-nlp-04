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
    
    # =====================================================
    # [Research 연동] generate_section 이후 라우팅
    # 
    # needs_research=True인 경우:
    #   - END로 종료하여 Supervisor에게 제어를 반환
    #   - Supervisor가 RUN_RESEARCH → RUN_PLANNING으로 재호출
    #   - current_section_index는 그대로 유지되어 동일 섹션 재처리
    # 
    # needs_research=False인 경우:
    #   - increment_index로 이동하여 다음 섹션 처리
    # =====================================================
    def route_after_section(state: PlanInternalState) -> str:
        # [Explicit State] plan_status 확인
        if state.get("plan_status") == "WAITING_FOR_RESEARCH":
            return "end_for_research"
        return "increment_index"
    
    g.add_conditional_edges(
        "generate_section",
        route_after_section,
        {
            "end_for_research": END,
            "increment_index": "increment_index"
        }
    )
    
    # Route Next Section
    # [Refactor] 내부 루프 제거 -> 섹션 단위 실행 (Incremental Execution)
    # generate_section -> increment_index -> compose_output -> save_output -> END
    
    # Route Next Section (Increment 후 종료)
    # 다음 섹션이 있는지 여부는 nodes.py의 increment_index에서 
    # GlobalState.plan_status를 통해 Supervisor에게 전달됨
    g.add_edge("increment_index", "compose_output")
    g.add_edge("compose_output", "save_output")
    g.add_edge("save_output", END)
    
    return g.compile()

# 컴파일된 파이프라인
plan_pipeline = build_plan_pipeline()

def invoke_plan_pipeline(initial_state: Dict[str, Any]) -> Dict[str, Any]:
    """외부 헬퍼 (Legacy 호환성 유지)"""
    reset_logger()
    return plan_pipeline.invoke(initial_state, {"recursion_limit": 200})
