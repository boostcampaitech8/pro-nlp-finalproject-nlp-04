"""
LangGraph 노드 - KG 통합

역할:
    1. kg_query_node: 검색 전 KG에서 정보 조회 (캐시 역할)
    2. kg_extract_and_save_node: Tavily 검색 결과를 KG에 저장
    3. KGToolWrapper: Tool로 등록하여 다른 Agent에서 사용
"""
import sqlite3
from datetime import datetime
from typing import List

from .config import TAVILY_DB_PATH
from .extraction import extract_triplets_from_text
from .tools import kg_add_triplets, kg_search_text, kg_get_entity, save_kg


def init_tavily_db():
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
    from state.research import ResearchState, KGQueryResult, KGTriple
    
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
    from state.research import ResearchState
    
    search_results = state.search_results
    
    if not search_results:
        print("\n--- [KG Extract & Save] 검색 결과 없음 ---")
        return {"kg_extraction_summary": "검색 결과 없음"}
    
    print(f"\n--- [KG Extract & Save] {len(search_results)}개 검색 결과 처리 중 ---")
    
    init_tavily_db()
    
    conn = sqlite3.connect(TAVILY_DB_PATH)
    cursor = conn.cursor()
    
    all_triplets = []
    urls_with_triplets = set()
    search_time = datetime.now().isoformat()

    for idx, item in enumerate(search_results, 1):
        print(f"   [{idx}/{len(search_results)}] {item.title[:50]}...")

        cursor.execute(
            '''INSERT INTO tavily_results 
               (query, title, url, content, score, search_time, processed) 
               VALUES (?, ?, ?, ?, ?, ?, 0)''',
            (state.question, item.title, item.url, item.content, item.score, search_time)
        )

        try:
            triplets = extract_triplets_from_text(
                text=item.content,
                source_url=item.url,
                domain="research",
                crawl_time=search_time,
                lang="auto"
            )

            if triplets:
                print(f"      ✅ {len(triplets)}개 트리플 추출")
                all_triplets.extend(triplets)
                urls_with_triplets.add(item.url)
            else:
                print(f"      ℹ️  트리플 추출 실패 (다음에 재시도 가능)")

        except Exception as e:
            print(f"      ❌ 오류: {e}")

    conn.commit()
    conn.close()

    if all_triplets:
        try:
            count = kg_add_triplets(all_triplets, auto_save=False)
            save_kg()
            summary = f"✅ KG에 {count}개 트리플 추가 완료"
            print(f"\n{summary}")

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
    MIN_TRIPLETS = 15
    if len(triplets) < MIN_TRIPLETS:
        return True
    
    MIN_AVG_CONFIDENCE = 0.7
    avg_confidence = sum(t.confidence for t in triplets) / len(triplets)
    if avg_confidence < MIN_AVG_CONFIDENCE:
        return True
    
    return False


class KGToolWrapper:
    @staticmethod
    def search_entities(query: str) -> str:
        entities = kg_search_text(query, top_k=5)
        
        if not entities:
            return f"'{query}' 관련 엔티티가 KG에 없습니다."
        
        return f"'{query}' 검색 결과:\n" + "\n".join(f"- {e}" for e in entities)
    
    @staticmethod
    def get_entity_info(entity_name: str, domain: str = None) -> str:
        info = kg_get_entity(entity_name, max_hops=1, domain=domain)
        
        if not info:
            return f"'{entity_name}' 엔티티가 KG에 없습니다."
        
        output = f"'{entity_name}' 정보 ({len(info)}건):\n"
        for r in info[:5]:
            output += f"- {r['subject']} {r['relation']} {r['object']} (신뢰도: {r['confidence']:.2f})\n"
        
        if len(info) > 5:
            output += f"... 외 {len(info) - 5}건"
        
        return output