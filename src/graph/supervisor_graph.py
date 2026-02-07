from langgraph.graph import StateGraph, END
from state.base import GlobalState
from graph.idea_graph import idea_subgraph
from graph.plan_graph import plan_subgraph
# =====================================================
# [Research 연동] run_research_for_plan 래퍼 함수 사용
# 
# research_subgraph는 ResearchState를 기대하지만,
# run_research_for_plan은 GlobalState를 받아서 내부적으로 변환 후
# research_subgraph를 호출하고 결과를 GlobalState.research에 저장
# =====================================================
from graph.research_graph import run_research_for_plan
from agents.supervisor import supervisor_node, ask_user, supervisor_router


# 노드 설정
supervisor_graph = StateGraph(GlobalState)
supervisor_graph.add_node("supervisor", supervisor_node)
supervisor_graph.add_node("ask_user", ask_user)
supervisor_graph.add_node("idea_phase", idea_subgraph)
supervisor_graph.add_node("plan_phase", plan_subgraph)
# Research 노드: GlobalState <-> ResearchState 변환을 담당하는 래퍼 사용
supervisor_graph.add_node("research_phase", run_research_for_plan)
supervisor_graph.set_entry_point("supervisor")

# 엣지 설정
supervisor_graph.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "ASK_USER": "ask_user",
        "RUN_IDEA_STRUCTURING": "idea_phase",
        "RUN_PLANNING": "plan_phase",
        "RUN_RESEARCH": "research_phase",
        "supervisor_node": "supervisor"
    }
)
supervisor_graph.add_edge("ask_user", END)
supervisor_graph.add_edge("idea_phase", "supervisor")
supervisor_graph.add_edge("plan_phase", "supervisor")
supervisor_graph.add_edge("research_phase", "supervisor")

# 컴파일
supervisor_app = supervisor_graph.compile()