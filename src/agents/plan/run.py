"""
오케스트레이터 파이프라인 - 기획서 생성 실행 인터페이스
"""
from typing import Dict, Any
from graph.plan_graph import invoke_plan_pipeline


def run_plan(structured_input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Blueprint 기반 파이프라인 실행
    
    Args:
        structured_input_data: 외부 에이전트가 제공한 구조화된 입력 (dict)
    
    Returns:
        최종 상태 (PlanPipelineState)
    """
    # plan_graph.py에 통합된 실행 로직 사용
    return invoke_plan_pipeline(structured_input_data)


if __name__ == "__main__":
    # 테스트용 더미 데이터
    dummy_input = {
        "planning_style": "General",
        "rationale": "테스트 실행",
        "toc": ["1. 소개", "2. 기능"],
        "blueprint": [
            {
                "target_id": "item_1",
                "title": "소개",
                "content": "이것은 테스트 소개입니다.",
                "guideline": None
            },
            {
                "target_id": "item_2",
                "title": "기능",
                "content": None,
                "guideline": "주요 기능을 나열하세요."
            }
        ]
    }
    
    run_plan(dummy_input)
