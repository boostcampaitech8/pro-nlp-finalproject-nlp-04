"""
Plan Agent Adapter Functions (Facade)
InternalState(GlobalState) 패턴 적용
"""
from typing import Dict, Any
from state.base import GlobalState
from state.plan import PlanInternalState
from agents.plan_core.pipeline import plan_pipeline

def plan_generate(state: GlobalState) -> GlobalState:
    """
    [진입점] GlobalState를 기반으로 PlanInternalState를 초기화하여 내부 파이프라인 실행
    """
    # 1. 초기 내부 상태 구성
    # GlobalState의 모든 내용을 복사하고, Plan 전용 변수들을 초기화합니다.
    plan_data = state.get("plan", {})
    
    initial_internal_state = state.copy()
    initial_internal_state.update({
        "sections": [],
        "visual_artifacts": [],
        "temp_visual_state": {},
        "final_markdown": "",
        "current_section_index": 0,
        "output_path": ""
    })
    
    # 2. 전제조건 확인 (Blueprint가 있어야 함)
    # PlanState에 있거나, IdeaState에 있는 blueprint를 확인
    blueprint = plan_data.get("blueprint") or state.get("idea", {}).get("blueprint")
    
    if not blueprint:
        print("[plan_generate] Blueprint가 없습니다. 생성을 건너뜁니다.")
        return state
    
    # 3. 내부 파이프라인 실행
    print(">>> Starting Internal Plan Pipeline...")
    # recursion_limit은 invoke 시점에 전달
    result = plan_pipeline.invoke(initial_internal_state, {"recursion_limit": 200})
    
    # 4. 결과 매핑 (내부 상태의 변화를 GlobalState['plan']에 집약)
    updated_plan_state = state.get("plan", {}).copy()
    updated_plan_state.update({
        "sections": result.get("sections", []),
        "visual_artifacts": result.get("visual_artifacts", []),
        "final_markdown": result.get("final_markdown", ""),
        "output_path": result.get("output_path", "")
    })
    
    state["plan"] = updated_plan_state
    return state


def plan_evaluate(state: GlobalState) -> GlobalState:
    """결과 평가 및 로깅"""
    plan_data = state.get("plan", {})
    sections_count = len(plan_data.get("sections", []))
    print(f"[plan_evaluate] 생성된 섹션 수: {sections_count}")
    return state


def plan_eval_router(state: GlobalState) -> str:
    """다음 단계 결정"""
    plan_data = state.get("plan", {})
    if plan_data.get("sections"):
        return "pass"
    return "retry"
