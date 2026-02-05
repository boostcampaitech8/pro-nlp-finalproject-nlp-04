"""
기획서 파이프라인 내부 상태 정의
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from state.base import GlobalState


class PlanInternalState(GlobalState):
    """기획서 생성 파이프라인 내부 전용 상태 (전역 상태 확장)"""
    # 내부 가공용 데이터
    sections: Annotated[List[Dict[str, Any]], "생성된 섹션 리스트 (PlanSection)"]
    visual_artifacts: Annotated[List[Dict[str, Any]], "생성된 시각화 리스트 (VisualArtifact)"]
    final_markdown: Annotated[str, "최종 조합된 마크다운 텍스트"]
    
    # 진행 제어용
    current_section_index: Annotated[int, "현재 작성 중인 섹션 인덱스"]
    temp_visual_state: Annotated[Dict[str, Any], "시각화 처리를 위한 임시 상태"]
    
    # 출력 경로
    output_path: Annotated[str, "최종 파일 저장 경로"]


class SectionProcessState(TypedDict, total=False):
    """섹션 처리 상태 (시각화 서브 파이프라인용)"""
    section_id: str
    section_title: str
    section_text: str
    
    # 시각화 결정
    decision: Dict[str, Any]
    visual_meta: Dict[str, Any]
    
    # 생성 결과
    artifacts: Dict[str, Any]
    
    # 검증
    validation_result: Dict[str, Any]
    retry_count: int
    should_retry: bool
