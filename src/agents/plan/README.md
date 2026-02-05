# Plan Agent (기획서 생성 에이전트)

Blueprint 기반 기획서 자동 생성 파이프라인입니다.

## 구조

```
agents/plan/
├── __init__.py          # 패키지 초기화 + 기존 함수 호환
├── __main__.py          # CLI 진입점(임시)
├── schemas.py           # 기획서 스키마 정의
├── generator.py         # 섹션 생성 로직
│
├── visual/              # 시각화 하위 에이전트
│   ├── schemas.py       # 시각화 관련 스키마
│   ├── router.py        # 시각화 유형 결정
│   ├── generator.py     # 표/다이어그램 생성
│   └── validator.py     # 시각화 적합성 검증
│
└── orchestrator/        # 파이프라인 오케스트레이터
    ├── pipeline.py      # 전체 워크플로우
    └── logger.py        # 로깅 시스템
```

## 사용법

### CLI 실행

```bash
# 테스트 실행
cd src
python -m agents.plan

# Blueprint 파일로 실행
python -m agents.plan --blueprint-file ../sample_blueprint.json
```

### 코드에서 사용

```python
from agents.plan import run_plan

blueprint_data = {
    "planning_style": "Business",
    "rationale": "...",
    "toc": ["1. 서비스 개요", "2. 시장 분석"],
    "blueprint": [...]
}

result = run_plan(blueprint_data)
print(f"출력 파일: {result['output_path']}")
```

## Blueprint 입력 형식

```json
{
    "planning_style": "Business",
    "rationale": "스타일 선택 이유",
    "system_prompt": "기획서 작성 톤/스타일 (선택)",
    "toc": ["1. 섹션1", "2. 섹션2"],
    "blueprint": [
        {
            "target_id": "item_1",
            "title": "섹션1",
            "content": "유저가 작성한 내용 (없으면 null)",
            "guideline": "LLM 생성 가이드라인"
        }
    ]
}
```

## 파이프라인 흐름

```
Blueprint 입력 → 섹션 생성 → 시각화 결정 → 시각화 생성 → 검증 → 마크다운 출력
```

## 기존 코드 호환

기존 `plan.py`의 함수들은 그대로 사용 가능:

```python
from agents.plan import plan_generate, plan_evaluate, plan_eval_router
```
