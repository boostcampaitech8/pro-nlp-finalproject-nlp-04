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
from prompts.plan_prompts import RESEARCH_NEED_PROMPT


# ===========================
# Pydantic Schemas
# ===========================

class ResearchNeedScore(BaseModel):
    """Pre-write: 리서치 필요도 평가 결과"""
    score: float = Field(..., ge=0.0, le=1.0, description="리서치 필요도 (높을수록 필요)")
    needs_research: bool = Field(..., description="리서치 필요 여부")
    research_goal: str = Field(default="", description="리서치 목적 및 필요 정보 (Context & Intent)")
    reasoning: str = Field(default="", description="평가 근거 및 공백 분석")
    
    # Optional fields for backward compatibility or detailed analysis
    fact_requirement: Optional[float] = Field(None, description="(Deprecated) 팩트 요구 수준")
    external_dependency: Optional[float] = Field(None, description="(Deprecated) 외부 의존도")
    hallucination_risk: Optional[float] = Field(None, description="(Deprecated) 할루시네이션 위험")


# ===========================
# Stage 1: Pre-write ResearchNeedScore
# ===========================




def evaluate_research_need(
    blueprint_item: BlueprintItem,
    planning_style: str = "Business",
    rationale: str = ""
) -> ResearchNeedScore:
    """
    섹션 작성 전 리서치 필요도 평가 (Pre-write, LLM 기반)
    
    Args:
        blueprint_item: 평가할 BlueprintItem
        planning_style: 기획 스타일
        rationale: 기획 의도
    
    Returns:
        ResearchNeedScore: 리서치 필요도 점수
    """
    chat = get_llm(max_tokens=2048, reasoning_effort="low")
    
    # [Fix] with_structured_output 대신 JsonOutputParser 사용 (호환성/파싱 개선)
    from langchain_core.output_parsers import JsonOutputParser
    # from langchain_core.prompts import PromptTemplate # 이미 ChatPromptTemplate을 사용하거나, 문자열 포맷팅 사용 중
    
    parser = JsonOutputParser(pydantic_object=ResearchNeedScore)
    
    # 프롬프트에 포맷 지침 추가 (Parser가 제공하는 지침 활용 가능하지만, 현재 프롬프트가 강력함)
    formatted_prompt = RESEARCH_NEED_PROMPT.format(
        planning_style=planning_style or "Business",
        rationale=rationale or "정보 없음",
        title=blueprint_item.title,
        guideline=blueprint_item.guideline or "없음"
    )
    
    import json
    import re

    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            # Chain 실행
            response = chat.invoke(formatted_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # [Fix] content가 리스트인 경우 처리 (dict인 경우 'text' 키 추출)
            if isinstance(content, list):
                extracted = []
                for part in content:
                    if isinstance(part, str):
                        extracted.append(part)
                    elif isinstance(part, dict) and "text" in part:
                        extracted.append(part["text"])
                    else:
                        extracted.append(str(part))
                content = "".join(extracted)
            
            try:
                # 1. JsonOutputParser 시도 (마크다운 블록 제거 포함)
                result_dict = parser.parse(content)
                return ResearchNeedScore(**result_dict)
            except Exception as parse_error:
                # 2. 파싱 오류 시 최소한의 복구 시도 (정규식으로 JSON 추출)
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result_dict = json.loads(json_match.group())
                    return ResearchNeedScore(**result_dict)
                raise parse_error
                
        except Exception as e:
            last_error = e
            print(f"[ResearchEvaluator] Attempt {attempt}/{max_retries} failed: {str(e)}")
            if attempt < max_retries:
                print(f"[ResearchEvaluator] Retrying...")
                continue
    
    # 모든 재시도 실패 시
    print(f"[ResearchEvaluator] All {max_retries} attempts failed. Returning default.")
    return ResearchNeedScore(
        score=0.3,
        needs_research=False,
        reasoning=f"평가 실패 (최대 재시도 초과): {str(last_error)}"
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

