"""
Knowledge Graph Tool API (Supervisor용)
"""
from typing import List, Dict, Optional, Tuple
from .core import KnowledgeGraphStore


def kg_get_entity(name: str, max_hops: int = 1, domain: Optional[str] = None) -> List[Dict]:
    kg = KnowledgeGraphStore()
    return kg.get_entity_info(name, max_hops, domain)


def kg_find_related(
    entity_a: str,
    entity_b: str,
    max_length: int = 4,
    domain: Optional[str] = None
) -> Optional[List[Tuple[str, str, str]]]:
    kg = KnowledgeGraphStore()
    return kg.find_path(entity_a, entity_b, max_length, domain)


def kg_search_text(query: str, top_k: int = 10) -> List[str]:
    kg = KnowledgeGraphStore()
    return kg.search_entities(query, top_k)


def kg_add_triplets(triplets: List[Dict], auto_save: bool = True) -> int:
    kg = KnowledgeGraphStore()
    
    for t in triplets:
        kg.add_triple(
            subject=t['subject'],
            relation=t['relation'],
            obj=t['object'],
            subject_type=t.get('subject_type', 'Concept'),
            object_type=t.get('object_type', 'Concept'),
            confidence=t.get('confidence', 1.0),
            source_url=t.get('source_url', ''),
            domain=t.get('domain', 'general'),
            crawl_time=t.get('crawl_time'),
            extractor_version=t.get('extractor_version')
        )
    
    if auto_save:
        kg.save()
    
    return len(triplets)


def get_kg_stats() -> Dict:
    return KnowledgeGraphStore().get_stats()


def save_kg():
    kg = KnowledgeGraphStore()
    kg.save()
    kg.export_to_sqlite()


def load_kg():
    KnowledgeGraphStore().load()