from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages


class IdeaState(TypedDict):
    planning_style: Annotated[str, 'Planning Style']
    rationale: Annotated[str, 'Rationale']
    toc: Annotated[List[str], 'Table of Contents']
    blueprint: Annotated[Optional[List[Dict[str, Any]]], 'Blueprint Items (Output of Idea)']
    

class PlanState(TypedDict, total=False):
    blueprint: Annotated[List[Dict[str, Any]], 'Blueprint Items (Input for Plan)']
    sections: Annotated[List[Dict[str, Any]], 'Plan Sections']
    visual_artifacts: Annotated[List[Dict[str, Any]], 'Visual Artifacts']
    final_markdown: Annotated[str, 'Final Markdown']
    output_path: Annotated[str, 'Output Path']


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
    plan: PlanState
    research: ResearchState
    supervision: SupervisionState