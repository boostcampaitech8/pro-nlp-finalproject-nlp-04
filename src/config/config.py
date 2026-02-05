from dotenv import load_dotenv
import os
from pathlib import Path

# config 폴더 안 .env 경로를 명시적으로 지정
dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

API_KEY = os.getenv("API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
