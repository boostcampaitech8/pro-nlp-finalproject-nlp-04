"""
Plan 서브그래프 - Blueprint 기반 기획서 생성 파이프라인 연결
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from state.base import GlobalState
from state.plan import PlanPipelineState
from agents.plan.logger import reset_logger

# Import nodes specifically for the pipeline graph
from agents.plan.nodes import (
    parse_input_node,
    generate_section_node,
    visual_decide_node,
    visual_generate_node,
    visual_validate_node,
    visual_finalize_node,
    increment_section_index_node,
    compose_output_node,
    save_output_node,
    check_needs_visual,
    route_visual_validation,
    route_next_section,
)

# ===========================
# Plan Pipeline Graph (Detailed)
# ===========================

def build_plan_pipeline():
    """Blueprint 기반 기획서 생성 파이프라인 빌드"""
    g = StateGraph(PlanPipelineState)
    
    # 노드 추가
    g.add_node("parse_input", parse_input_node)
    g.add_node("generate_section", generate_section_node)
    g.add_node("visual_decide", visual_decide_node)
    g.add_node("visual_generate", visual_generate_node)
    g.add_node("visual_validate", visual_validate_node)
    g.add_node("visual_finalize", visual_finalize_node)
    g.add_node("next_section", increment_section_index_node)
    g.add_node("compose_output", compose_output_node)
    g.add_node("save_output", save_output_node)
    
    # 엣지 연결
    g.set_entry_point("parse_input")
    g.add_edge("parse_input", "generate_section")
    g.add_edge("generate_section", "visual_decide")
    
    # 시각화 분기
    g.add_conditional_edges(
        "visual_decide",
        check_needs_visual,
        {
            "visual_generate": "visual_generate",
            "next_section": "next_section"
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
    
    g.add_edge("visual_finalize", "next_section")
    
    # 다음 섹션 분기
    g.add_conditional_edges(
        "next_section",
        route_next_section,
        {
            "generate_section": "generate_section",
            "compose_output": "compose_output"
        }
    )
    
    g.add_edge("compose_output", "save_output")
    g.add_edge("save_output", END)
    
    return g.compile()

# 유일한 plan_pipeline 인스턴스 (module-level)
plan_pipeline = build_plan_pipeline()


# ===========================
# Helper: Run Pipeline (Logic extracted from run_plan)
# ===========================
def invoke_plan_pipeline(structured_input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Blueprint 파이프라인 실행 및 로그 처리 (run_plan의 로직)
    """
    # 1. 로거 초기화
    logger = reset_logger()
    logger.log_pipeline_start("blueprint", str(structured_input_data.get("planning_style", "")))
    
    initial_state: PlanPipelineState = {
        "structured_input": structured_input_data,
    }
    
    print("=" * 60)
    print(f"Blueprint 기반 기획서 생성 파이프라인 시작 (Graph 통합)")
    print(f"스타일: {structured_input_data.get('planning_style')}")
    print("=" * 60)
    
    # 2. 파이프라인 실행 (재귀 제한 증가)
    result = plan_pipeline.invoke(initial_state, {"recursion_limit": 200})
    
    # 3. 종료 로그 및 저장
    logger.log_pipeline_end(
        len(result.get("sections", [])),
        len(result.get("visual_artifacts", [])),
        result.get("output_path", "")
    )
    logger.save_json()
    
    print("=" * 60)
    print("파이프라인 완료!")
    print(f"출력 파일: {result.get('output_path')}")
    print("=" * 60)
    print("\n" + logger.generate_summary())
    
    return result


# ===========================
# Global Plan Graph (Wrapper)
# ===========================

def plan_generate(state: GlobalState) -> GlobalState:
    """
    GlobalState에서 Blueprint 입력을 추출하여 plan_pipeline 실행
    """
    idea = state.get("idea", {})
    
    # GlobalState → StructuredInput 변환
    structured_input = {
        "planning_style": idea.get("planning_style", "General"),
        "rationale": idea.get("rationale", ""),
        "toc": idea.get("toc", []),
        "blueprint": state.get("blueprint", [])
    }
    
    # Blueprint가 없으면 빈 상태 반환
    if not structured_input["blueprint"]:
        print("[plan_generate] Blueprint가 없습니다. 스킵합니다.")
        return state
    
    # 파이프라인 직접 실행 (invoke_plan_pipeline 사용)
    result = invoke_plan_pipeline(structured_input)
    
    # 결과 저장
    state["plan_output"] = {
        "sections": result.get("sections", []),
        "visual_artifacts": result.get("visual_artifacts", []),
        "final_markdown": result.get("final_markdown", ""),
        "output_path": result.get("output_path", "")
    }
    
    return state


def plan_evaluate(state: GlobalState) -> GlobalState:
    """
    Plan 결과 평가
    """
    plan_output = state.get("plan_output")
    
    if not plan_output:
        return state
    
    # 평가 로직 (현재는 통과)
    sections_count = len(plan_output.get("sections", []))
    print(f"[plan_evaluate] 생성된 섹션 수: {sections_count}")
    
    return state


def plan_eval_router(state: GlobalState) -> str:
    """
    평가 결과에 따라 pass/retry 결정
    """
    plan_output = state.get("plan_output")
    
    # 출력이 있으면 통과
    if plan_output and plan_output.get("sections"):
        return "pass"
    
    # Blueprint가 없으면 통과 (스킵된 경우)
    if not state.get("blueprint"):
        return "pass"
    
    return "retry"


# Global Graph 구성
plan_graph = StateGraph(GlobalState)
plan_graph.add_node("generate", plan_generate)
plan_graph.add_node("evaluate", plan_evaluate)
plan_graph.set_entry_point("generate")

plan_graph.add_edge("generate", "evaluate")
plan_graph.add_conditional_edges(
    "evaluate",
    plan_eval_router,
    {
        "pass": END,
        "retry": "generate"
    }
)

plan_subgraph = plan_graph.compile()
