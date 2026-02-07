"""
Plan Confidence Evaluator - 2-Stage Confidence System

Stage 1: Pre-write ResearchNeedScore
- 섹션 작성 전 리서치 필요 여부 결정

Stage 2: Post-write GroundednessScore  
- 작성 후 주장-근거 정합성 검증
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

from agents.plan_core.schemas import BlueprintItem
from models.llm import get_llm


# ===========================
# Pydantic Schemas
# ===========================

class ResearchNeedScore(BaseModel):
    """Pre-write: 리서치 필요도 평가 결과"""
    score: float = Field(..., ge=0.0, le=1.0, description="리서치 필요도 (높을수록 필요)")
    
    # 세부 평가 요소
    fact_requirement: float = Field(..., ge=0.0, le=1.0, description="팩트/수치 요구 수준")
    external_dependency: float = Field(..., ge=0.0, le=1.0, description="외부 정보 의존도")
    hallucination_risk: float = Field(..., ge=0.0, le=1.0, description="할루시네이션 발생 위험도")
    
    needs_research: bool = Field(..., description="리서치 필요 여부 (score >= 0.5)")
    reasoning: str = Field(default="", description="점수 산정 근거")
    suggested_queries: List[str] = Field(default_factory=list, description="추천 검색 쿼리")


class GroundednessScore(BaseModel):
    """Post-write: 근거 기반 품질 평가 결과"""
    score: float = Field(..., ge=0.0, le=1.0, description="근거 품질 (높을수록 OK)")
    
    # 세부 점수
    cited_claim_ratio: float = Field(..., ge=0.0, le=1.0, description="인용 마커가 붙은 주장 비율")
    entailment_ratio: float = Field(..., ge=0.0, le=1.0, description="근거로 뒷받침되는 주장 비율")
    
    unsupported_claims: List[str] = Field(default_factory=list, description="근거 없는 주장 목록")
    reasoning: str = Field(default="", description="점수 산정 근거")


# ===========================
# Stage 1: Pre-write ResearchNeedScore
# ===========================

RESEARCH_NEED_PROMPT = """
다음 기획서 섹션을 작성하기 전, 웹 리서치가 필요한지 평가하세요.

[섹션 정보]
제목: {title}
가이드라인: {guideline}

[평가 기준]

1. **fact_requirement** (팩트/수치 요구 수준)
   - 시장 규모, 경쟁사, 통계, 법규, KPI 등 외부 데이터가 필요하면 높음
   - 서비스 소개, 팀 역량, 비전 등 자체 정보이면 낮음

2. **external_dependency** (외부 정보 의존도)
   - "내 아이디어 설명" → 낮음 (0.0~0.3)
   - "시장/경쟁/트렌드 분석" → 높음 (0.7~1.0)
   
3. **hallucination_risk** (할루시네이션 위험도)
   - 검증 불가능한 수치/사실을 LLM이 지어낼 위험이 높으면 높음
   - 창의적 아이디어, 일반 상식이면 낮음

[최종 score 계산]
score = (fact_requirement + external_dependency + hallucination_risk) / 3

[needs_research 판단]
- score >= 0.5 이면 needs_research = true

[suggested_queries]
리서치가 필요한 경우, 검색에 사용할 쿼리 2~3개를 제안하세요.
"""


def evaluate_research_need(
    blueprint_item: BlueprintItem,
    planning_style: str = None
) -> ResearchNeedScore:
    """
    섹션 작성 전 리서치 필요도 평가 (Pre-write, LLM 기반)
    
    Args:
        blueprint_item: 평가할 BlueprintItem
        planning_style: 기획 스타일 (Optional context)
    
    Returns:
        ResearchNeedScore: 리서치 필요도 점수
    """
    chat = get_llm(max_tokens=2048, reasoning_effort="low")
    structured_llm = chat.with_structured_output(ResearchNeedScore)
    
    prompt = RESEARCH_NEED_PROMPT.format(
        title=blueprint_item.title,
        guideline=blueprint_item.guideline or "없음"
    )
    
    try:
        result = structured_llm.invoke(prompt)
        return result
    except Exception as e:
        # 실패 시 기본값 반환 (낮은 점수 = 리서치 불필요)
        return ResearchNeedScore(
            score=0.3,
            fact_requirement=0.3,
            external_dependency=0.3,
            hallucination_risk=0.3,
            needs_research=False,
            reasoning=f"평가 중 오류 발생: {str(e)}",
            suggested_queries=[]
        )


# ===========================
# Stage 2: Post-write GroundednessScore (TODO)
# ===========================

def evaluate_groundedness(
    content: str,
    evidence_store: List[str] = None
) -> GroundednessScore:
    """
    작성 후 근거 기반 품질 평가 (Post-write)
    
    TODO: 추후 구현
    """
    # Placeholder
    return GroundednessScore(
        score=1.0,
        cited_claim_ratio=1.0,
        entailment_ratio=1.0,
        unsupported_claims=[],
        reasoning="[TODO] Post-write 평가 미구현"
    )

