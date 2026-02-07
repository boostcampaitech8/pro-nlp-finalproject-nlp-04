from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages

class IdeaState(TypedDict):
    planning_style: Annotated[str, '기획 스타일']
    rationale: Annotated[str, '기획 이유']
    toc: Annotated[List[str], '기획 목차']
    blueprint: Annotated[List[Dict[str, Any]], '기획 청사진']
    last_decision: Annotated[str, 'Evaluator의 결정']
    messages: Annotated[str, 'AI가 생성한 메시지']
    form: Annotated[List[Dict[str, Any]], 'AI가 생성한 질문']
    

class PlanState(TypedDict):
    sections: Annotated[List[str], '생성된 섹션 본문 리스트']
    final_markdown: Annotated[str, '합쳐진 전체 마크다운 문자열']
    output_path: Annotated[str, '저장된 파일 경로']
    visual_artifacts: Annotated[Dict[str, Any], '시각화(표/차트) 메타데이터 리스트']


class EditState(TypedDict):
    last_edited_section: Annotated[str, "마지막으로 수정된 섹션 ID"]
    edit_history: Annotated[List[str], "수정 이력"]


class SupervisionState(TypedDict):
    goal: Annotated[str, 'Produce a high-quality vibe-based planning document']
    last_decision: Annotated[str, '마지막 결정']
    current_task: Annotated[str | None, '현재 작업']
    reason: Annotated[str, '결정 이유']
    pending_request: Annotated[str | None, '에이전트의 사용자 입력 요청']
    request_type: Annotated[str | None, '요청 타입']


class VisualState(TypedDict):
    last_generated_code: Annotated[str, "마지막 생성 코드"]
    artifacts: Annotated[Dict[str, Any], "생성된 시각화 결과물 (ID 매핑)"]

class GlobalState(TypedDict):
    messages: Annotated[list, add_messages]
    awaiting_input: Annotated[bool, '입력 대기 여부']
    input_request: Annotated[str | None, '사용자 입력 요청 내용']
    user_response: Annotated[str | None, '사용자 응답']
    completed_steps: Annotated[str, '완료된 단계']
    idea: IdeaState
    plan: PlanState
    edit: EditState
    visual: VisualState
    supervision: SupervisionState