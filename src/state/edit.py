"""
Edit Pipeline Internal State
"""
from __future__ import annotations
from typing import TypedDict, Dict, Any, Optional, Annotated
from state.base import GlobalState

class EditInternalState(GlobalState):
    """
    편집 파이프라인 내부용 상태
    GlobalState를 상속받아 전체 데이터(blueprints 등)에 접근 가능
    """
    # --- Edit Specific Internal Fields ---
    target_section_id: Annotated[str, "수정 대상 섹션 ID"]
    instruction: Annotated[str, "유저의 수정 요청"]
    
    # Logic
    match_section_index: Annotated[int, "타겟 섹션의 인덱스"]
    
    # Granular Edit Fields
    granularity: Annotated[str, "수정 단위 (section/paragraph/sentence)"]
    edit_range_start: Annotated[int | None, "수정 시작 라인 인덱스 (Inclusive, 0-based)"]
    edit_range_end: Annotated[int | None, "수정 끝 라인 인덱스 (Inclusive, 0-based)"]

    # Output (Temporary)
    regenerated_content: Annotated[str, "재생성된 결과 (전체 텍스트 합본)"]
    
    # Evaluation
    critique: Annotated[str | None, "평가 비평"]
    feedback: Annotated[str | None, "재생성 피드백"]
    retry_count: Annotated[int, "재시도 횟수"]
    
    # Debug / Provenance
    used_guideline: Annotated[str | None, "실제 생성에 사용된 가이드라인 (Instruction 포함)"]
