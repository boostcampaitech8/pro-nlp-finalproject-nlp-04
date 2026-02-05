import sys
import os

# 현재 파일의 부모의 부모 폴더(src)를 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from state.base import InternalState
from agents.idea import idea_router, analyzer_node, creator_node, updater_node, questioner_node, evaluator_node


# 노드 설정
idea_graph = StateGraph(InternalState)
idea_graph.add_node("analyzer", analyzer_node)
idea_graph.add_node("creator", creator_node)
idea_graph.add_node("updater", updater_node)
idea_graph.add_node("questioner", questioner_node)
idea_graph.add_node("evaluator", evaluator_node)

idea_graph.set_entry_point("analyzer")

# 엣지 설정
idea_graph.add_conditional_edges(
    "analyzer",
    idea_router,
    {
        "creator" : "creator",
        "updater" : "updater",
        "questioner" : "questioner",
        "evaluator" : "evaluator" 
    }
)
idea_graph.add_edge("creator", "questioner")
idea_graph.add_edge("updater", "questioner")
idea_graph.add_edge("questioner", "evaluator")

idea_graph.add_conditional_edges(
    "evaluator",
    lambda x: x["supervision"]["last_decision"],
    {
        "REJECTED": "analyzer",       
        "WAIT_FOR_USER": END,          
        "COMPLETE": END               
    }
)

# 컴파일
idea_subgraph = idea_graph.compile()