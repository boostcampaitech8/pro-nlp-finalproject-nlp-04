from langgraph.graph import StateGraph, END
from state.base import GlobalState
from agents.plan import plan_generate, plan_evaluate, plan_eval_router


# 노드 설정
plan_graph = StateGraph(GlobalState)
plan_graph.add_node("generate", plan_generate)
plan_graph.add_node("evaluate", plan_evaluate)
plan_graph.set_entry_point("generate")

# 엣지 설정
plan_graph.add_edge("generate", "evaluate")
plan_graph.add_conditional_edges(
    "evaluate",
    plan_eval_router,
    {
        "pass": END,
        "retry": "generate"
    }
)

# 컴파일
plan_subgraph = plan_graph.compile()