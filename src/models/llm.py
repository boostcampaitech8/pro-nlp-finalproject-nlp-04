from config.config import API_KEY
from langchain_upstage import ChatUpstage

def get_llm(
    model: str = "solar-pro2",
    temperature: float = 0.7,
    max_tokens: int = 65536,
    reasoning_effort: str = "medium"
):
    return ChatUpstage(
    api_key=API_KEY,
    model=model,
    temperature=temperature,
    max_tokens=max_tokens,
    reasoning_effort=reasoning_effort
)

def get_mini_llm(
    temperature: float = 0.7, 
    max_tokens: int = 16384
):
    return ChatUpstage(
    api_key=API_KEY,
    model="upstage/solar-1-mini-chat",
    temperature=temperature,
    max_tokens=max_tokens
)