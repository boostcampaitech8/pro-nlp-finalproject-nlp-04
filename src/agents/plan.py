"""
Plan Agent Adapter Functions (Facade)
InternalState(GlobalState) 패턴 적용
"""
from typing import Dict, Any
from state.base import GlobalState
from state.plan import PlanInternalState
from agents.plan_core.pipeline import plan_pipeline
from agents.plan_core.logger import get_logger, LogLevel

def plan_generate(state: GlobalState) -> GlobalState:
    """
    [진입점] GlobalState를 기반으로 PlanInternalState를 초기화하여 내부 파이프라인 실행
    """
    # 1. 초기 내부 상태 구성
    # GlobalState의 모든 내용을 복사하고, Plan 전용 변수들을 초기화합니다.
    plan_data = state.get("plan", {})
    
    # =====================================================
    # [Research 연동] current_section_index 유지
    # 
    # 리서치 후 재호출 시 동일 섹션부터 재개하기 위해
    # GlobalState.plan에서 current_section_index를 가져옴
    # 없으면 0으로 초기화
    # =====================================================
    existing_index = plan_data.get("current_section_index", 0)
    existing_sections = plan_data.get("sections", [])
    
    initial_internal_state = state.copy()
    initial_internal_state.update({
        "sections": existing_sections,  # 기존 섹션 유지
        "visual_artifacts": plan_data.get("visual_artifacts", []),
        "temp_visual_state": {},
        "final_markdown": "",
        "current_section_index": existing_index,  # 기존 인덱스 유지
        "output_path": plan_data.get("output_path", ""), # [Fix] 기존 경로 유지
        "plan_status": "IN_PROGRESS", # 기본 상태
        # [Fix] 리서치 데이터를 명시적으로 전달하여 섹션 생성 시 활용
        "research": state.get("research", {}),
    })
    
    # 2. 전제조건 확인 (Blueprint가 있어야 함)
    # PlanState에 있거나, IdeaState에 있는 blueprint를 확인
    blueprint = state.get("idea", {}).get("blueprint", [])
    
    if not blueprint:
        logger = get_logger()
        logger.log(LogLevel.WARNING, "plan_generate", "Blueprint가 없습니다. 생성을 건너뜁니다.", {})
        return state
    
    # 3. 내부 파이프라인 실행
    logger = get_logger()
    logger.log(LogLevel.INFO, "plan_generate", f"Plan Pipeline 시작 (섹션 {existing_index}부터)", {
        "starting_index": existing_index
    })
    # recursion_limit은 invoke 시점에 전달
    result = plan_pipeline.invoke(initial_internal_state, {"recursion_limit": 200})
    
    # 4. 결과 매핑 (내부 상태의 변화를 GlobalState['plan']에 집약)
    updated_plan_state = state.get("plan", {}).copy()
    updated_plan_state.update({
        "sections": result.get("sections", []),
        "visual_artifacts": result.get("visual_artifacts", []),
        "final_markdown": result.get("final_markdown", ""),
        "output_path": result.get("output_path", ""),
        "current_section_index": result.get("current_section_index", 0),
        "plan_status": result.get("plan_status", "IN_PROGRESS")
    })
    
    state["plan"] = updated_plan_state
    
    # =====================================================
    # [Research 연동] 파이프라인에서 research 상태를 GlobalState로 전달
    # 
    # pipeline이 needs_research=True로 종료된 경우:
    #   - result['research']에 쿼리 및 섹션 정보가 담겨 있음
    #   - Supervisor가 이를 감지하여 RUN_RESEARCH로 라우팅
    # =====================================================
    if result.get("research"):
        state["research"] = result["research"]
    
    return state


def plan_evaluate(state: GlobalState) -> GlobalState:
    """결과 평가 및 로깅"""
    logger = get_logger()
    
    plan_data = state.get("plan", {})
    sections_count = len(plan_data.get("sections", []))
    status = plan_data.get("plan_status", "UNKNOWN")
    
    logger.log(LogLevel.INFO, "plan_evaluate", 
        f"기획 생성 노드 종료 (섹션 수: {sections_count}, 상태: {status})", {
            "sections_count": sections_count,
            "status": status,
            "current_index": plan_data.get("current_section_index")
        })
    return state


def plan_eval_router(state: GlobalState) -> str:
    """다음 단계 결정"""
    plan_data = state.get("plan", {})
    
    # [Fix] 리서치 대기 상태면 서브그래프를 종료하고 Supervisor에게 제어권 반환 (무한루프 방지)
    if plan_data.get("plan_status") == "WAITING_FOR_RESEARCH":
        return "pass"
        
    if plan_data.get("sections"):
        return "pass"
    return "retry"
