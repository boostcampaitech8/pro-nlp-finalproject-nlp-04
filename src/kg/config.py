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