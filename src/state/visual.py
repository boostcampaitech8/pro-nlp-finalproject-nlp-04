"""
Visual Agent 전용 내부 상태 정의
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from state.base import GlobalState

class VisualInternalState(GlobalState):
    """시각화 생성 파이프라인 내부 상태"""
    # 1. 요청 컨텍스트
    target_section_id: Annotated[str, "시각화 대상 섹션 ID"]
    visual_request: Annotated[str, "시각화 요청 사항 (예: '표로 정리해줘')"]
    context_text: Annotated[str, "시각화 생성을 위한 참고 텍스트 (섹션 본문 등)"]
    
    # 2. 결정 및 생성
    visual_type: Annotated[str, "결정된 시각화 유형 (Table/Chart/Diagram)"]
    visual_meta: Annotated[Dict[str, Any], "시각화 메타데이터 (Purpose, Why, etc.)"]
    code: Annotated[str, "생성된 코드 (Python/Mermaid)"]
    html: Annotated[str, "렌더링된 HTML 또는 결과물"]
    
    # 3. 검증
    validation_results: Annotated[Dict[str, Any], "검증 결과"]
    retry_count: Annotated[int, "재시도 횟수"]
