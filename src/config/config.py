from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")