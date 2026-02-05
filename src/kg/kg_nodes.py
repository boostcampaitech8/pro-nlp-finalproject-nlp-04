"""
LangGraph 노드 - KG 통합

역할:
    1. kg_query_node: 검색 전 KG에서 정보 조회 (캐시 역할)
    2. kg_extract_and_save_node: Tavily 검색 결과를 KG에 저장
    3. KGToolWrapper: Tool로 등록하여 다른 Agent에서 사용
"""

import sqlite3
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from .kg_module import (
    extract_triplets_from_text,
    kg_add_triplets,
    kg_search_text,
    kg_get_entity,
    save_kg,
    TAVILY_DB_PATH,
    DATA_DIR
)


def init_tavily_db():
    """
    Tavily 검색 결과 DB 초기화
    
    검색 결과를 저장하여:
        1. 중복 검색 방지
        2. 배치 처리용 데이터 축적
        3. Provenance 추적
    
    테이블 구조:
        - query: 검색 쿼리
        - title: 검색 결과 제목
        - url: 원본 URL
        - content: 본문
        - score: Tavily 점수
        - processed: KG 추출 완료 여부
    """
    conn = sqlite3.connect(TAVILY_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tavily_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            title TEXT,
            url TEXT,
            content TEXT,
            score REAL,
            search_time TEXT,
            processed BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()


def kg_query_node(state):
    """
    [LangGraph 노드] 검색 전 KG 조회
    
    역할:
        사용자 질문과 관련된 정보가 KG에 이미 있는지 확인
        → 있으면 Tavily 호출 생략 (비용 절감)
    
    흐름:
        1. 사용자 질문에서 키워드 추출
        2. KG에서 관련 엔티티 검색
        3. 발견된 엔티티 정보 조회
        4. state.kg_cached_info에 저장
    
    Args:
        state: ResearchState
    
    Returns:
        업데이트된 state
    """
    from state.research import ResearchState, KGQueryResult, KGTriple
    from datetime import datetime, timedelta
    
    question = state.question
    print(f"\n--- [KG Query Node] KG에서 '{question}' 관련 정보 조회 ---")
    
    keywords = [w for w in question.split() if len(w) > 1][:5]
    
    queried_entities = []
    found_triplets_raw = []
    
    for keyword in keywords:
        entities = kg_search_text(keyword, top_k=3)
        
        for entity in entities:
            if entity not in queried_entities:
                queried_entities.append(entity)
            
            info = kg_get_entity(entity, max_hops=1)
            if info:
                found_triplets_raw.extend(info)
    
    # 중복 제거
    unique_triplets = []
    seen = set()
    for r in found_triplets_raw:
        key = (r['subject'], r['relation'], r['object'])
        if key not in seen:
            seen.add(key)
            unique_triplets.append(r)
    
    found_triplets = [
        KGTriple(
            subject=r['subject'],
            relation=r['relation'],
            object=r['object'],
            confidence=r['confidence'],
            source_url=r.get('source_url', ''),
            domain=r.get('domain', 'general')
        )
        for r in unique_triplets
    ]
    
    # 검색 필요 여부 판단
    need_search = _should_search(found_triplets, question)
    
    if found_triplets:
        summary_lines = []
        for t in found_triplets[:10]:
            summary_lines.append(
                f"- {t.subject} {t.relation} {t.object} "
                f"(신뢰도: {t.confidence:.2f})"
            )
        summary_text = "\n".join(summary_lines)
        
        print(f"   ✅ KG에서 {len(found_triplets)}개 트리플 발견")
        print(f"   조회 엔티티: {', '.join(queried_entities[:5])}")
        
        if need_search:
            print(f"   ℹ️  정보가 부족하거나 오래되어 Tavily 검색 진행")
        else:
            print(f"   ✅ 충분한 정보가 있어 검색 스킵")
    else:
        summary_text = ""
        need_search = True
        print(f"   ℹ️  KG에 관련 정보 없음 → Tavily 검색 필요")
    
    kg_result = KGQueryResult(
        queried_entities=queried_entities,
        found_triplets=found_triplets,
        summary_text=summary_text
    )
    
    return {
        "kg_query_result": kg_result,
        "kg_cached_info": summary_text,
        "need_search": need_search
    }


def kg_extract_and_save_node(state):
    """
    [핵심 LangGraph 노드] Tavily 검색 결과 → KG 저장
    
    역할:
        검색 직후 즉시 트리플 추출하여 KG에 저장
        → 실시간 KG 구축 및 증강
    
    파이프라인:
        1. Tavily 검색 결과 (SearchItem 리스트) 가져오기
        2. 각 결과별로:
           a. Tavily DB에 저장 (processed=0)
           b. content에서 트리플 추출 (extract_triplets_from_text)
           c. KG에 추가 (kg_add_triplets)
        3. KG 저장 (pickle + SQLite)
    
    Args:
        state: ResearchState (search_results 포함)
    
    Returns:
        업데이트된 state (kg_extraction_summary)
    """
    from state.research import ResearchState
    
    search_results = state.search_results
    
    if not search_results:
        print("\n--- [KG Extract & Save] 검색 결과 없음 ---")
        return {"kg_extraction_summary": "검색 결과 없음"}
    
    print(f"\n--- [KG Extract & Save] {len(search_results)}개 검색 결과 처리 중 ---")
    
    # Tavily DB 초기화
    init_tavily_db()
    
    conn = sqlite3.connect(TAVILY_DB_PATH)
    cursor = conn.cursor()
    
    all_triplets = []
    urls_with_triplets = set()
    search_time = datetime.now().isoformat()

    for idx, item in enumerate(search_results, 1):
        print(f"   [{idx}/{len(search_results)}] {item.title[:50]}...")

        # 1. Tavily DB에 저장 (나중에 배치 처리 가능)
        cursor.execute(
            '''INSERT INTO tavily_results 
               (query, title, url, content, score, search_time, processed) 
               VALUES (?, ?, ?, ?, ?, ?, 0)''',
            (state.question, item.title, item.url, item.content, item.score, search_time)
        )

        # 2. 트리플 추출 (content만) — 추출 결과는 모아둔다
        try:
            triplets = extract_triplets_from_text(
                text=item.content,
                source_url=item.url,
                domain="research",  # 도메인 태그
                crawl_time=search_time,
                lang="auto"  # 자동 언어 감지
            )

            if triplets:
                print(f"      ✅ {len(triplets)}개 트리플 추출")
                all_triplets.extend(triplets)
                urls_with_triplets.add(item.url)
            else:
                print(f"      ℹ️  트리플 추출 실패 (다음에 재시도 가능)")

        except Exception as e:
            # 추출 중 예외가 나도 processed는 변경하지 않음 — 재시도 대상으로 남김
            print(f"      ❌ 오류: {e}")

    # DB에 INSERT 쿼리들을 commit (삽입은 모두 끝난 상태)
    conn.commit()
    conn.close()

    # 3. KG에 추가 — 한 번에 처리 (중복 방지는 kg_add_triplets 내부에서 이루어짐)
    if all_triplets:
        try:
            count = kg_add_triplets(all_triplets, auto_save=False)
            # KG 파일로 저장 (pickle + sqlite)
            save_kg()
            summary = f"✅ KG에 {count}개 트리플 추가 완료"
            print(f"\n{summary}")

            # 이제 실제로 저장이 완료되었으므로 processed 플래그를 업데이트
            conn = sqlite3.connect(TAVILY_DB_PATH)
            cursor = conn.cursor()
            for url in urls_with_triplets:
                cursor.execute('UPDATE tavily_results SET processed = 1 WHERE url = ?', (url,))
            conn.commit()
            conn.close()
            print(f"[KG] processed flag updated for {len(urls_with_triplets)} URLs")

        except Exception as e:
            summary = f"❌ KG 저장 실패: {e}"
            print(f"\n{summary}")
    else:
        summary = "⚠️ 추출된 트리플 없음"
        print(f"\n{summary}")

    return {"kg_extraction_summary": summary}


def _should_search(triplets: List, question: str) -> bool:
    """
    검색 필요 여부 판단 로직
    
    판단 기준:
        1. 트리플 수 (충분한가?)
        2. 신뢰도 (높은가?)
        3. 정보의 신선도 (최근 것인가?)
        4. 커버리지 (질문을 충분히 답변할 수 있는가?)
    
    Returns:
        True: 검색 필요
        False: KG 정보만으로 충분
    """
    from datetime import datetime, timedelta
    
    # 기준 1: 최소 트리플 수
    MIN_TRIPLETS = 15  # 최소 15개는 있어야 함
    if len(triplets) < MIN_TRIPLETS:
        return True  # 정보 부족 → 검색 필요
    
    # 기준 2: 평균 신뢰도
    MIN_AVG_CONFIDENCE = 0.7
    avg_confidence = sum(t.confidence for t in triplets) / len(triplets)
    if avg_confidence < MIN_AVG_CONFIDENCE:
        return True  # 신뢰도 낮음 → 검색 필요
    
    # # 기준 3: 정보의 신선도 (최근 7일 이내?)
    # MAX_AGE_DAYS = 7
    # recent_count = 0
    # for t in triplets:
    #     # crawl_time이 없으면 오래된 것으로 간주
    #     if not hasattr(t, 'crawl_time') or not t.crawl_time:
    #         continue
        
    #     try:
    #         crawl_time = datetime.fromisoformat(t.crawl_time)
    #         age = (datetime.now() - crawl_time).days
    #         if age <= MAX_AGE_DAYS:
    #             recent_count += 1
    #     except:
    #         pass
    
    # # 최소 30% 이상이 최근 정보여야 함
    # if len(triplets) > 0 and recent_count / len(triplets) < 0.3:
    #     return True  # 정보가 오래됨 → 검색 필요
    
    # # 기준 4: 키워드 커버리지
    # # 질문의 주요 키워드가 트리플에 포함되어 있는가?
    # keywords = [w.lower() for w in question.split() if len(w) > 1]
    # covered_keywords = set()
    
    # for t in triplets:
    #     for kw in keywords:
    #         if kw in t.subject.lower() or kw in t.object.lower():
    #             covered_keywords.add(kw)
    
    # coverage = len(covered_keywords) / len(keywords) if keywords else 0
    # MIN_COVERAGE = 0.5  # 최소 50% 커버
    
    # if coverage < MIN_COVERAGE:
    #     return True  # 커버리지 부족 → 검색 필요
    
    # 모든 기준 통과 → 검색 불필요
    return False    

# ============================================================================
# LangGraph Tool 래퍼
# ============================================================================

class KGToolWrapper:
    """
    [LangGraph Tool] Agent가 KG를 조회할 수 있도록 Tool로 래핑
    
    사용 예시:
        from langchain.tools import Tool
        
        kg_tool = Tool(
            name="knowledge_graph_search",
            func=KGToolWrapper.search_entities,
            description="지식 그래프에서 엔티티 검색"
        )
    """
    
    @staticmethod
    def search_entities(query: str) -> str:
        """
        엔티티 검색 (문자열 반환)
        
        Args:
            query: 검색 쿼리
        
        Returns:
            검색 결과 문자열
        """
        entities = kg_search_text(query, top_k=5)
        
        if not entities:
            return f"'{query}' 관련 엔티티가 KG에 없습니다."
        
        return f"'{query}' 검색 결과:\n" + "\n".join(f"- {e}" for e in entities)
    
    @staticmethod
    def get_entity_info(entity_name: str, domain: str = None) -> str:
        """
        엔티티 정보 조회 (문자열 반환)
        
        Args:
            entity_name: 엔티티 이름
            domain: 도메인 필터 (선택)
        
        Returns:
            엔티티 정보 문자열
        """
        info = kg_get_entity(entity_name, max_hops=1, domain=domain)
        
        if not info:
            return f"'{entity_name}' 엔티티가 KG에 없습니다."
        
        output = f"'{entity_name}' 정보 ({len(info)}건):\n"
        for r in info[:5]:
            output += f"- {r['subject']} {r['relation']} {r['object']} (신뢰도: {r['confidence']:.2f})\n"
        
        if len(info) > 5:
            output += f"... 외 {len(info) - 5}건"
        
        return output