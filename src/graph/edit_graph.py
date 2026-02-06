"""
Edit Pipeline Graph
"""
from langgraph.graph import StateGraph, END
from state.edit import EditInternalState
from agents.plan_core.edit.nodes import regenerate_section_node
from agents.plan_core.edit.evaluation import evaluate_section_node, route_evaluation

def build_edit_pipeline():
    """
    단일 섹션 재생성 파이프라인 (Self-Correction Loop 포함)
    Node: regenerate -> evaluate -> (loop) or end
    """
    workflow = StateGraph(EditInternalState)
    
    # Node 추가
    workflow.add_node("regenerate", regenerate_section_node)
    workflow.add_node("evaluate", evaluate_section_node)
    
    # Flow 정의
    workflow.set_entry_point("regenerate")
    workflow.add_edge("regenerate", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        route_evaluation,
        {
            "regenerate": "regenerate",
            "end": END
        }
    )
    
    return workflow.compile()

# Singleton Instance
edit_subgraph = build_edit_pipeline()
