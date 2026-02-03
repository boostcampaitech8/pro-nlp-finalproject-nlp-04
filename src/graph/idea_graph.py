from langgraph.graph import StateGraph, END
from state.base import GlobalState
from agents.idea import idea_generate, idea_evaluate, idea_eval_router


# 노드 설정
idea_graph = StateGraph(GlobalState)
idea_graph.add_node("generate", idea_generate)
idea_graph.add_node("evaluate", idea_evaluate)
idea_graph.set_entry_point("generate")

# 엣지 설정
idea_graph.add_edge("generate", "evaluate")
idea_graph.add_conditional_edges(
    "evaluate",
    idea_eval_router,
    {
        "pass": END,
        "retry": "generate"
    }
)

# 컴파일
idea_subgraph = idea_graph.compile()