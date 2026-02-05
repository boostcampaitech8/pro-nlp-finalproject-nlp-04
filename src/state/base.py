from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages

class IdeaState(TypedDict):
    planning_style: Annotated[str, '기획 스타일']
    rationale: Annotated[str, '기획 이유']
    toc: Annotated[List[str], '기획 목차']
    blueprint: Annotated[List[Dict[str, Any]], '기획 청사진']
    last_decision: Annotated[str, 'Evaluator의 결정']
    messages: Annotated[str, 'AI가 생성한 메시지']
    

class PlanState(TypedDict):
    sections: Annotated[List[str], '생성된 섹션 본문 리스트']
    final_markdown: Annotated[str, '합쳐진 전체 마크다운 문자열']
    output_path: Annotated[str, '저장된 파일 경로']
    visual_artifacts: Annotated[Dict[str, Any], '시각화(표/차트) 메타데이터 리스트']


class SupervisionState(TypedDict):
    last_decision: Annotated[str, '마지막 결정']

class GlobalState(TypedDict):
    messages: Annotated[list, add_messages]
    awaiting_input: Annotated[bool, '입력 대기 여부']
    input_request: Annotated[str | None, '입력 요청']
    user_response: Annotated[str | None, '사용자 응답']
    current_task: Annotated[str | None, '현재 작업']
    idea: IdeaState
    plan: PlanState
    supervision: SupervisionState