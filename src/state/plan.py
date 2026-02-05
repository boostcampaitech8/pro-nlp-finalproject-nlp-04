"""
기획서 파이프라인 상태 정의
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict


class PlanPipelineState(TypedDict, total=False):
    """전체 기획서 파이프라인 상태"""
    # 입력
    raw_idea: str
    method: str  # "context" or "guideline"
    
    # 기획서 생성 단계
    idea: Dict[str, Any]  # StructuredIdea
    toc: Dict[str, Any]  # TableOfContents
    current_section_index: int
    sections: List[Dict[str, Any]]  # List[PlanSection]
    
    # 시각화 단계
    visual_artifacts: List[Dict[str, Any]]  # List[VisualArtifact]
    current_visual_state: Dict[str, Any]  # 현재 처리 중인 시각화 상태
    
    # 검증 단계
    validation_results: List[Dict[str, Any]]
    retry_count: int
    
    # 출력
    final_markdown: str
    output_path: str
    
    # Blueprint 기반 입력
    structured_input: Dict[str, Any]  # StructuredInput


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
