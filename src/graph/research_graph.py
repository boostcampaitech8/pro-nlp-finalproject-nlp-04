from langgraph.graph import StateGraph, END
from state.base import GlobalState
from state.research import ResearchState
from agents.research import research_generate, research_evaluate, research_eval_router
from agents.research import generate_queries, search_with_tavily, analysis_search_results, upsert_qdrant, execute_hybrid_search


# # 노드 설정
# research_graph = StateGraph(GlobalState)
# research_graph.add_node("generate", research_generate)
# research_graph.add_node("evaluate", research_evaluate)
# research_graph.set_entry_point("generate")

# # 엣지 설정
# research_graph.add_edge("generate", "evaluate")
# research_graph.add_conditional_edges(
#     "evaluate",
#     research_eval_router,
#     {
#         "pass": END,
#         "retry": "generate"
#     }
# )

def check_analyst(state: ResearchState):
    if state.is_analysis_need == True:
        return "analysis"
    else:
        return END

research_graph = StateGraph(ResearchState)

research_graph.add_node("query_gen", generate_queries)
research_graph.add_node("search", search_with_tavily)
research_graph.add_node("upsert_qdrant", upsert_qdrant)
research_graph.add_node("hybrid_search", execute_hybrid_search)
research_graph.add_node("analysis", analysis_search_results)

research_graph.set_entry_point("query_gen")
research_graph.add_edge("query_gen", "search")
research_graph.add_edge("search", "upsert_qdrant")
research_graph.add_edge("upsert_qdrant", "hybrid_search")
research_graph.add_conditional_edges(
    "hybrid_search",
    check_analyst,
    {"analysis": "analysis", END: END})
research_graph.add_edge("analysis", END)

# 컴파일
research_subgraph = research_graph.compile()

if __name__ == '__main__':
    from dotenv import load_dotenv
    
    load_dotenv()

    inputs = {"question": "게임 내 신규 유저 지원 시스템을 위한 기획서 양식이 필요해."}
    config = {"configurable": {"thread_id": "1"}}

    output = research_subgraph.invoke(inputs, config)