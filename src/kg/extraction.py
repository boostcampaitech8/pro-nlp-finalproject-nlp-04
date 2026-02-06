"""
Relationship Extraction using LLM (OpenIE)
"""
import re
import json
import time
from datetime import datetime
from typing import List, Dict

from .config import (
    SOLAR_API_KEY,
    SOLAR_ENDPOINT,
    MIN_CONFIDENCE,
    EXTRACTOR_VERSION,
    ENTITY_TYPES,
    RELATION_TYPES
)
from .ner import _extract_ner


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