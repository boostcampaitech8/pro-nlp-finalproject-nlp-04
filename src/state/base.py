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
    
class FormOption(TypedDict):
    label: str
    value: str

class FormSection(TypedDict):
    current_section: str
    question: str
    options: List[FormOption]
    guide_text: str

class FormRequest(TypedDict):
    message: str
    forms: List[FormSection]

class GlobalState(TypedDict):
    messages: Annotated[list, add_messages]
    awaiting_input: Annotated[bool, 'Awaiting Input']
    input_request: Annotated[str | None, 'Input Request']
    form_request: Annotated[FormRequest | None, 'Form Request'] # Added form_request
    user_response: Annotated[str | None, 'User Response']
    current_task: Annotated[str | None, 'Current Task']
    idea: IdeaState
    supervision: SupervisionState
    
    # Plan 파이프라인 연결용 (선택적)
    blueprint: Annotated[Optional[List[Dict[str, Any]]], 'Blueprint Items']
    plan_output: Annotated[Optional[Dict[str, Any]], 'Plan Pipeline Output']