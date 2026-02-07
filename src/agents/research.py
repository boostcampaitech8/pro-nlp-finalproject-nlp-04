from state.base import GlobalState
from state.research import ResearchState, SearchQueries, SearchItem
from langchain_core.prompts import ChatPromptTemplate
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_upstage import ChatUpstage
from langchain_tavily import TavilySearch
from config.config import API_KEY
from kg import kg_query_node, kg_extract_and_save_node

# MODEL_NAME = "gemini-3-pro-preview"
MODEL_NAME_PRO = "solar-pro2"
MODEL_NAME_MINI = "solar-mini"

def research_generate(state: GlobalState) -> GlobalState:
    # 생성
    return state

def research_evaluate(state: GlobalState) -> GlobalState:
    # 평가
    return state

def research_eval_router(state: GlobalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"

def generate_queries(state: ResearchState):
    """
    Pydantic과 Structured Output을 사용하여 구조화된 검색 쿼리를 생성.
    """
    question = state.question
    print(f"\n--- [Node: Query Generator] 분석 중: {question} ---")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 검색 전문가입니다. 사용자의 질문을 분석하여 
        가장 정확하고 전문적인 검색 결과를 얻을 수 있는 다각도의 검색 쿼리를 생성하세요.
        결과는 영어 및 한국어 각각 3개 내외로 작성하세요."""),
        ("human", "{question}")
    ])
    
    llm = ChatUpstage(model=MODEL_NAME_MINI, temperature=0.1, api_key=API_KEY)
    structured_llm = llm.with_structured_output(SearchQueries)
    
    query_chain = prompt | structured_llm
    result = query_chain.invoke({"question": question})
    
    return {"search_queries": result.queries}

def search_with_tavily(state: ResearchState):
    """
    Docstring for search_with_tavily
    
    :param state: Description
    :type state: ResearchState
    """
    queries = state.search_queries
    search = TavilySearch(
        max_results=3,
        search_depth="advanced"
    )
    search_results = []

    for query in queries:
        output = search.invoke({"query": query})
        for res in output["results"]:
            item = SearchItem(
                title=res.get("title", "No Title"),
                url=res.get("url", ""),
                content=res.get("content", ""),
                score=res.get("score", 0.0)
            )
            search_results.append(item)

    # final_output = StructuredSearchOutput(
    #     query=query,
    #     results=search_results
    # )

    return {"search_results": search_results}

def analysis_search_results(state: ResearchState):
    """
    분석 노드
    
    개선사항:
        1. KG 사용 여부 명시
        2. 개선된 시스템 프롬프트
        3. 파일 저장 시 명확한 출처 표시
        4. 구조화된 분석 결과
    """
    from pathlib import Path
    from datetime import datetime
    
    question = state.question
    search_results = state.search_results
    kg_result = state.kg_query_result
    
    print(f"\n--- [Node: Search Results Analyst] 분석 중: {question} ---")
    
    # ============================================================================
    # 1. KG 정보 포맷팅 (사용 여부 추적)
    # ============================================================================
    
    kg_context = ""
    kg_used = False  # ★ KG 사용 여부 플래그
    
    if kg_result.found_triplets:
        kg_used = True
        kg_context = f"""## Knowledge Graph에서 조회된 기존 정보

**조회한 엔티티**: {', '.join(kg_result.queried_entities[:10])}

**발견된 관계** ({len(kg_result.found_triplets)}개):

"""
        for t in kg_result.found_triplets[:15]:  # 최대 15개
            kg_context += f"- {t.subject} → [{t.relation}] → {t.object}\n"
            kg_context += f"  (신뢰도: {t.confidence:.2f}, 출처: {t.source_url[:60]}...)\n"
        
        if len(kg_result.found_triplets) > 15:
            kg_context += f"\n... 외 {len(kg_result.found_triplets) - 15}개\n"
        
        kg_context += "\n"
        
        print(f"   ✅ KG 정보 활용: {len(kg_result.found_triplets)}개 트리플")
    else:
        print(f"   ℹ️  KG 정보 없음 (첫 실행 또는 관련 정보 부족)")
    
    # ============================================================================
    # 2. 검색 결과 포맷팅
    # ============================================================================
    
    search_summary = ""
    search_used = False
    
    if search_results:
        search_used = True
        # 상위 5개 선택 (점수 기준)
        results_top5 = sorted(search_results, key=lambda x: x.score, reverse=True)[:5]
        
        search_summary = "\n## 새로운 검색 결과\n\n"
        for idx, result in enumerate(results_top5, 1):
            search_summary += f"### {idx}. {result.title}\n\n"
            search_summary += f"**출처**: {result.url}\n\n"
            search_summary += f"{result.content}\n\n"
            search_summary += f"---\n\n"
        
        print(f"   ✅ 검색 결과 활용: {len(results_top5)}개")
    else:
        print(f"   ℹ️  검색 결과 없음 (검색 스킵됨)")
    
    # ============================================================================
    # 3. 통합 컨텍스트 생성
    # ============================================================================
    
    if kg_context and search_summary:
        full_context = kg_context + search_summary
    elif kg_context:
        full_context = kg_context
    elif search_summary:
        full_context = search_summary
    else:
        full_context = "(사용 가능한 정보가 없습니다.)"
    
    # ============================================================================
    # 4. 개선된 시스템 프롬프트
    # ============================================================================
    
    system_prompt = """당신은 전문 리서치 분석가입니다.

**역할**: 사용자의 질문에 대해 종합적이고 구조화된 분석 자료를 작성합니다.

**분석 원칙**:
1. **정확성**: 제공된 정보만을 기반으로 작성하며, 추측하지 않습니다.
2. **구조화**: 명확한 섹션 구분과 계층 구조를 사용합니다.
3. **실용성**: 사용자가 즉시 활용할 수 있는 구체적인 정보를 제공합니다.
4. **출처 명시**: 정보의 출처(KG 또는 검색 결과)를 명확히 표시합니다.

**출력 형식**:
```markdown
## 핵심 요약
[질문에 대한 직접적인 답변을 3-5줄로 요약]

## 주요 내용

### 1. [첫 번째 주요 포인트]
- 구체적인 세부사항
- 예시 또는 사례

### 2. [두 번째 주요 포인트]
- 구체적인 세부사항
- 예시 또는 사례

### 3. [추가 포인트...]

## 실무 적용 방안
[사용자가 실제로 어떻게 활용할 수 있는지 구체적으로 제시]

## 추가 고려사항
[관련 정보, 주의사항, 참고 사항등 구체적으로 제시]
```

**Knowledge Graph(KG) 정보 활용 시**:
- KG 정보는 **(KG 출처)** 태그를 붙여 표시하세요.
  예: "게임 기획서는 시스템 디자인의 일부입니다 (KG 출처)."
- KG 정보와 새 검색 결과가 상충되면 둘 다 제시하고 비교하세요.
  예: "기존 KG에 따르면 A입니다 (KG 출처). 그러나 최신 검색 결과는 B를 보고합니다."

**품질 기준**:
- 최소 800자 이상 작성
- 구체적인 예시 또는 사례 포함
- 실무에서 바로 적용 가능한 수준의 상세함
- 불필요한 반복 없이 간결하게
- 각 섹션은 명확한 주제를 가지고 있어야 함

질문에 정확하고 실용적으로 답변하세요."""

    # ============================================================================
    # 5. LLM 분석
    # ============================================================================
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "## 사용자 질문\n\n{question}"),
        ("human", "## 참고 정보\n\n{context}")
    ])
    
    llm = ChatUpstage(model=MODEL_NAME_PRO, temperature=0.1, api_key=API_KEY)
    query_chain = prompt | llm
    
    analysis_result = query_chain.invoke({
        "question": question,
        "context": full_context
    })

    # # 6. 분석 결과 파일 저장 (KG 활용 추적 포함)
    
    # output_dir = Path(__file__).parent.parent.parent / "data" / "analysis_results"
    # output_dir.mkdir(parents=True, exist_ok=True)
    
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # safe_question = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in question[:30])
    # filename = f"{timestamp}_{safe_question}.md"
    # filepath = output_dir / filename
    
    # with open(filepath, 'w', encoding='utf-8') as f:
    #     # 헤더
    #     f.write(f"# 분석 결과 보고서\n\n")
    #     f.write(f"**질문**: {question}\n\n")
    #     f.write(f"**생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
    #     # ★★★ 정보 출처 명시 ★★★
    #     f.write(f"**정보 출처**: ")
    #     sources = []
    #     if kg_used:
    #         sources.append(f"Knowledge Graph ({len(kg_result.found_triplets)}개 트리플)")
    #     if search_used:
    #         sources.append(f"Tavily 검색 ({len(search_results)}개 결과)")
        
    #     if sources:
    #         f.write(" + ".join(sources) + "\n\n")
    #     else:
    #         f.write("정보 없음\n\n")
        
    #     f.write(f"---\n\n")
        
    #     # ============================================================================
    #     # KG 활용 현황 섹션
    #     # ============================================================================
        
    #     f.write(f"## 📊 Knowledge Graph 활용 현황\n\n")
        
    #     if kg_used:
    #         f.write(f"### 조회된 엔티티 ({len(kg_result.queried_entities)}개)\n\n")
    #         f.write(f"{', '.join(kg_result.queried_entities[:20])}\n\n")
            
    #         if len(kg_result.queried_entities) > 20:
    #             f.write(f"... 외 {len(kg_result.queried_entities) - 20}개\n\n")
            
    #         f.write(f"### 발견된 지식 ({len(kg_result.found_triplets)}개 트리플)\n\n")
    #         f.write(f"| 주체 | 관계 | 객체 | 신뢰도 | 출처 |\n")
    #         f.write(f"|------|------|------|--------|------|\n")
            
    #         for t in kg_result.found_triplets[:20]:
    #             if getattr(t, "source_url", None):
    #                 source = t.source_url
    #                 # 텍스트로 보여줄 짧은 레이블: 도메인 우선, 없으면 앞부분 자르기
    #                 try:
    #                     domain_label = source.split('/')[2]
    #                 except Exception:
    #                     domain_label = source if len(source) <= 60 else source[:60] + "..."
    #                 source_md = f"[{domain_label}]({source})"
    #             else:
    #                 source_md = "-"

    #             subj_text = (t.subject[:50] + '...') if len(t.subject) > 50 else t.subject
    #             obj_text = (t.object[:50] + '...') if len(t.object) > 50 else t.object

                
    #             f.write(f"| {subj_text} | {t.relation} | {obj_text} | {t.confidence:.2f} | {source_md} |\n")
            
    #         if len(kg_result.found_triplets) > 20:
    #             f.write(f"\n... 외 {len(kg_result.found_triplets) - 20}개\n\n")
            
    #         f.write(f"\n**✅ KG 활용도**: 분석에 {len(kg_result.found_triplets)}개의 기존 지식이 사용되었습니다.\n\n")
    #     else:
    #         f.write(f"**KG 정보 없음**: 이번 분석은 새로운 검색 결과만을 기반으로 합니다.\n\n")
            
    #         if search_used:
    #             f.write(f"(검색 결과가 KG에 저장되어 다음 실행 시 활용 가능합니다.)\n\n")
        
    #     f.write(f"---\n\n")
        
    #     # ============================================================================
    #     # 검색 결과 요약 섹션
    #     # ============================================================================
        
    #     if search_used:
    #         f.write(f"## 🔍 검색 결과 요약\n\n")
    #         f.write(f"총 {len(search_results)}개의 검색 결과 중 상위 5개를 분석에 사용했습니다.\n\n")
            
    #         results_top5 = sorted(search_results, key=lambda x: x.score, reverse=True)[:5]
    #         for idx, r in enumerate(results_top5, 1):
    #             f.write(f"{idx}. **{r.title}** (점수: {r.score:.2f})\n")
    #             f.write(f"   - URL: {r.url}\n\n")
            
    #         f.write(f"---\n\n")
        
    #     # ============================================================================
    #     # 분석 내용
    #     # ============================================================================
        
    #     f.write(f"## 📝 분석 내용\n\n")
    #     f.write(analysis_result.content)
        
    #     # ============================================================================
    #     # 메타데이터 푸터
    #     # ============================================================================
        
    #     f.write(f"\n\n---\n\n")
    #     f.write(f"## 📋 메타데이터\n\n")
    #     f.write(f"- **KG 트리플 사용**: {len(kg_result.found_triplets)}개\n")
    #     f.write(f"- **검색 결과 사용**: {len(search_results) if search_used else 0}개\n")
    #     f.write(f"- **생성 모델**: {MODEL_NAME_PRO}\n")
    #     f.write(f"- **생성 시각**: {datetime.now().isoformat()}\n")
    
    # # ============================================================================
    # # 터미널 출력
    # # ============================================================================
    
    # print(f"\n✅ 분석 결과 저장: {filepath}")
    
    # if kg_used and search_used:
    #     print(f"   정보 출처: KG ({len(kg_result.found_triplets)}개) + Tavily ({len(search_results)}개)")
    # elif kg_used:
    #     print(f"   정보 출처: KG만 ({len(kg_result.found_triplets)}개 트리플)")
    # elif search_used:
    #     print(f"   정보 출처: Tavily만 ({len(search_results)}개 결과)")
    # else:
    #     print(f"   정보 출처: 없음")
    
    # ============================================================================
    # 7. 반환 (State 업데이트)
    # ============================================================================
    
    return {
        "analysis_result": analysis_result.content
    }


__all__ = [
    "research_generate",
    "research_evaluate",
    "research_eval_router",
    "generate_queries",
    "search_with_tavily",
    "analysis_search_results",
    "kg_query_node",              # ← KG 노드
    "kg_extract_and_save_node",   # ← KG 노드
]