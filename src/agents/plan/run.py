"""
오케스트레이터 파이프라인 - 기획서 생성 실행 인터페이스
"""
from typing import Dict, Any

# ===========================
# Helper: Run Pipeline (Logic extracted from run_plan)
# ===========================
def invoke_plan_pipeline(structured_input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Blueprint 파이프라인 실행 및 로그 처리 (run_plan의 로직)
    """
    # 1. 로거 초기화
    logger = reset_logger()
    logger.log_pipeline_start("blueprint", str(structured_input_data.get("planning_style", "")))
    
    initial_state: PlanPipelineState = {
        "structured_input": structured_input_data,
    }
    
    print("=" * 60)
    print(f"Blueprint 기반 기획서 생성 파이프라인 시작 (Graph 통합)")
    print(f"스타일: {structured_input_data.get('planning_style')}")
    print("=" * 60)
    
    # 2. 파이프라인 실행 (재귀 제한 증가)
    result = plan_pipeline.invoke(initial_state, {"recursion_limit": 200})
    
    # 3. 종료 로그 및 저장
    logger.log_pipeline_end(
        len(result.get("sections", [])),
        len(result.get("visual_artifacts", [])),
        result.get("output_path", "")
    )
    logger.save_json()
    
    print("=" * 60)
    print("파이프라인 완료!")
    print(f"출력 파일: {result.get('output_path')}")
    print("=" * 60)
    print("\n" + logger.generate_summary())
    
    return result

def run_plan(structured_input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Blueprint 기반 파이프라인 실행
    
    Args:
        structured_input_data: 외부 에이전트가 제공한 구조화된 입력 (dict)
    
    Returns:
        최종 상태 (PlanPipelineState)
    """
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
