"""
Research 그래프 (KG 통합)

파이프라인:
    query_gen → kg_query → search → kg_save → (analysis) → END
    
    KG 통합 포인트:
    1. kg_query: 검색 전 KG 조회 (캐시)
    2. kg_save: 검색 직후 KG 저장 (실시간 구축)
"""

from langgraph.graph import StateGraph, END
from state.base import GlobalState
from state.research import ResearchState
from agents.research import (
    research_generate,
    research_evaluate,
    research_eval_router,
    generate_queries,
    search_with_tavily,
    analysis_search_results,
    kg_query_node,              # ← KG 노드
    kg_extract_and_save_node    # ← KG 노드
)
def check_need_search(state: ResearchState) -> str:
    """
    라우터: 검색 필요 여부 판단
    
    KG에 충분한 정보가 있으면 검색 스킵
    """
    if state.need_search:
        return "search"  # Tavily 검색
    else:
        return "analysis"  # 바로 분석

def check_analyst(state: ResearchState):
    """분석 필요 여부 확인"""
    if state.is_analysis_need == True:
        return "analysis"
    else:
        return END


# Research 그래프 정의 (KG 통합)
research_graph = StateGraph(ResearchState)

# 노드 추가
research_graph.add_node("query_gen", generate_queries)
research_graph.add_node("kg_query", kg_query_node)           # ← KG 조회
research_graph.add_node("search", search_with_tavily)
research_graph.add_node("kg_save", kg_extract_and_save_node) # ← KG 저장
research_graph.add_node("analysis", analysis_search_results)

# 엣지 설정
research_graph.set_entry_point("query_gen")
research_graph.add_edge("query_gen", "kg_query")      # 쿼리 생성 → KG 조회
research_graph.add_conditional_edges(
    "kg_query",
    check_need_search,
    {
        "search": "search",      # 검색 필요 → Tavily 호출
        "analysis": "analysis"   # 충분함 → 바로 분석
    }
)
research_graph.add_edge("search", "kg_save")          # 검색 → KG 저장
research_graph.add_conditional_edges(
    "kg_save",
    check_analyst,
    {"analysis": "analysis", END: END}
)
research_graph.add_edge("analysis", END)

# 컴파일
research_subgraph = research_graph.compile()


if __name__ == '__main__':
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # 테스트 실행
    inputs = {"question": "게임 시스템 개선을 위한 기획서 양식이 필요해."}
    config = {"configurable": {"thread_id": "1"}}
    
    print("\n" + "="*60)
    print("Research 파이프라인 테스트 (KG 통합)")
    print("="*60)
    
    output = research_subgraph.invoke(inputs, config)
    
    print("\n" + "="*60)
    print("최종 결과")
    print("="*60)
    print(f"\n[질문] {output['question']}")
    
    kg_summary = output.get('kg_extraction_summary', '검색 스킵됨')
    print(f"\n[KG 추출] {kg_summary}")
    
    kg_cached = output.get('kg_cached_info', '')
    if kg_cached:
        print(f"\n[KG 캐시] {kg_cached[:200]}...")
    else:
        print(f"\n[KG 캐시] 없음")
    
    print(f"\n[분석 결과 (처음 500자)]")
    print(output['analysis_result'][:500])
    
    if output.get('analysis_file_path'):
        print(f"\n📄 전체 결과 파일: {output['analysis_file_path']}")