"""
시각화 에이전트 패키지
"""
from typing import Optional, Dict, Any

from agents.visual_core.schemas import (
    Decision,
    VisualMeta,
    VisualArtifact,
    TableType,
    DiagramType,
)

from agents.visual_core.router import (
    decide_node,
    generate_visual_meta,
    route_next,
)

from agents.visual_core.generator import (
    render_table,
    render_diagram,
    render_chart,
    image_search,
    image_gen,
    create_visual_artifact,
)

from agents.visual_core.validator import (
    validate_visual,
    validate_and_decide_retry,
    ValidationResult,
)

from agents.plan_core.logger import get_logger, LogLevel


def run_visual_for_section(
    section_id: str, 
    section_title: str, 
    section_text: str
) -> Optional[Dict[str, Any]]:
    """
    섹션에 대한 시각화 처리 (plan_core용 헬퍼)
    
    Returns:
        시각화가 필요한 경우 artifact dict, 불필요하면 None
    """
    logger = get_logger()
    
    # 1. 시각화 필요 여부 판단
    router_state = {
        "section_id": section_id,
        "section_title": section_title,
        "section_text": section_text,
        "retry_count": 0
    }
    
    router_state = decide_node(router_state)
    decision = Decision(**router_state.get("decision", {}))
    
    logger.log_visual_decision(section_id, router_state.get("decision", {}))
    
    # 시각화 불필요
    if not any([decision.needs_table, decision.needs_diagram, decision.needs_chart,
                decision.needs_image_search, decision.needs_image_gen]):
        return None
    
    # 2. 메타데이터 생성
    router_state = generate_visual_meta(router_state)
    
    # 3. 시각화 생성
    try:
        if decision.needs_chart:
            router_state = render_chart(router_state)
            visual_type = "chart"
        elif decision.needs_diagram:
            router_state = render_diagram(router_state)
            visual_type = "diagram"
        elif decision.needs_table:
            router_state = render_table(router_state)
            visual_type = "table"
        elif decision.needs_image_search:
            router_state = image_search(router_state)
            visual_type = "image_search"
        elif decision.needs_image_gen:
            router_state = image_gen(router_state)
            visual_type = "image_gen"
        else:
            return None
            
        logger.log_visual_generation(section_id, visual_type, True)
        
        # 4. Artifact 반환
        visual_meta_data = router_state.get("visual_meta", {})
        
        # [Fix] VisualArtifact 스키마에 맞게 구조화
        return {
            "section_number": str(section_id),
            "meta": {
                "visual_type": visual_type,
                "purpose": visual_meta_data.get("purpose", "시각화 목적 미정"), 
                "why_this_format": visual_meta_data.get("why_this_format", "자동 생성됨"),
                "data_source": visual_meta_data.get("data_source", ""),
                "placeholder": visual_meta_data.get("placeholder", ""),
                "content": visual_meta_data.get("content", ""),
                "image_path": visual_meta_data.get("image_path"),
                "image_url": visual_meta_data.get("image_url"),
            },
            "is_placeholder": False
        }
        
    except Exception as e:
        logger.log_visual_generation(section_id, "unknown", False, str(e))
        return None


__all__ = [
    # 스키마
    "Decision",
    "VisualMeta",
    "VisualArtifact",
    "TableType",
    "DiagramType",
    # 라우터
    "decide_node",
    "generate_visual_meta",
    "route_next",
    # 생성기
    "render_table",
    "render_diagram",
    "render_chart",
    "image_search",
    "image_gen",
    "create_visual_artifact",
    # 검증기
    "validate_visual",
    "validate_and_decide_retry",
    "ValidationResult",
    # 헬퍼
    "run_visual_for_section",
]

