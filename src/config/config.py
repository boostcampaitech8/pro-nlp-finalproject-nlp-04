from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")