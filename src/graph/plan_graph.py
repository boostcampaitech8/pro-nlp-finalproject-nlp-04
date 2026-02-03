"""
Plan 서브그래프 - Blueprint 기반 기획서 생성 파이프라인 연결
"""
from langgraph.graph import StateGraph, END
from state.base import GlobalState
from agents.plan.orchestrator.pipeline import run_plan


def plan_generate(state: GlobalState) -> GlobalState:
    """
    GlobalState에서 Blueprint 입력을 추출하여 run_plan 실행
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
    
    # 파이프라인 실행
    result = run_plan(structured_input)
    
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


# 노드 설정
plan_graph = StateGraph(GlobalState)
plan_graph.add_node("generate", plan_generate)
plan_graph.add_node("evaluate", plan_evaluate)
plan_graph.set_entry_point("generate")

# 엣지 설정
plan_graph.add_edge("generate", "evaluate")
plan_graph.add_conditional_edges(
    "evaluate",
    plan_eval_router,
    {
        "pass": END,
        "retry": "generate"
    }
)

# 컴파일
plan_subgraph = plan_graph.compile()
