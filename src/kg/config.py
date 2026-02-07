"""
Knowledge Graph 설정 및 상수
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / os.getenv("KG_DATA_DIR", "data")
DATA_DIR.mkdir(exist_ok=True)

KG_PICKLE_PATH = DATA_DIR / os.getenv("KG_PICKLE_FILE", "knowledge_graph.gpickle")
KG_SQLITE_PATH = DATA_DIR / os.getenv("KG_SQLITE_FILE", "knowledge_graph.db")
TAVILY_DB_PATH = DATA_DIR / "tavily_results.db"

SOLAR_API_KEY = os.getenv("SOLAR_PRO2_API_KEY", "") or os.getenv("API_KEY", "")
SOLAR_ENDPOINT = os.getenv("SOLAR_PRO2_ENDPOINT", "https://api.upstage.ai/v1/solar/chat/completions")

if not SOLAR_API_KEY:
    print("⚠️  경고: SOLAR_PRO2_API_KEY (또는 API_KEY)가 설정되지 않았습니다.")

SPACY_MODEL_KO = os.getenv("SPACY_MODEL_KO", "ko_core_news_sm")
SPACY_MODEL_EN = os.getenv("SPACY_MODEL_EN", "en_core_web_sm")

MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.5"))
EXTRACTOR_VERSION = os.getenv("EXTRACTOR_VERSION", "v1.0-prod")

ENTITY_TYPES = [
    "Person",
    "Organization",
    "Location",
    "Product",
    "Concept",
    "Event"
]
VALID_ENTITY_TYPES = set(ENTITY_TYPES)

RELATION_TYPES = [
    "works_for",
    "located_in",
    "produces",
    "owns",
    "related_to",
    "founded_by",
    "acquires",
    "member_of",
    "part_of",
    "causes"
]

RELATION_NORMALIZER = {
    "근무": "works_for", "소속": "works_for", "재직": "works_for",
    "일하다": "works_for", "employed_by": "works_for",
    "위치": "located_in", "본사": "located_in", "있다": "located_in",
    "based_in": "located_in", "headquarters": "located_in",
    "생산": "produces", "제조": "produces", "출시": "produces",
    "개발": "produces", "만들다": "produces", "creates": "produces",
    "소유": "owns", "보유": "owns", "owns": "owns",
    "설립": "founded_by", "창립": "founded_by", "founded": "founded_by",
    "인수": "acquires", "매입": "acquires", "acquired": "acquires",
    "포함": "part_of", "구성": "part_of", "consists_of": "part_of",
    "회원": "member_of", "구성원": "member_of", "member": "member_of",
}

TYPE_CONSTRAINTS = {
    "works_for": {
        "subject_types": ["Person"],
        "object_types": ["Organization"]
    },
    "located_in": {
        "subject_types": ["Organization", "Person", "Event", "Product"],
        "object_types": ["Location"]
    },
    "produces": {
        "subject_types": ["Organization", "Person"],
        "object_types": ["Product", "Concept"]
    },
    "owns": {
        "subject_types": ["Organization", "Person"],
        "object_types": ["Product", "Organization"]
    },
    "founded_by": {
        "subject_types": ["Organization"],
        "object_types": ["Person"]
    },
    "acquires": {
        "subject_types": ["Organization"],
        "object_types": ["Organization", "Product"]
    },
    "member_of": {
        "subject_types": ["Person"],
        "object_types": ["Organization"]
    },
    "part_of": {
        "subject_types": ["Concept", "Product", "Organization", "Location"],
        "object_types": ["Concept", "Product", "Organization", "Location"]
    },
    "causes": {
        "subject_types": ["Event", "Concept"],
        "object_types": ["Event", "Concept"]
    },
    "related_to": {
        # 모든 타입 조합 허용 (fallback)
        "subject_types": ENTITY_TYPES,
        "object_types": ENTITY_TYPES
    }
}

RELATION_TRIGGERS = {
    "works_for": [
        # 한글
        "근무", "일하다", "재직", "소속", "직장", "회사", "입사", "퇴사",
        # 영어
        "work", "employ", "hired", "job", "career", "position"
    ],
    "located_in": [
        # 한글
        "위치", "본사", "있다", "소재", "자리", "거점", "주소",
        # 영어
        "located", "based", "situated", "headquarters", "office", "address"
    ],
    "produces": [
        # 한글
        "생산", "제조", "개발", "출시", "만들다", "제작", "발표", "론칭",
        # 영어
        "produce", "develop", "create", "manufacture", "release", "launch", "make", "build"
    ],
    "owns": [
        # 한글
        "소유", "보유", "가지다", "소지",
        # 영어
        "own", "possess", "hold", "have"
    ],
    "founded_by": [
        # 한글
        "설립", "창립", "창업", "창설", "세우다",
        # 영어
        "found", "establish", "create", "start"
    ],
    "acquires": [
        # 한글
        "인수", "매입", "합병", "인수합병", "매수",
        # 영어
        "acquire", "buy", "purchase", "merge", "takeover"
    ],
    "member_of": [
        # 한글
        "회원", "구성원", "멤버", "소속",
        # 영어
        "member", "belong", "part of"
    ],
    "part_of": [
        # 한글
        "포함", "구성", "일부", "속하다", "포함하다",
        # 영어
        "part", "include", "contain", "comprise", "consist"
    ],
    "causes": [
        # 한글
        "야기", "초래", "유발", "발생", "일으키다", "원인",
        # 영어
        "cause", "lead", "result", "trigger", "induce"
    ],
    # related_to는 trigger 체크 없음 (유연성 유지)
}

CONFIDENCE_THRESHOLDS = {
    "related_to": 0.9,      # 높게 (남발 방지)
    "works_for": 0.8,
    "produces": 0.8,
    "located_in": 0.75,
    "founded_by": 0.8,
    "acquires": 0.8,
    "owns": 0.75,
    "member_of": 0.75,
    "part_of": 0.7,
    "causes": 0.75,
    "default": 0.7
}