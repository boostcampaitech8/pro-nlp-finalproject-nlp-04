"""KG 유틸리티 함수"""

import re
from typing import List


def extract_keywords(text: str, lang: str = "auto") -> List[str]:
    """
    ★★★ 강건한 키워드 추출 (SpaCy 의존도 낮춤) ★★★
    
    전략:
        1. 정규표현식으로 한글/영어 단어 추출 (우선)
        2. SpaCy 형태소 분석 (보조)
        3. 중복 제거 및 정렬
    
    Args:
        text: 입력 텍스트
        lang: 언어 (사용 안 함, 호환성 유지)
    
    Returns:
        키워드 리스트
    """
    keywords = set()
    
    # ===== 전략 1: 정규표현식 (가장 강건) =====
    
    # 1-1. 한글: 2글자 이상 연속된 한글 (복합명사 포함)
    # "사건사고", "게임기획서", "시스템디자인" 등을 잡아냄
    korean_words = re.findall(r'[가-힣]{2,}', text)
    keywords.update(korean_words)
    
    # 1-2. 영어: 단어 단위 (2글자 이상)
    english_words = re.findall(r'\b[A-Za-z]{2,}\b', text)
    keywords.update(english_words)
    
    # 1-3. 숫자+명사 조합 (예: "2000대", "50개")
    number_noun = re.findall(r'\d+[가-힣]+', text)
    keywords.update(number_noun)
    
    # 1-4. 영문 약어 (대문자 2글자 이상, 예: "IT", "AI", "CEO")
    abbreviations = re.findall(r'\b[A-Z]{2,}\b', text)
    keywords.update(abbreviations)
    
    # ===== 전략 2: SpaCy 보조 (있으면 사용) =====
    try:
        from .ner import _detect_language, _get_spacy_nlp
        
        detected_lang = _detect_language(text)
        nlp = _get_spacy_nlp(detected_lang)
        
        if nlp:
            doc = nlp(text)
            
            # 고유명사만 추가 (일반 명사는 정규식으로 이미 추출됨)
            for token in doc:
                if token.pos_ == "PROPN" and len(token.text) > 1:
                    keywords.add(token.text)
    except:
        # SpaCy 없어도 괜찮음
        pass
    
    return list(keywords)


def remove_stopwords(keywords: List[str]) -> List[str]:
    """
    ★★★ 강화된 불용어 제거 ★★★
    """
    # 불용어 사전 (확장)
    STOPWORDS_KO = {
        # 일반 명사
        "것", "수", "등", "때", "곳", "중", "더", "만", "개", "번",
        "점", "건", "명", "분", "초", "년", "월", "일", "시",
        
        # 동사 어간
        "조사", "분석", "추천", "검색", "확인", "제공", "설명",
        "알려", "보여", "찾아", "해줘", "주세요", "부탁",
        
        # 형용사/부사
        "좋은", "나쁜", "많은", "적은", "크다", "작다",
        
        # 대명사
        "이", "그", "저", "여기", "거기", "저기"
    }
    
    STOPWORDS_EN = {
        "thing", "one", "way", "time", "place", "information", "data",
        "please", "show", "tell", "find", "search", "give", "help",
        "good", "bad", "many", "few", "big", "small",
        "this", "that", "here", "there"
    }
    
    stopwords = STOPWORDS_KO | STOPWORDS_EN
    
    filtered = []
    for k in keywords:
        # 소문자로 변환해서 체크
        k_lower = k.lower()
        
        # 불용어 제거
        if k_lower in stopwords:
            continue
        
        # 너무 짧은 키워드 제거 (1글자)
        if len(k) < 2:
            continue
        
        # 순수 숫자만 있는 키워드 제거
        if k.isdigit():
            continue
        
        # 특수문자만 있는 키워드 제거
        if not re.search(r'[가-힣a-zA-Z0-9]', k):
            continue
        
        filtered.append(k)
    
    return filtered


def expand_keywords(keywords: List[str]) -> List[str]:
    """
    ★★★ 키워드 확장 (동의어, 변형) ★★★
    
    예:
        "사건사고" → ["사건사고", "사건", "사고"]
        "IT기업" → ["IT기업", "IT", "기업"]
    """
    expanded = set(keywords)
    
    for keyword in keywords:
        # 한글 복합명사 분해 (2글자씩)
        if re.match(r'^[가-힣]{4,}$', keyword):
            # "사건사고" (4글자) → "사건", "사고"
            for i in range(0, len(keyword) - 1, 2):
                if i + 2 <= len(keyword):
                    expanded.add(keyword[i:i+2])
        
        # 영어+한글 조합 분해
        # "IT기업" → "IT", "기업"
        parts = re.findall(r'[A-Za-z]+|[가-힣]+|\d+', keyword)
        if len(parts) > 1:
            expanded.update(parts)
    
    return list(expanded)


def infer_domain(question: str) -> str:
    """
    ★★★ 도메인 자동 추론 (확장) ★★★
    """
    question_lower = question.lower()
    
    DOMAIN_KEYWORDS = {
        "tech": [
            "it", "소프트웨어", "개발", "프로그래밍", "ai", "인공지능",
            "클라우드", "데이터", "반도체", "software", "developer", "tech",
            "컴퓨터", "전자", "디지털", "스타트업"
        ],
        "travel": [
            "여행", "관광", "여행지", "관광지", "호텔", "맛집", "축제",
            "travel", "tourism", "sightseeing", "hotel", "restaurant",
            "명소", "투어", "리조트"
        ],
        "auto": [
            "자동차", "차", "차량", "자동차업", "모터", "엔진", "차종",
            "car", "vehicle", "automotive", "motor", "suv", "sedan"
        ],
        "finance": [
            "금융", "은행", "투자", "주식", "펀드", "증권", "경제",
            "finance", "bank", "investment", "stock", "economy"
        ],
        "news": [
            "사건", "사고", "뉴스", "보도", "사건사고", "범죄", "재난",
            "news", "incident", "accident", "crime", "event", "disaster"
        ],
        "game": [
            "게임", "기획", "게임기획", "게임개발", "게임업계",
            "game", "gaming", "esports"
        ],
    }
    
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        if score > 0:
            scores[domain] = score
    
    if not scores:
        return "general"
    
    return max(scores, key=scores.get)


def calculate_relevance_score(
    entity: str,
    keywords: List[str],
    question_domain: str,
    kg_store
) -> float:
    """
    엔티티와 질문의 관련성 점수 계산
    """
    score = 0.0
    
    # 1. 키워드 매칭 점수 (0 ~ 0.5)
    entity_lower = entity.lower()
    
    # 완전 일치 보너스
    if entity_lower in [k.lower() for k in keywords]:
        score += 0.5
    else:
        # 부분 일치
        matched = sum(1 for kw in keywords if kw.lower() in entity_lower)
        score += min(matched / max(len(keywords), 1), 0.3)
    
    # 2. 도메인 매칭 점수 (0 ~ 0.3)
    if kg_store.graph.has_node(entity):
        entity_domains = kg_store.graph.nodes[entity].get('domains', set())
        
        if question_domain in entity_domains:
            score += 0.3
        elif question_domain == "general" or "general" in entity_domains:
            score += 0.1
    
    # 3. 엔티티 길이 보너스 (0 ~ 0.2)
    # 긴 이름 = 더 구체적 = 관련성 높음
    name_length_score = min(len(entity) / 20, 0.2)
    score += name_length_score
    
    return min(score, 1.0)