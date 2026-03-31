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


# =====================================================
# [Plan Agent 연동용] Research 서브그래프 실행 래퍼
# 
# 사용 시점:
#   - Supervisor가 RUN_RESEARCH로 라우팅했을 때 호출
#   - Plan Agent의 generate_section_node()에서 needs_research=True로 설정된 후
#
# 입력:
#   - state['research']['queries']: Plan Agent가 요청한 검색 쿼리 목록
#   - state['research']['section_context']: 리서치 대상 섹션 제목
#
# 출력:
#   - state['research']['gathered_evidence']: 수집된 검색 결과 리스트
#   - state['research']['analysis_result']: 분석 결과 텍스트
#   - state['research']['needs_research']: False로 설정
# =====================================================
def run_research_for_plan(state: dict) -> dict:
    """
    GlobalState를 받아서 Research 서브그래프를 실행하고,
    결과를 state['research']에 저장하여 반환
    """
    research_info = state.get('research', {})
    queries = research_info.get('queries', [])
    section_context = research_info.get('section_context', '')
    
    if not queries and not section_context:
        # 쿼리와 컨텍스트 모두 없으면 리서치 완료로 처리
        state['research'] = {
            **research_info,
            'needs_research': False,
            'evidence_store': [],
            'analysis_result': ''
        }
        return state
    
    # ResearchState 형태로 변환하여 서브그래프 실행
    # - question: 섹션 컨텍스트 (분석 시 참고) -> [Improvement] 쿼리에 리서치 목표가 있으면 그것을 질문으로 사용
    # - search_queries: Plan Agent가 제안한 쿼리들
    # - is_analysis_need: True (분석 결과도 필요)
    
    research_question = section_context
    if queries and len(queries) > 0:
        # nodes.py에서 첫 번째 쿼리로 Research Goal을 전달했으므로 이를 질문으로 활용
        research_question = queries[0]
        
    research_input = {
        "question": research_question,
        "search_queries": queries,
        "is_analysis_need": True
    }
    
    try:
        result = research_subgraph.invoke(research_input)
        
        # 검색 결과에서 content 추출
        search_results = result.get('search_results', [])
        evidence_list = []
        for item in search_results:
            # item is SearchItem (object) or dict
            if isinstance(item, dict):
                title = item.get('title', 'No Title')
                url = item.get('url', '')
                content = item.get('content', '')
                score = item.get('score', 0.0)
            else:
                title = getattr(item, 'title', 'No Title')
                url = getattr(item, 'url', '')
                content = getattr(item, 'content', '')
                score = getattr(item, 'score', 0.0)
            
            evidence_list.append({
                "title": title,
                "url": url,
                "content": content,
                "score": score
            })
        
        # [Fix] 스코어 기준 내림차순 정렬 (상위 결과 우선)
        evidence_list.sort(key=lambda x: x['score'], reverse=True)
        
        # 분석 결과 추출
        analysis = result.get('analysis_result', '')
        if hasattr(analysis, 'content'):
            analysis = analysis.content
        
        # GlobalState.research에 저장
        state['research'] = {
            **research_info,
            'needs_research': False,
            'evidence_store': evidence_list,
            'analysis_result': analysis
        }
    except Exception as e:
        # 에러 발생 시에도 needs_research=False로 설정하여 무한루프 방지
        print(f"[Research Error] {str(e)}")
        state['research'] = {
            **research_info,
            'needs_research': False,
            'evidence_store': [],
            'analysis_result': f'리서치 실행 중 오류 발생: {str(e)}'
        }
    
    return state


if __name__ == '__main__':
    from dotenv import load_dotenv
    
    load_dotenv()

    inputs = {"question": "게임 내 신규 유저 지원 시스템을 위한 기획서 양식이 필요해."}
    config = {"configurable": {"thread_id": "1"}}

    # output = research_subgraph.invoke(inputs, config)_subgraph.invoke(inputs, config)
    output = research_subgraph.invoke(inputs, config)