"""
기획서 생성 에이전트 패키지

이 패키지는 Blueprint 기반 기획서 생성 시스템을 제공합니다.

사용법:
    python -m agents.plan                              # 테스트 실행
    python -m agents.plan --blueprint-file FILE        # 파일로 실행

주요 모듈:
    - schemas: 기획서 관련 스키마 (StructuredInput, PlanSection 등)
    - generator: 섹션 생성 로직
    - visual/: 시각화 하위 에이전트
    - orchestrator/: 파이프라인 오케스트레이터
"""

# 기존 plan.py 기능 호환성 유지
from state.base import GlobalState


def plan_generate(state: GlobalState) -> GlobalState:
    """기획서 생성 (기존 함수 호환)"""
    return state


def plan_evaluate(state: GlobalState) -> GlobalState:
    """기획서 평가 (기존 함수 호환)"""
    return state


def plan_eval_router(state: GlobalState) -> str:
    """평가 결과에 따라 pass/retry 결정 (기존 함수 호환)"""
    return "pass"


# 주요 API export
from agents.plan.schemas import (
    StructuredInput,
    BlueprintItem,
    PlanSection,
    GeneratedPlan,
    TableOfContents,
    TableOfContentsItem,
    StructuredIdea,
)

from agents.plan.generator import (
    generate_section_from_blueprint,
    compose_plan_markdown,
)

from agents.plan.run import (
    run_plan,
)

__all__ = [
    # 기존 호환
    "plan_generate",
    "plan_evaluate", 
    "plan_eval_router",
    # 스키마
    "StructuredInput",
    "BlueprintItem",
    "PlanSection",
    "GeneratedPlan",
    "TableOfContents",
    "TableOfContentsItem",
    "StructuredIdea",
    # 생성 함수
    "generate_section_from_blueprint",
    "compose_plan_markdown",
    # 파이프라인
    "run_plan",
]
