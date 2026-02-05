"""
Knowledge Graph 핵심 모듈

주요 책임:
    1. [RE] Relationship Extraction: LLM 기반 OpenIE로 트리플 추출
    2. [KG 구축] NetworkX MultiDiGraph로 KG 저장 및 증강
    3. [Tool] LangGraph Agent에서 사용 가능한 조회 API 제공

구조:
    - Global Core Ontology: 공통 엔티티/관계 타입 정의
    - Domain-Specific Subgraphs: domain 태그로 네임스페이스 분리
    - Provenance: source_url, crawl_time, extractor_version 추적
"""

import os
import json
import re
import pickle
import sqlite3
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
import networkx as nx

# ============================================================================
# 설정 로드
# ============================================================================

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent  # src/kg/ → project root
DATA_DIR = BASE_DIR / os.getenv("KG_DATA_DIR", "data")
DATA_DIR.mkdir(exist_ok=True)

# KG 저장 경로
KG_PICKLE_PATH = DATA_DIR / os.getenv("KG_PICKLE_FILE", "knowledge_graph.gpickle")
KG_SQLITE_PATH = DATA_DIR / os.getenv("KG_SQLITE_FILE", "knowledge_graph.db")

# Tavily 검색 결과 DB
TAVILY_DB_PATH = DATA_DIR / "tavily_results.db"

# LLM API 설정 (Upstage Solar Pro2)
SOLAR_API_KEY = os.getenv("SOLAR_PRO2_API_KEY", "") or os.getenv("API_KEY", "")
SOLAR_ENDPOINT = os.getenv("SOLAR_PRO2_ENDPOINT", "https://api.upstage.ai/v1/solar/chat/completions")

if not SOLAR_API_KEY:
    print("⚠️  경고: SOLAR_PRO2_API_KEY (또는 API_KEY)가 설정되지 않았습니다.")

# SpaCy 모델 (다국어 지원)
SPACY_MODEL_KO = os.getenv("SPACY_MODEL_KO", "ko_core_news_sm")
SPACY_MODEL_EN = os.getenv("SPACY_MODEL_EN", "en_core_web_sm")

# 추출 설정
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.5"))
EXTRACTOR_VERSION = os.getenv("EXTRACTOR_VERSION", "v1.0-prod")

# ============================================================================
# Global Core Ontology (공통 레이블/타입)
# ============================================================================

# 엔티티 타입 (전체 도메인에서 공통으로 사용)
ENTITY_TYPES = [
    "Person",         # 인물
    "Organization",   # 조직/회사
    "Location",       # 장소/지역
    "Product",        # 제품/서비스
    "Concept",        # 개념/아이디어
    "Event"           # 이벤트/사건
]

# 관계 타입 (전체 도메인에서 공통으로 사용)
RELATION_TYPES = [
    "works_for",      # ~에서 일한다
    "located_in",     # ~에 위치한다
    "produces",       # ~을 생산한다
    "owns",           # ~을 소유한다
    "related_to",     # ~와 관련있다 (fallback)
    "founded_by",     # ~에 의해 설립됨
    "acquires",       # ~을 인수한다
    "member_of",      # ~의 구성원이다
    "part_of",        # ~의 일부이다
    "causes"          # ~을 야기한다
]

# 관계 정규화 매퍼 (동의어 → 표준 관계)
# LLM이 다양한 표현으로 추출한 관계를 표준 관계로 매핑
RELATION_NORMALIZER = {
    # works_for
    "근무": "works_for", "소속": "works_for", "재직": "works_for",
    "일하다": "works_for", "employed_by": "works_for",
    
    # located_in
    "위치": "located_in", "본사": "located_in", "있다": "located_in",
    "based_in": "located_in", "headquarters": "located_in",
    
    # produces
    "생산": "produces", "제조": "produces", "출시": "produces",
    "개발": "produces", "만들다": "produces", "creates": "produces",
    
    # owns
    "소유": "owns", "보유": "owns", "owns": "owns",
    
    # founded_by
    "설립": "founded_by", "창립": "founded_by", "founded": "founded_by",
    
    # acquires
    "인수": "acquires", "매입": "acquires", "acquired": "acquires",
    
    # part_of
    "포함": "part_of", "구성": "part_of", "consists_of": "part_of",
    
    # member_of
    "회원": "member_of", "구성원": "member_of", "member": "member_of",
}

# ============================================================================
# SpaCy NER (다국어 지원)
# ============================================================================

_nlp_ko = None  # 한글 모델
_nlp_en = None  # 영어 모델


def _detect_language(text: str) -> str:
    """
    텍스트 언어 자동 감지 (간단한 휴리스틱)
    
    한글 문자 비율이 30% 이상이면 한글, 아니면 영어로 판단
    
    Args:
        text: 입력 텍스트
    
    Returns:
        "ko" 또는 "en"
    """
    korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
    total_chars = len(text)
    
    if total_chars == 0:
        return "en"
    
    korean_ratio = korean_chars / total_chars
    return "ko" if korean_ratio > 0.3 else "en"


def _get_spacy_nlp(lang: str = "auto"):
    """
    SpaCy 모델 로드 (다국어 지원)
    
    Args:
        lang: "auto" (자동 감지), "ko" (한글), "en" (영어)
    
    Returns:
        spacy.Language 객체 또는 None
    """
    global _nlp_ko, _nlp_en
    
    try:
        import spacy
        
        if lang == "ko" or lang == "auto":
            if _nlp_ko is None:
                _nlp_ko = spacy.load(SPACY_MODEL_KO)
            if lang == "ko":
                return _nlp_ko
        
        if lang == "en" or lang == "auto":
            if _nlp_en is None:
                _nlp_en = spacy.load(SPACY_MODEL_EN)
            if lang == "en":
                return _nlp_en
        
        # auto인 경우 둘 다 로드 시도 (한글 우선)
        return _nlp_ko if _nlp_ko else _nlp_en
    
    except Exception as e:
        print(f"⚠️  SpaCy 모델 로드 실패: {e}")
        print(f"   설치 명령: python -m spacy download {SPACY_MODEL_KO}")
        print(f"   설치 명령: python -m spacy download {SPACY_MODEL_EN}")
        return None


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


# ============================================================================
# Relationship Extraction (RE) - LLM 기반 OpenIE
# ============================================================================

def _extract_ner(text: str, lang: str = "auto") -> List[Dict]:
    """
    [핵심 1-1] SpaCy NER로 엔티티 후보 추출
    
    Hallucination 방지를 위해 LLM에 엔티티 힌트 제공
    
    Args:
        text: 입력 텍스트
        lang: "auto" (자동 감지), "ko", "en"
    
    Returns:
        [{"text": "OpenAI", "label": "Organization"}, ...]
    """
    # 언어 자동 감지
    if lang == "auto":
        detected_lang = _detect_language(text)
    else:
        detected_lang = lang
    
    nlp = _get_spacy_nlp(detected_lang)
    if not nlp:
        return []
    
    doc = nlp(text)
    
    # SpaCy 라벨 → Core Ontology 매핑
    label_map_ko = {
        "PS": "Person",       # 인명
        "LC": "Location",     # 지명
        "OG": "Organization", # 기관명
    }
    
    label_map_en = {
        "PERSON": "Person",
        "GPE": "Location",
        "ORG": "Organization",
        "PRODUCT": "Product",
        "EVENT": "Event",
    }
    
    label_map = label_map_ko if detected_lang == "ko" else label_map_en
    
    return [
        {"text": ent.text, "label": label_map.get(ent.label_, "Concept")}
        for ent in doc.ents
    ]


def _build_openie_prompt(sentences: List[str], ner_entities: List[Dict] = None) -> str:
    """
    [핵심 1-2] OpenIE용 LLM 프롬프트 생성
    
    LLM에게 Global Core Ontology를 제시하고
    SpaCy NER 결과를 힌트로 제공하여 Hallucination 방지
    
    Args:
        sentences: 추출할 문장 리스트
        ner_entities: SpaCy NER 결과 (엔티티 힌트)
    
    Returns:
        프롬프트 문자열
    """
    prompt = f"""You are an expert in Relationship Extraction for Knowledge Graph construction.

**Entity Types**: {', '.join(ENTITY_TYPES)}
**Relation Types**: {', '.join(RELATION_TYPES)}

**CRITICAL Rules**:
1. Extract ONLY explicit, meaningful relationships
2. DO NOT extract:
   - Bullet points (•, -, *, numbers) as entities
   - Korean particles (의, 은, 는, 이, 가) as part of entity names
   - Page numbers, ranges (e.g., "30~50페이지")
   - Generic words alone ("하나", "여러", "모든")
   - Partial words or fragments
3. Entity names must be:
   - Complete nouns (not "게임의" but "게임")
   - Proper names without particles
   - Minimum 2 characters
4. Use "related_to" ONLY when no specific relation applies
5. Verify entity types match the actual entity

"""
    
    if ner_entities:
        prompt += "**Entity Hints (from NER)**:\n"
        for ent in ner_entities[:10]:
            prompt += f"- {ent['label']}: {ent['text']}\n"
        prompt += "\n"
    
    prompt += "**Sentences**:\n"
    for i, sent in enumerate(sentences, 1):
        prompt += f"{i}. {sent}\n"
    
    prompt += """
**Output (JSON array only, NO explanation)**:
[{"subject":"EntityName","subject_type":"Type","relation":"relation_type","object":"EntityName","object_type":"Type","confidence":0.95}]

JSON only:"""
    
    return prompt

def _clean_entity_name(name: str) -> str:
    """
    엔티티 이름 정제 (조사 제거)
    
    한글 조사 제거:
        - "게임의" → "게임"
        - "시스템은" → "시스템"
        - "이순 신" → "이순신" (띄어쓰기 제거)
    """
    import re
    
    # 띄어쓰기 제거
    name = name.replace(" ", "")
    
    # 한글 조사 패턴 제거
    particles = [
        "의", "은", "는", "이", "가", "을", "를", 
        "에", "에서", "로", "으로", "와", "과"
    ]
    
    for particle in particles:
        if name.endswith(particle):
            name = name[:-len(particle)]
            break
    
    return name.strip()

def _call_llm(prompt: str, max_retries: int = 3) -> str:
    """
    [핵심 1-3] LLM API 호출 (Upstage Solar Pro2)
    
    실제 Relationship Extraction 수행
    
    Args:
        prompt: OpenIE 프롬프트
        max_retries: 최대 재시도 횟수
    
    Returns:
        LLM 응답 (JSON 문자열)
    """
    if not SOLAR_API_KEY:
        raise ValueError("SOLAR_PRO2_API_KEY 또는 API_KEY가 설정되지 않았습니다.")
    
    import requests
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"🔄 LLM 재시도... ({attempt + 1}/{max_retries})")
            
            response = requests.post(
                SOLAR_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {SOLAR_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "solar-pro2",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 800
                },
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
        
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 429 and attempt < max_retries - 1:
                print("   Rate limit, 10초 대기...")
                time.sleep(10)
                continue
            raise
        
        except Exception as e:
            print(f"❌ LLM 오류: {e}")
            raise
    
    raise TimeoutError(f"LLM API {max_retries}번 실패")


def _parse_llm_response(response: str) -> List[Dict]:
    """
    [핵심 1-4] LLM 응답 파싱 (강력한 JSON 추출)
    
    LLM이 설명 텍스트를 추가해도 JSON만 정확히 추출
    
    Args:
        response: LLM 응답
    
    Returns:
        파싱된 트리플 리스트
    """
    original_response = response
    
    # 방법 1: 전체를 바로 파싱
    try:
        triplets = json.loads(response.strip())
        return triplets if isinstance(triplets, list) else [triplets]
    except json.JSONDecodeError:
        pass
    
    # 방법 2: Markdown 코드블록 추출
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        try:
            triplets = json.loads(json_match.group(1).strip())
            return triplets if isinstance(triplets, list) else [triplets]
        except json.JSONDecodeError:
            pass
    
    # 방법 3: 첫 번째 JSON 배열만 추출 (가장 강력)
    json_array_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
    if json_array_match:
        try:
            triplets = json.loads(json_array_match.group(0))
            return triplets if isinstance(triplets, list) else [triplets]
        except json.JSONDecodeError:
            pass
    
    # 모든 방법 실패
    print(f"⚠️  JSON 파싱 실패 (응답 처음 500자):")
    print(f"   {original_response[:500]}")
    return []


def extract_triplets_from_text(
    text: str,
    source_url: str = "",
    domain: str = "general",
    crawl_time: str = None,
    max_sentences: int = 3,
    lang: str = "auto"
) -> List[Dict]:
    """
    [핵심 1] Relationship Extraction (RE) 메인 함수
    
    DB의 크롤링 페이지 데이터로부터 트리플 추출
    
    파이프라인:
        1. 문장 분리
        2. SpaCy NER로 엔티티 후보 추출 (Hallucination 방지)
        3. LLM(Solar Pro2) 기반 OpenIE로 관계 추출
        4. JSON 파싱 및 필터링
        5. Provenance 메타데이터 추가
    
    Args:
        text: 입력 텍스트 (Tavily 검색 결과의 content)
        source_url: 출처 URL (Provenance)
        domain: 도메인 태그 (네임스페이스)
        crawl_time: 크롤링 시간
        max_sentences: 최대 처리 문장 수 (토큰 절약)
        lang: 언어 ("auto", "ko", "en")
    
    Returns:
        트리플 리스트 [
            {
                "subject": "OpenAI",
                "relation": "produces",
                "object": "ChatGPT",
                "subject_type": "Organization",
                "object_type": "Product",
                "confidence": 0.98,
                "source_url": "https://...",
                "domain": "tech",
                "crawl_time": "2024-...",
                "extractor_version": "v1.0-prod"
            },
            ...
        ]
    
    Example:
        triplets = extract_triplets_from_text(
            text="OpenAI developed ChatGPT.",
            source_url="https://openai.com",
            domain="tech"
        )
    """
    # 1. 문장 분리
    sentences = [s.strip() for s in re.split(r'[.!?]\s+', text) if s.strip()][:max_sentences]
    if not sentences:
        return []
    
    # 2. NER 추출 (Hallucination 방지)
    ner_entities = _extract_ner(text, lang=lang)
    
    # 3. LLM 프롬프트 생성
    prompt = _build_openie_prompt(sentences, ner_entities)
    
    # 4. LLM 호출
    try:
        response = _call_llm(prompt)
        triplets = _parse_llm_response(response)
    except Exception as e:
        print(f"   ❌ RE 실패: {e}")
        return []
    
    # 5. Provenance 추가 및 신뢰도 필터링
    sentences = [s.strip() for s in re.split(r'[.!?]\s+', text) if s.strip()][:max_sentences]
    if not sentences:
        return []
    
    ner_entities = _extract_ner(text, lang=lang)
    prompt = _build_openie_prompt(sentences, ner_entities)
    
    try:
        response = _call_llm(prompt)
        triplets = _parse_llm_response(response)
    except Exception as e:
        print(f"   ❌ RE 실패: {e}")
        return []
    
    # 강화된 필터링
    filtered = []
    for t in triplets:
        # 신뢰도 필터
        if t.get('confidence', 0) < MIN_CONFIDENCE:
            continue
        
        # 엔티티 이름 정제
        subject = _clean_entity_name(t.get('subject', ''))
        obj = _clean_entity_name(t.get('object', ''))
        relation = t.get('relation', '')
        
        # ===== 제외 조건 (강화) =====
        
        # 1. 불릿 포인트
        invalid_chars = ['•', '·', '-', '*', '▪', '▫', '○', '●']
        if subject in invalid_chars or obj in invalid_chars:
            continue
        
        # 2. 너무 짧은 엔티티 (1글자 이하)
        if len(subject) < 2 or len(obj) < 2:
            continue
        
        # 3. 숫자만 있는 엔티티
        if subject.isdigit() or obj.isdigit():
            continue
        
        # 4. 페이지 번호, 범위
        page_patterns = [r'\d+페이지', r'\d+~\d+', r'p\.\d+', r'page\s*\d+']
        if any(re.search(p, subject, re.I) or re.search(p, obj, re.I) for p in page_patterns):
            continue
        
        # 5. 일반적인 단어만 (의미 없음)
        generic_words = ['하나', '여러', '모든', '일부', '전체', '기타', '등등', 
                        '예시', '참고', '샘플', '테스트']
        if subject in generic_words or obj in generic_words:
            continue
        
        # 6. 공백, 특수문자만
        if not re.search(r'[가-힣a-zA-Z]', subject) or not re.search(r'[가-힣a-zA-Z]', obj):
            continue
        
        # 7. related_to 남발 방지 (양쪽이 모두 Concept이고 related_to면 제외)
        if (relation == "related_to" and 
            t.get('subject_type') == "Concept" and 
            t.get('object_type') == "Concept"):
            # 둘 다 Concept이면서 related_to는 너무 모호함
            continue
        
        # ===== 통과 =====
        
        t['subject'] = subject
        t['object'] = obj
        t['source_url'] = source_url
        t['domain'] = domain
        t['crawl_time'] = crawl_time or datetime.now().isoformat()
        t['extractor_version'] = EXTRACTOR_VERSION
        
        filtered.append(t)
    
    return filtered 


# ============================================================================
# LangGraph Tool용 Public API
# ============================================================================

def kg_get_entity(name: str, max_hops: int = 1, domain: Optional[str] = None) -> List[Dict]:
    """
    [LangGraph Tool] 엔티티 정보 조회
    
    다른 Agent가 KG에서 정보를 조회할 때 사용
    
    Args:
        name: 엔티티 이름
        max_hops: 최대 탐색 거리
        domain: 도메인 필터
    
    Returns:
        트리플 리스트
    """
    kg = KnowledgeGraphStore()
    return kg.get_entity_info(name, max_hops, domain)


def kg_find_related(
    entity_a: str,
    entity_b: str,
    max_length: int = 4,
    domain: Optional[str] = None
) -> Optional[List[Tuple[str, str, str]]]:
    """
    [LangGraph Tool] 엔티티 간 경로 찾기
    
    두 엔티티의 연관성을 파악할 때 사용
    
    Args:
        entity_a: 시작 엔티티
        entity_b: 종료 엔티티
        max_length: 최대 경로 길이
        domain: 도메인 필터
    
    Returns:
        경로 또는 None
    """
    kg = KnowledgeGraphStore()
    return kg.find_path(entity_a, entity_b, max_length, domain)


def kg_search_text(query: str, top_k: int = 10) -> List[str]:
    """
    [LangGraph Tool] 엔티티 검색
    사용자 쿼리에 맞는 엔티티 찾기
    
    Args:
        query: 검색 쿼리
        top_k: 반환할 최대 결과 수
    
    Returns:
        엔티티 이름 리스트
    """
    kg = KnowledgeGraphStore()
    return kg.search_entities(query, top_k)


def kg_add_triplets(triplets: List[Dict], auto_save: bool = True) -> int:
    """
    트리플 배치 추가 (KG 구축/증강)
    
    Args:
        triplets: 트리플 리스트
        auto_save: 자동 저장 여부
    
    Returns:
        추가된 트리플 수
    """
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
    """KG 통계"""
    return KnowledgeGraphStore().get_stats()


def save_kg():
    """KG 저장 (pickle + SQLite)"""
    kg = KnowledgeGraphStore()
    kg.save()
    kg.export_to_sqlite()


def load_kg():
    """KG 로드"""
    KnowledgeGraphStore().load()


__version__ = "1.0.0"