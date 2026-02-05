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

class ResearchState(BaseModel):
    is_analysis_need: bool = Field(default=True)
    question: str = Field(default="")
    search_queries: List[str] = Field(default_factory=list)
    search_results: List[SearchItem] = Field(default_factory=list)
    analysis_result: str = Field(default="")