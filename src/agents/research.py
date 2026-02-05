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
    분석 노드 (KG 활용 추적)
    """
    from pathlib import Path
    
    question = state.question
    search_results = state.search_results
    kg_result = state.kg_query_result
    
    print(f"\n--- [Node: Search Results Analyst] 분석 중: {question} ---")
    
    # 상위 5개 검색 결과
    results_top5 = sorted(search_results, key=lambda x: x.score, reverse=True)[:5]
    
    search_summary = ""
    for result in results_top5:
        search_summary += f"### {result.title}\n\n{result.content}\n\n\n"
    
    # KG 정보를 구조화해서 프롬프트에 포함
    kg_context = ""
    if kg_result.found_triplets:
        kg_context = f"""## Knowledge Graph에서 조회된 기존 정보

**조회한 엔티티**: {', '.join(kg_result.queried_entities[:10])}

**발견된 관계** ({len(kg_result.found_triplets)}개):
"""
        for t in kg_result.found_triplets[:15]:
            kg_context += f"- {t.subject} → [{t.relation}] → {t.object}\n"
            kg_context += f"  (신뢰도: {t.confidence:.2f}, 출처: {t.source_url[:80]})\n"
        
        kg_context += "\n"
    
    full_context = (
        kg_context + f"\n## 새로운 검색 결과\n\n{search_summary}"
        if kg_context else search_summary
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 분석 전문가입니다.
        
        주어진 정보를 바탕으로 사용자의 질문에 대한 종합 분석 자료를 작성하세요.
        
        **중요**:
        1. Knowledge Graph(KG)에 이미 저장된 정보가 있다면 이를 **명시적으로 인용**하세요.
        2. KG 정보와 새 검색 결과를 **비교/대조**하세요.
        3. KG 정보를 활용한 부분에는 **(KG 출처)** 표시를 추가하세요.
        4. 완전하고 상세한 분석을 제공하세요."""),
        ("human", "{question}"),
        ("human", "{context}")
    ])
    
    llm = ChatUpstage(
        model=MODEL_NAME_PRO,
        temperature=0.1,
        api_key=API_KEY
    )
    
    analysis_result = (prompt | llm).invoke({
        "question": question,
        "context": full_context
    })
    
    # 결과 파일 저장
    output_dir = Path(__file__).parent.parent.parent / "data" / "analysis_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    safe_question = "".join(
        c if c.isalnum() or c in (' ', '_') else '_' for c in question[:30]
    ).strip().replace(" ", "_")
    
    filename = f"{safe_question}.md"
    filepath = output_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# 분석 결과 보고서\n\n")
        f.write(f"**질문**: {question}\n\n")
        f.write("---\n\n")
        
        # KG 활용 섹션
        f.write("## 📊 Knowledge Graph 활용 현황\n\n")
        if kg_result.found_triplets:
            f.write(f"### 조회된 엔티티 ({len(kg_result.queried_entities)}개)\n\n")
            f.write(", ".join(kg_result.queried_entities) + "\n\n")
            
            f.write(f"### 발견된 지식 ({len(kg_result.found_triplets)}개 트리플)\n\n")
            f.write("| 주체 | 관계 | 객체 | 신뢰도 | 출처 |\n")
            f.write("|------|------|------|--------|------|\n")
            for t in kg_result.found_triplets:
                source_short = (
                    t.source_url.split('/')[2]
                    if '/' in t.source_url else t.source_url[:20]
                )
                f.write(
                    f"| {t.subject} | {t.relation} | {t.object} | "
                    f"{t.confidence:.2f} | {source_short} |\n"
                )
            
            f.write(f"\n**KG 활용도**: {len(kg_result.found_triplets)}개 트리플 사용\n\n")
        else:
            f.write(
                "KG에서 관련 정보를 찾지 못했습니다. "
                "이번 분석은 새로운 검색 결과만을 기반으로 합니다.\n\n"
            )
        
        f.write("---\n\n")
        
        # 검색 결과 요약
        f.write("## 🔍 검색 결과 요약\n\n")
        f.write(
            f"총 {len(search_results)}개 중 "
            f"상위 {len(results_top5)}개 결과를 사용했습니다.\n\n"
        )
        for idx, r in enumerate(results_top5, 1):
            f.write(f"{idx}. **{r.title}** (점수: {r.score:.2f})\n")
            f.write(f"   - URL: {r.url}\n\n")
        
        f.write("---\n\n")
        
        # 분석 내용
        f.write("## 📝 분석 내용\n\n")
        f.write(analysis_result.content)
        
        # 메타데이터
        f.write("\n\n---\n\n")
        f.write("**메타데이터**:\n")
        f.write(f"- KG 트리플 사용: {len(kg_result.found_triplets)}개\n")
        f.write(f"- 검색 결과 사용: {len(results_top5)}개\n")
        f.write(f"- 생성 모델: {MODEL_NAME_PRO}\n")
    
    print(f"\n✅ 분석 결과 저장: {filepath}")
    print(f"   KG 활용: {len(kg_result.found_triplets)}개 트리플")
    print(f"   검색 활용: {len(results_top5)}개 결과")
    
    return {
        "analysis_result": analysis_result.content,
        "analysis_file_path": str(filepath)
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