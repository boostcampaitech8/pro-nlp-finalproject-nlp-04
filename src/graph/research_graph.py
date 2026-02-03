from langgraph.graph import StateGraph, END
from state.base import GlobalState
from agents.research import research_generate, research_evaluate, research_eval_router


# 노드 설정
research_graph = StateGraph(GlobalState)
research_graph.add_node("generate", research_generate)
research_graph.add_node("evaluate", research_evaluate)
research_graph.set_entry_point("generate")

# 엣지 설정
research_graph.add_edge("generate", "evaluate")
research_graph.add_conditional_edges(
    "evaluate",
    research_eval_router,
    {
        "pass": END,
        "retry": "generate"
    }
)

# 컴파일
research_subgraph = research_graph.compile()