from langgraph.graph import StateGraph, END
from state.base import GlobalState
from graph.idea_graph import idea_subgraph
from graph.plan_graph import plan_subgraph
from graph.research_graph import research_subgraph
from agents.supervisor import supervisor_node, ask_user, supervisor_router


# 노드 설정
supervisor_graph = StateGraph(GlobalState)
supervisor_graph.add_node("supervisor", supervisor_node)
supervisor_graph.add_node("ask_user", ask_user)
supervisor_graph.add_node("idea_phase", idea_subgraph)
supervisor_graph.add_node("plan_phase", plan_subgraph)
supervisor_graph.add_node("research_phase", research_subgraph)
supervisor_graph.set_entry_point("supervisor")

# 엣지 설정
supervisor_graph.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "ask_user": "ask_user",
        "invoke_idea": "idea_phase",
        "invoke_plan": "plan_phase",
        "invoke_research": "research_phase",
        "supervisor_node": "supervisor"
    }
)
supervisor_graph.add_edge("ask_user", END)
supervisor_graph.add_edge("idea_phase", "supervisor")
supervisor_graph.add_edge("plan_phase", "supervisor")
supervisor_graph.add_edge("research_phase", "supervisor")

# 컴파일
supervisor_app = supervisor_graph.compile()