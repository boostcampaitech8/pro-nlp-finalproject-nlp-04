from typing import List
from pydantic import BaseModel, Field

class SearchQueries(BaseModel):
    queries: List[str] = Field(
        default_factory=list,
        description="검색 엔진용으로 최적화된 3~6개의 검색 쿼리 리스트"
    )

class SearchItem(BaseModel):
    title: str = Field(description="검색 결과의 제목")
    url: str = Field(description="원본 웹페이지 링크")
    content: str = Field(description="검색 결과의 주요 내용")
    score: float = Field(description="쿼리와 검색 결과의 유사도 점수")

class StructuredSearchOutput(BaseModel):
    query: str
    results: List[SearchItem]

class KGTriple(BaseModel):
    """KG에서 조회한 트리플"""
    subject: str
    relation: str
    object: str
    confidence: float
    source_url: str = ""
    domain: str = "general"


class KGQueryResult(BaseModel):
    """KG 조회 결과 전체"""
    queried_entities: List[str] = Field(
        default_factory=list,
        description="조회한 엔티티 목록"
    )
    found_triplets: List[KGTriple] = Field(
        default_factory=list,
        description="발견된 트리플 목록"
    )
    summary_text: str = Field(
        default="",
        description="사람이 읽을 수 있는 요약"
    )

class ResearchState(BaseModel):
    """
    Research 파이프라인 상태
    
    KG 통합 필드:
        - kg_cached_info: 검색 전 KG 조회 결과 (캐시)
    """
    
    # 기존 필드
    is_analysis_need: bool = Field(default=True)
    question: str = Field(default="")
    search_queries: List[str] = Field(default_factory=list)
    search_results: List[SearchItem] = Field(default_factory=list)
    analysis_result: str = Field(default="")
    
    # KG 관련 필드 (추가)
    kg_query_result: KGQueryResult = Field(
        default_factory=KGQueryResult,
        description="구조화된 KG 조회 결과"
    )
    kg_cached_info: str = Field(
        default="",
        description="(Deprecated) 하위 호환용"
    )

    need_search: bool = Field(
        default=True,
        description="Tavily 검색이 필요한지 여부 (KG 정보가 충분하면 False)"
    )