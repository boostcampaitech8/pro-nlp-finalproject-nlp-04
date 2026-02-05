
"""
Supervisor가 직접 사용할 수 있는 KG Tool
"""

from langchain.tools import Tool
from kg import kg_search_text, kg_get_entity, kg_find_related


def kg_search_tool(query: str) -> str:
    """
    엔티티 검색 Tool
    
    Args:
        query: 검색 쿼리
    
    Returns:
        검색 결과 문자열
    """
    entities = kg_search_text(query, top_k=10)
    
    if not entities:
        return f"'{query}'와 관련된 엔티티를 찾을 수 없습니다."
    
    result = f"'{query}' 검색 결과 ({len(entities)}개):\n"
    for i, entity in enumerate(entities, 1):
        result += f"{i}. {entity}\n"
    
    return result


def kg_get_entity_tool(entity_name: str, max_hops: int = 1) -> str:
    """
    엔티티 정보 조회 Tool
    
    Args:
        entity_name: 엔티티 이름
        max_hops: 최대 탐색 거리
    
    Returns:
        엔티티 정보 문자열 (관계 목록)
    """
    info = kg_get_entity(entity_name, max_hops=max_hops)
    
    if not info:
        return f"'{entity_name}' 엔티티를 찾을 수 없습니다."
    
    result = f"'{entity_name}' 정보 ({len(info)}개 관계):\n\n"
    
    for i, r in enumerate(info[:20], 1):  # 최대 20개
        result += f"{i}. {r['subject']} → [{r['relation']}] → {r['object']}\n"
        result += f"   (신뢰도: {r['confidence']:.2f}, 출처: {r['source_url'][:50]}...)\n\n"
    
    if len(info) > 20:
        result += f"... 외 {len(info) - 20}개"
    
    return result


def kg_find_path_tool(entity_a: str, entity_b: str) -> str:
    """
    두 엔티티 간 경로 찾기 Tool
    
    Args:
        entity_a: 시작 엔티티
        entity_b: 종료 엔티티
    
    Returns:
        경로 문자열
    """
    path = kg_find_related(entity_a, entity_b, max_length=4)
    
    if not path:
        return f"'{entity_a}'와 '{entity_b}' 사이의 경로를 찾을 수 없습니다."
    
    result = f"'{entity_a}' → '{entity_b}' 경로:\n\n"
    
    for i, (subj, rel, obj) in enumerate(path, 1):
        result += f"{i}. {subj} → [{rel}] → {obj}\n"
    
    return result


# LangChain Tool로 래핑
kg_search_langchain_tool = Tool(
    name="kg_search",
    func=kg_search_tool,
    description="""Knowledge Graph에서 엔티티를 검색합니다.
    
    입력: 검색 쿼리 (예: "게임기획서", "OpenAI")
    출력: 매칭된 엔티티 목록
    
    사용 시기: 
    - 특정 주제와 관련된 엔티티를 찾고 싶을 때
    - KG에 어떤 정보가 있는지 탐색할 때
    """
)

kg_get_entity_langchain_tool = Tool(
    name="kg_get_entity",
    func=kg_get_entity_tool,
    description="""Knowledge Graph에서 특정 엔티티의 정보를 조회합니다.
    
    입력: 엔티티 이름 (예: "게임기획서")
    출력: 엔티티와 관련된 모든 관계 (트리플)
    
    사용 시기:
    - 엔티티의 상세 정보를 알고 싶을 때
    - 엔티티가 어떤 다른 엔티티와 연결되어 있는지 확인할 때
    """
)

kg_find_path_langchain_tool = Tool(
    name="kg_find_path",
    func=kg_find_path_tool,
    description="""Knowledge Graph에서 두 엔티티 간의 연결 경로를 찾습니다.
    
    입력: "엔티티A,엔티티B" (쉼표로 구분)
    출력: 두 엔티티를 연결하는 관계 경로
    
    사용 시기:
    - 두 개념 사이의 연관성을 파악하고 싶을 때
    - 엔티티 간 관계를 추적하고 싶을 때
    """
)


# Supervisor가 사용할 Tool 리스트
KG_TOOLS = [
    kg_search_langchain_tool,
    kg_get_entity_langchain_tool,
    kg_find_path_langchain_tool
]