import sys
import os

# 현재 파일의 부모의 부모 폴더(src)를 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from state.base import GlobalState
from agents.idea import idea_router, analyzer_node, generator_node, evaluator_node


# 노드 설정
idea_graph = StateGraph(GlobalState)
idea_graph.add_node("analyzer", analyzer_node)
idea_graph.add_node("generator", generator_node)
idea_graph.add_node("evaluate", evaluator_node)

idea_graph.set_entry_point("analyzer")

# 엣지 설정
idea_graph.add_conditional_edges(
    "analyzer",
    idea_router,
    {
        "generator": "generator",
        # "clarifier": "clarifier" # 나중에 추가 가능
    }
)

idea_graph.add_conditional_edges(
    "evaluate",
    lambda x: x["supervision"]["last_decision"],
    {
        "REJECTED": "generator",       # 실패하면 다시 생성으로
        "WAIT_FOR_USER": END,          # 유저 답변이 필요하면 그래프 종료 (슈퍼바이저에게 복귀)
        "COMPLETE": END                # 다 끝났으면 그래프 종료 (슈퍼바이저에게 복귀)
    }
)
idea_graph.add_edge("generator", "evaluate")

# 컴파일
idea_subgraph = idea_graph.compile()

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    import json

    # 1. 이미 초안이 있는 상태를 가정 (Blueprint가 채워져 있음)
    test_state = {
        "messages": [HumanMessage(content="수익 모델 부분 말이야, 구독제 말고 건당 결제 방식으로 바꿔줄래?")],
        "idea": {
            "planning_style": "Business",
            "rationale": "초기 기획 단계",
            "target_sections": [] # Analyzer가 채울 예정
        },
        "supervision": {
            "user_intent": "CREATE", 
            "blueprint": [
                {"title": "서비스 개요", "content": "시니어 헬스케어 서비스", "guideline": "...", "is_required_from_user": False},
                {"title": "수익 모델", "content": "월 9,900원의 정기 구독 서비스", "guideline": "...", "is_required_from_user": False},
                {"title": "마케팅 전략", "content": "SNS 광고 중심", "guideline": "...", "is_required_from_user": False}
            ],
            "required_data_points": []
        }
    }

    print("🔍 [1단계: Analyzer] 사용자 의도 분석 중...")
    # analyzer_node 실행
    analyzer_result = analyzer_node(test_state)
    
    # 분석 결과 업데이트
    test_state["idea"]["target_sections"] = analyzer_result["idea"]["target_sections"]
    test_state["supervision"]["user_intent"] = analyzer_result["supervision"]["user_intent"]

    print(f"📍 분석된 의도: {test_state['supervision']['user_intent']}")
    print(f"📍 타겟 섹션: {test_state['idea']['target_sections']}")

    print("\n🔍 [2단계: Generator] 특정 섹션 업데이트 중...")
    # generator_node 실행
    final_result = generator_node(test_state)

    print("\n" + "="*60)
    print("[📋 최종 수정된 Blueprint 확인]")
    for item in final_result['supervision']['blueprint']:
        # 수정된 부분은 강조 표시
        is_updated = "✅ [수정됨]" if item['title'] in test_state['idea']['target_sections'] else "⚪ [유지됨]"
        print(f"{is_updated} {item['title']}: {item['content']}")
    print("="*60)