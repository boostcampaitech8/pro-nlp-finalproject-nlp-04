from state.base import GlobalState
from state.research import ResearchState, SearchQueries, SearchItem
from langchain_core.prompts import ChatPromptTemplate
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_upstage import ChatUpstage
from langchain_tavily import TavilySearch
from config.config import API_KEY, TAVILY_API_KEY

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
    
    llm = ChatUpstage(model=MODEL_NAME_PRO, temperature=0.1, api_key=API_KEY)
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
        search_depth="advanced",
        tavily_api_key=TAVILY_API_KEY
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
    Docstring for analysis_search_results
    
    :param state: Description
    :type state: ResearchState
    """
    question = state.question
    search_results = state.search_results
    print(f"\n--- [Node: Search Results Analyst] 분석 중: {question} ---")

    summary = ""
    results_top5 = sorted(search_results, key=lambda x: x.score)[-5:]
    for result in results_top5:
        summary += f"### {result.title}\n\n{result.content}\n\n\n"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 분석 전문가입니다.
        주어진 사용자의 질문 또는 요청을 바탕으로 검색 결과를 분석하여
        질문 또는 요청에 대해 적절한 참고용 분석 자료를 작성하세요."""),
        ("human", "{question}"),
        ("human", "## 검색 결과\n{summary}")
    ])

    llm = ChatUpstage(model=MODEL_NAME_PRO, temperature=0.1, api_key=API_KEY)

    query_chain = prompt | llm
    analysis_result = query_chain.invoke({"question": question, "summary": summary})

    return {"analysis_result": analysis_result}