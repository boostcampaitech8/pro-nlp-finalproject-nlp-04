"""SpaCy NER"""

from typing import List, Dict, Optional
from .config import SPACY_MODEL_KO, SPACY_MODEL_EN

_nlp_ko = None
_nlp_en = None


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