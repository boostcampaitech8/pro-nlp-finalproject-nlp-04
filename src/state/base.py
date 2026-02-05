from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages


class IdeaState(TypedDict):
    planning_style: Annotated[str, 'Planning Style']
    rationale: Annotated[str, 'Rationale']
    toc: Annotated[List[str], 'Table of Contents']
    

class SupervisionState(TypedDict):
    stage: Annotated[str, 'Stage']
    user_intent: Annotated[str, 'User Intent']
    last_decision: Annotated[str, 'Last Decision']


class GlobalState(TypedDict):
    messages: Annotated[list, add_messages]
    awaiting_input: Annotated[bool, 'Awaiting Input']
    input_request: Annotated[str | None, 'Input Request']
    user_response: Annotated[str | None, 'User Response']
    current_task: Annotated[str | None, 'Current Task']
    idea: IdeaState
    supervision: SupervisionState
    
    # Plan 파이프라인 연결용 (선택적)
    blueprint: Annotated[Optional[List[Dict[str, Any]]], 'Blueprint Items']
    plan_output: Annotated[Optional[Dict[str, Any]], 'Plan Pipeline Output']