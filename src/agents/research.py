import os
import uuid
import hashlib
from datetime import datetime

from state.base import GlobalState
from state.research import ResearchState, SearchQueries, SearchItem, ExtractedItem
from prompts.research_prompts import RESEARCH_ANALYSIS_PROMPT, RESEARCH_QUERY_GEN_PROMPT
from langchain_core.prompts import ChatPromptTemplate
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_upstage import ChatUpstage, UpstageEmbeddings
from langchain_tavily import TavilySearch
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchResults
from config.config import UPSTAGE_API_KEY
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import PointStruct, Document

# MODEL_NAME = "gemini-3-pro-preview"
MODEL_NAME_PRO = "solar-pro2"
MODEL_NAME_MINI = "solar-mini"
COLLECTION_NAME = "open-web-pages"
STALE_DAYS = 7

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if QDRANT_URL and QDRANT_API_KEY:
    qdrant_client = QdrantClient(
        url=QDRANT_URL, 
        api_key=QDRANT_API_KEY,
    )
else:
    qdrant_client = QdrantClient(path="./qdrant_data")

if not qdrant_client.collection_exists(COLLECTION_NAME):
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "text-dense": models.VectorParams(
                size=4096,
                distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "text-sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(on_disk=False)
            )
        }
    )
    print(f"Qdrant '{COLLECTION_NAME}' 콜렉션이 생성되었습니다.")
else:
    print(f"Qdrant '{COLLECTION_NAME}' 콜렉션이 이미 존재합니다.")

qdrant_client.create_payload_index(
    COLLECTION_NAME,
    field_name="url",
    field_schema="keyword",
)

def research_generate(state: GlobalState) -> GlobalState:
    # 생성
    return state

def research_evaluate(state: GlobalState) -> GlobalState:
    # 평가
    return state

def research_eval_router(state: GlobalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"

from datetime import datetime, timezone

def check_db_freshness(client: QdrantClient, collection_name: str, url: str, stale_days: int = 7):
    try:
        # 필터링을 사용하여 특정 URL 검색
        search_result, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="url", 
                        match=models.MatchValue(value=url),
                    ),
                ]
            ),
            limit=1,
            with_payload=True
        )

        if not search_result:
            return {"is_indexed": False, "is_stale": False}

        record = search_result[0]
        last_scraped_str = record.payload.get("last_scraped_at")
        
        if not last_scraped_str:
            return {"is_indexed": True, "is_stale": True} # 날짜 정보 없으면 업데이트 필요로 간주

        last_scraped_dt = datetime.fromisoformat(last_scraped_str)
        if last_scraped_dt.tzinfo is None:
            last_scraped_dt = last_scraped_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        
        is_stale = (now - last_scraped_dt).days >= stale_days
        return {"is_indexed": True, "is_stale": is_stale}

    except Exception as e:
        print(f"Error checking Qdrant: {e}")
        return {"is_indexed": False, "is_stale": False}

def generate_queries(state: ResearchState):
    """
    Pydantic과 Structured Output을 사용하여 구조화된 검색 쿼리를 생성.
    """
    question = state.question
    print(f"\n--- [Node: Query Generator] 분석 중: {question} ---")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", RESEARCH_QUERY_GEN_PROMPT),
        ("human", "{question}")
    ])
    
    llm = ChatUpstage(model=MODEL_NAME_PRO, temperature=0.1, api_key=UPSTAGE_API_KEY)
    structured_llm = llm.with_structured_output(SearchQueries)
    
    query_chain = prompt | structured_llm
    result = query_chain.invoke({"question": question})
    
    return {"search_queries": result.queries}

def search_with_tavily(state: ResearchState):
    queries = state.search_queries
    search = TavilySearch(
        max_results=5,
        search_depth="basic",
        include_raw_content=True
    )
    search_results = []

    for query in queries:
        output = search.invoke({"query": query})
        if isinstance(output, str):
            continue
        for res in output["results"]:
            url = res.get("url", "")
            db_status = check_db_freshness(qdrant_client, COLLECTION_NAME, url, STALE_DAYS)

            item = SearchItem(
                query=query,
                title=res.get("title", "No Title"),
                url=res.get("url", ""),
                snippet=res.get("content", ""),
                content=res.get("raw_content", res.get("content", "")),
                is_indexed=db_status["is_indexed"],
                is_stale=db_status["is_stale"],
            )
            search_results.append(item)

    return {"search_results": search_results}

def upsert_qdrant(state: ResearchState):
    target_results = [result for result in state.search_results if result.is_indexed == False]
    print(f"\n--- [Node: Upsert Qdrant] 신규 검색 결과 업로드 중: 총 {len(target_results)}건 ---")
    if len(target_results) == 0: return state

    passage_embeddings = UpstageEmbeddings(
        api_key=UPSTAGE_API_KEY,
        model="embedding-passage"
    )
    try:
        doc_results = passage_embeddings.embed_documents(
            [result.snippet for result in target_results]
        )
        qdrant_client.upsert(
            COLLECTION_NAME,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    payload={
                        "title": target_result.title,
                        "url": target_result.url,
                        "text_type": "snippet",
                        "content": target_result.snippet,
                        "page_hash": hashlib.sha256(target_result.snippet.encode('utf-8')).hexdigest(),
                        "last_scraped_at": datetime.now() if target_result.last_scraped_at is None else target_result.last_scraped_at
                    },
                    vector={
                        "text-dense": doc_results[idx],
                        "text-sparse": Document(
                            text=target_result.snippet,
                            model="qdrant/bm25"
                        )
                    }
                )
                for idx, target_result in enumerate(target_results)
            ]
        )
    except Exception as e:
        print(f"Failed: {e}")

    return state

def execute_hybrid_search(state: ResearchState):
    query_embeddings = UpstageEmbeddings(
        api_key=UPSTAGE_API_KEY,
        model="embedding-query"
    )
    query_embedding = query_embeddings.embed_documents(
        [state.question]
    )[0]
    
    queried_results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            # (1) Dense 벡터 검색 (Semantic)
            models.Prefetch(
                query=query_embedding,
                using="text-dense",
                limit=10,
            ),
            # (2) Sparse 벡터 검색 (Keyword)
            models.Prefetch(
                query=Document(
                    text=state.question,
                    model="qdrant/bm25"
                ),
                using="text-sparse",
                limit=10,
            ),
        ],
        # (3) 두 결과를 RRF로 통합
        query=models.FusionQuery(
            fusion=models.Fusion.RRF
        ),
        limit=5 # 최종 결과 개수
    )

    extracted_results = []
    for result in queried_results.points:
        payload = result.payload
        item = ExtractedItem(
            item_type=payload.get("text_type"),
            title=payload.get("title"),
            url=payload.get("url"),
            content=payload.get("content"),
            score=result.score
        )
        extracted_results.append(item)

    return {"search_results": extracted_results}

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
    # results_top5 = sorted(search_results, key=lambda x: x.score)[-5:]
    for result in search_results:
        summary += f"### <자료 제목> {result.title}\n\n<자료 내용>{result.content}\n\n\n"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", RESEARCH_ANALYSIS_PROMPT),
        ("human", "## 참고 자료(관련 검색 결과)\n{summary}"),
        ("human", "{question}"),
    ])

    llm = ChatUpstage(model=MODEL_NAME_PRO, temperature=0.1, api_key=UPSTAGE_API_KEY)

    query_chain = prompt | llm
    analysis_result = query_chain.invoke({"question": question, "summary": summary})

    return {"analysis_result": analysis_result.text}