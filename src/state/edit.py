"""
Edit Pipeline Internal State
"""
from __future__ import annotations
from typing import TypedDict, Dict, Any, Optional, Annotated
from state.base import GlobalState

class EditInternalState(GlobalState):
    """
    편집 파이프라인 상태
    
    [입력]
    - target_section_id: 수정할 섹션 ID
    - instruction: 유저의 수정 요청사항
    - granularity: 수정 단위 (section/paragraph/sentence)
    - edit_range_start: 부분 수정 시 범위
    - edit_range_end: 부분 수정 시 범위 (legacy)
    - idea['blueprint']: 원본 기획 데이터 참조
    
    [출력]
    - regenerated_content: 재생성된 콘텐츠
    - critique: 평가 결과
    - feedback: 개선 피드백
    """
    
    # --- Input Fields ---
    target_section_id: Annotated[str, "수정 대상 섹션 ID"]
    instruction: Annotated[str, "유저의 수정 요청"]
    
    # Option: Granular Edit
    granularity: Annotated[str, "수정 단위 (section/paragraph/sentence)"]
    edit_range_start: Annotated[Optional[int], "수정 시작 라인 인덱스 (Inclusive)"]
    edit_range_end: Annotated[Optional[int], "수정 끝 라인 인덱스 (Inclusive)"]

    # --- Internal Logic ---
    match_section_index: Annotated[int, "타겟 섹션의 Blueprint 인덱스"]
    retry_count: Annotated[int, "재시도 횟수"]
    
    # --- Output Fields ---
    regenerated_content: Annotated[str, "재생성된 결과 (전체 텍스트 합본)"]
    critique: Annotated[Optional[str], "평가 비평"]
    feedback: Annotated[Optional[str], "재생성 피드백"]
    
    # --- Debug Info ---
    used_guideline: Annotated[Optional[str], "실제 생성에 사용된 가이드라인"]
