"""
Knowledge Graph 모듈

역할:
    1. Tavily 검색 결과로부터 Relationship Extraction (RE) 수행
    2. 추출된 트리플을 바탕으로 NetworkX 기반 KG 구축 및 증강
    3. LangGraph Tool로 다른 Agent에서 KG 조회 가능

사용법:
    from kg import kg_get_entity, kg_search_text, kg_add_triplets
"""

from .kg_module import (
    # KG 조회 함수 (LangGraph Tool용)
    kg_get_entity,
    kg_find_related,
    kg_search_text,
    
    # KG 구축 함수
    kg_add_triplets,
    extract_triplets_from_text,
    
    # KG 관리 함수
    save_kg,
    load_kg,
    get_kg_stats,
    
    # 고급 사용
    KnowledgeGraphStore,
)

from .kg_nodes import (
    # LangGraph 노드
    kg_query_node,
    kg_extract_and_save_node,
    
    # Tool 래퍼
    KGToolWrapper,
)

__all__ = [
    # 조회 함수
    "kg_get_entity",
    "kg_find_related", 
    "kg_search_text",
    
    # 구축 함수
    "kg_add_triplets",
    "extract_triplets_from_text",
    
    # 관리 함수
    "save_kg",
    "load_kg",
    "get_kg_stats",
    
    # 노드
    "kg_query_node",
    "kg_extract_and_save_node",
    
    # 고급
    "KnowledgeGraphStore",
    "KGToolWrapper",
]

__version__ = "1.0.0"