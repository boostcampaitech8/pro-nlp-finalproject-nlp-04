"""
Knowledge Graph 모듈

하위 모듈:
    - config: 설정 및 상수
    - ner: SpaCy NER
    - extraction: LLM OpenIE
    - core: KnowledgeGraphStore
    - tools: Tool API
    - nodes: LangGraph 노드
"""

from .extraction import extract_triplets_from_text
from .tools import (
    kg_search_text,
    kg_get_entity,
    kg_add_triplets,
    kg_find_related,
    save_kg,
    load_kg,
    get_kg_stats
)
from .nodes import (
    kg_query_node,
    kg_extract_and_save_node,
    KGToolWrapper
)
from .core import KnowledgeGraphStore

__all__ = [
    # Extraction
    "extract_triplets_from_text",
    
    # Tools
    "kg_search_text",
    "kg_get_entity",
    "kg_add_triplets",
    "kg_find_related",
    "save_kg",
    "load_kg",
    "get_kg_stats",
    
    # Nodes
    "kg_query_node",
    "kg_extract_and_save_node",
    "KGToolWrapper",
    
    # Core
    "KnowledgeGraphStore",
]

__version__ = "1.0.0"