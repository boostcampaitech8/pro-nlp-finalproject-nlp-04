"""
Knowledge Graph 핵심 저장소
"""
import pickle
import sqlite3
import networkx as nx
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .config import (
    KG_PICKLE_PATH,
    KG_SQLITE_PATH,
    RELATION_NORMALIZER,
    RELATION_TYPES,
    EXTRACTOR_VERSION
)


# ============================================================================
# KG 저장소 (NetworkX MultiDiGraph)
# ============================================================================

class KnowledgeGraphStore:
    """
    NetworkX 기반 지식 그래프 저장소 (싱글톤)
    
    핵심 역할:
        1. [KG 구축] 트리플을 NetworkX MultiDiGraph에 저장
        2. [증강] 기존 KG에 새 트리플 추가 (중복 방지)
        3. [조회] 엔티티 검색, 경로 찾기 등
    
    설계 원칙:
        - Global Core Ontology: 모든 엔티티/관계는 정의된 타입 사용
        - Domain-Specific: 각 트리플에 domain 태그로 네임스페이스 분리
        - Provenance: source_url, crawl_time, extractor_version 추적
    
    MultiDiGraph 사용 이유:
        - Multi: 같은 엔티티 쌍에 여러 관계 허용
          예: (삼성전자) -[produces]-> (Galaxy S24)
              (삼성전자) -[owns]-> (Galaxy S24)
        - Directed: 관계의 방향성 표현
    """
    
    _instance = None  # 싱글톤 패턴
    
    def __new__(cls):
        """싱글톤: 프로그램 전체에서 하나의 그래프만 유지"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """초기화: 기존 그래프 로드 또는 새로 생성"""
        if self._initialized:
            return
        
        self.graph = nx.MultiDiGraph()
        
        # 기존 그래프가 있으면 로드 (증강 모드)
        if KG_PICKLE_PATH.exists():
            self.load()
        
        self._initialized = True
    
    def normalize_relation(self, relation: str) -> str:
        """
        관계 정규화 (동의어 → 표준 관계)
        
        Global Core Ontology 유지를 위해 필수
        
        Args:
            relation: 원본 관계 (예: "근무", "employed_by")
        
        Returns:
            정규화된 관계 (예: "works_for")
        """
        return RELATION_NORMALIZER.get(relation, relation)
    
    def _edge_exists(self, subject: str, relation: str, obj: str) -> bool:
        """
        중복 엣지 확인
        
        같은 (subject, relation, object) 트리플이 이미 존재하는지 확인
        KG 증강 시 중복 방지
        """
        if not self.graph.has_edge(subject, obj):
            return False
        
        for _, edge_data in self.graph[subject][obj].items():
            if edge_data.get('relation') == relation:
                return True
        
        return False
    
    def add_triple(
        self,
        subject: str,
        relation: str,
        obj: str,
        subject_type: str = "Concept",
        object_type: str = "Concept",
        confidence: float = 1.0,
        source_url: str = "",
        domain: str = "general",
        crawl_time: str = None,
        extractor_version: str = None,
        **metadata
    ):
        """
        [핵심 1] KG 구축 및 증강
        
        트리플을 NetworkX 그래프에 추가하여 KG 구축/증강
        
        Domain-Specific Subgraph 구현:
            - 각 노드/엣지에 domain 태그 추가
            - 조회 시 domain 필터링 가능
            - 예: domain="tech", domain="finance", domain="research"
        
        Provenance 추적:
            - source_url: 원본 웹페이지 링크
            - crawl_time: 크롤링 시간
            - extractor_version: 추출기 버전
            - confidence: LLM 신뢰도
        
        Args:
            subject: 주체 엔티티
            relation: 관계 (자동 정규화됨)
            obj: 객체 엔티티
            subject_type: 주체 타입 (ENTITY_TYPES 중 하나)
            object_type: 객체 타입
            confidence: 신뢰도 (0.0~1.0)
            source_url: 출처 URL (Provenance)
            domain: 도메인 태그 (네임스페이스)
            crawl_time: 크롤링 시간 (ISO 8601)
            extractor_version: 추출기 버전
            **metadata: 추가 메타데이터
        
        Example:
            kg.add_triple(
                subject="OpenAI",
                relation="produces",
                obj="ChatGPT",
                subject_type="Organization",
                object_type="Product",
                confidence=0.98,
                source_url="https://openai.com",
                domain="tech"
            )
        """
        # 1. 관계 정규화 (Global Core Ontology 유지)
        relation = self.normalize_relation(relation)
        
        # 2. 중복 체크 (KG 증강 시 중복 방지)
        if self._edge_exists(subject, relation, obj):
            return
        
        # 3. 노드 추가 (엔티티)
        if not self.graph.has_node(subject):
            self.graph.add_node(
                subject,
                entity_type=subject_type,
                domains=set()  # 여러 도메인에 속할 수 있음
            )
        if not self.graph.has_node(obj):
            self.graph.add_node(
                obj,
                entity_type=object_type,
                domains=set()
            )
        
        # 4. 도메인 태그 추가 (Domain-Specific Subgraph)
        self.graph.nodes[subject]['domains'].add(domain)
        self.graph.nodes[obj]['domains'].add(domain)
        
        # 5. 엣지 추가 (관계) + Provenance
        self.graph.add_edge(
            subject, obj,
            relation=relation,
            confidence=confidence,
            source_url=source_url,
            domain=domain,
            crawl_time=crawl_time or datetime.now().isoformat(),
            extractor_version=extractor_version or EXTRACTOR_VERSION,
            timestamp=datetime.now().isoformat(),
            **metadata
        )
    
    def get_entity_info(
        self,
        name: str,
        max_hops: int = 1,
        domain: Optional[str] = None
    ) -> List[Dict]:
        """
        [핵심 3] LangGraph Tool - 엔티티 조회
        
        엔티티와 관련된 모든 트리플 조회
        다른 Agent에서 KG 정보를 활용할 때 사용
        
        Args:
            name: 엔티티 이름
            max_hops: 최대 탐색 거리 (1=직접 연결만, 2=2단계까지)
            domain: 도메인 필터 (None=전체, "tech"=기술 도메인만)
        
        Returns:
            트리플 리스트 [
                {
                    "subject": "...",
                    "relation": "...",
                    "object": "...",
                    "confidence": 0.95,
                    "source_url": "...",
                    "domain": "..."
                },
                ...
            ]
        
        Example:
            # "OpenAI"와 직접 연결된 모든 관계
            info = kg.get_entity_info("OpenAI", max_hops=1)
            
            # "tech" 도메인만 필터링
            info = kg.get_entity_info("OpenAI", domain="tech")
        """
        if not self.graph.has_node(name):
            return []
        
        results = []
        visited = set()
        
        def traverse(node, depth):
            """재귀적 그래프 탐색"""
            if depth > max_hops or node in visited:
                return
            visited.add(node)
            
            # 나가는 엣지 (주체 → 객체)
            for neighbor in self.graph.successors(node):
                for _, edge_data in self.graph[node][neighbor].items():
                    # 도메인 필터 적용
                    if domain is None or edge_data.get('domain') == domain:
                        results.append({
                            'subject': node,
                            'relation': edge_data['relation'],
                            'object': neighbor,
                            'confidence': edge_data['confidence'],
                            'source_url': edge_data.get('source_url', ''),
                            'domain': edge_data.get('domain', 'general'),
                        })
                
                if depth < max_hops:
                    traverse(neighbor, depth + 1)
            
            # 들어오는 엣지 (객체 ← 주체)
            for predecessor in self.graph.predecessors(node):
                for _, edge_data in self.graph[predecessor][node].items():
                    if domain is None or edge_data.get('domain') == domain:
                        results.append({
                            'subject': predecessor,
                            'relation': edge_data['relation'],
                            'object': node,
                            'confidence': edge_data['confidence'],
                            'source_url': edge_data.get('source_url', ''),
                            'domain': edge_data.get('domain', 'general'),
                        })
                
                if depth < max_hops:
                    traverse(predecessor, depth + 1)
        
        traverse(name, 0)
        return results
    
    def find_path(
        self,
        entity_a: str,
        entity_b: str,
        max_length: int = 4,
        domain: Optional[str] = None
    ) -> Optional[List[Tuple[str, str, str]]]:
        """
        [핵심 3] LangGraph Tool - 경로 찾기
        
        두 엔티티 간 최단 경로 찾기
        Agent가 엔티티 간 연관성을 파악할 때 사용
        
        Args:
            entity_a: 시작 엔티티
            entity_b: 종료 엔티티
            max_length: 최대 경로 길이
            domain: 도메인 필터
        
        Returns:
            경로 [(entity, relation, entity), ...] 또는 None
        
        Example:
            path = kg.find_path("OpenAI", "ChatGPT")
            # [("OpenAI", "produces", "ChatGPT")]
        """
        if not self.graph.has_node(entity_a) or not self.graph.has_node(entity_b):
            return None
        
        try:
            # 도메인 필터링된 서브그래프 생성
            if domain:
                edges = [
                    (u, v, k) for u, v, k, d in self.graph.edges(keys=True, data=True)
                    if d.get('domain') == domain
                ]
                subgraph = self.graph.edge_subgraph(edges)
            else:
                subgraph = self.graph
            
            # 최단 경로 찾기
            path = nx.shortest_path(subgraph, entity_a, entity_b)
            
            if len(path) - 1 > max_length:
                return None
            
            # 경로를 (엔티티, 관계, 엔티티) 형태로 변환
            result = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = list(subgraph[u][v].values())[0]
                result.append((u, edge_data['relation'], v))
            
            return result
        
        except nx.NetworkXNoPath:
            return None
    
    def search_entities(self, query: str, top_k: int = 10) -> List[str]:
        """
        [핵심 3] LangGraph Tool - 텍스트 검색
        
        엔티티 이름 부분 매칭 검색
        Agent가 사용자 쿼리에 맞는 엔티티를 찾을 때 사용
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
        
        Returns:
            매칭된 엔티티 이름 리스트
        
        Example:
            entities = kg.search_entities("OpenAI", top_k=5)
            # ["OpenAI", "OpenAI DevDay", ...]
        """
        query_lower = query.lower()
        matches = [
            node for node in self.graph.nodes()
            if query_lower in node.lower()
        ]
        return matches[:top_k]
    
    def get_stats(self) -> Dict:
        """그래프 통계"""
        num_nodes = self.graph.number_of_nodes()
        return {
            'num_entities': num_nodes,
            'num_relations': self.graph.number_of_edges(),
            'avg_degree': sum(dict(self.graph.degree()).values()) / max(num_nodes, 1) if num_nodes > 0 else 0,
        }
    
    def save(self):
        """그래프 저장 (pickle)"""
        with open(KG_PICKLE_PATH, 'wb') as f:
            pickle.dump(self.graph, f)
    
    def load(self):
        """그래프 로드 (증강 모드)"""
        if KG_PICKLE_PATH.exists():
            with open(KG_PICKLE_PATH, 'rb') as f:
                self.graph = pickle.load(f)
    
    def export_to_sqlite(self):
        """SQLite로 덤프 (백업/외부 도구 연동)"""
        conn = sqlite3.connect(KG_SQLITE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                name TEXT PRIMARY KEY,
                entity_type TEXT,
                domains TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                relation TEXT,
                object TEXT,
                confidence REAL,
                source_url TEXT,
                domain TEXT,
                crawl_time TEXT,
                extractor_version TEXT,
                timestamp TEXT,
                FOREIGN KEY (subject) REFERENCES entities(name),
                FOREIGN KEY (object) REFERENCES entities(name)
            )
        ''')
        
        cursor.execute('DELETE FROM entities')
        cursor.execute('DELETE FROM relations')
        
        for node, data in self.graph.nodes(data=True):
            cursor.execute(
                'INSERT OR REPLACE INTO entities VALUES (?, ?, ?)',
                (node, data.get('entity_type', 'Concept'),
                 ','.join(data.get('domains', set())))
            )
        
        for u, v, data in self.graph.edges(data=True):
            cursor.execute(
                '''INSERT INTO relations
                   (subject, relation, object, confidence, source_url, domain, crawl_time, extractor_version, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (u, data['relation'], v, data['confidence'],
                 data.get('source_url', ''), data.get('domain', 'general'),
                 data.get('crawl_time', ''), data.get('extractor_version', ''),
                 data.get('timestamp', ''))
            )
        
        conn.commit()
        conn.close()