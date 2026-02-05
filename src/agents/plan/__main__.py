"""
기획서 생성 파이프라인 진입점

실행 방법:
    cd src
    python -m agents.plan                              # 테스트 실행
    python -m agents.plan --blueprint-file FILE        # 파일로 실행
"""
import sys
from pathlib import Path

_current_file = Path(__file__).resolve()
_src_dir = _current_file.parent.parent.parent  # agents/plan/__main__.py -> src/
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="기획서 생성 파이프라인")
    parser.add_argument(
        "--blueprint-file",
        type=str,
        help="Blueprint JSON 파일 경로"
    )

    args = parser.parse_args()

    if args.blueprint_file:
        run_from_file(args.blueprint_file)
    else:
        run_test()


def run_from_file(file_path: str):
    """Blueprint 파일로 파이프라인 실행"""
    from agents.plan.run import run_plan

    blueprint_path = Path(file_path)
    if not blueprint_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {file_path}")
        return

    with open(blueprint_path, "r", encoding="utf-8") as f:
        blueprint_data = json.load(f)

    result = run_plan(blueprint_data)

    # 결과 요약
    print("\n" + "=" * 60)
    print("실행 결과 요약")
    print("=" * 60)
    print(f"섹션 수: {len(result.get('sections', []))}")
    print(f"시각화 수: {len(result.get('visual_artifacts', []))}")
    print(f"출력 파일: {result.get('output_path')}")


def run_test():
    """테스트 실행"""
    from agents.plan.run import run_plan

    print("=" * 60)
    print("기획서 생성 파이프라인 테스트 실행")
    print("=" * 60)

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

    result = run_plan(dummy_input)

    print("\n테스트 완료!")
    print(f"출력 파일: {result.get('output_path')}")


if __name__ == "__main__":
    main()
