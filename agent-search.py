import os
from typing import List, TypedDict
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langsmith import traceable

import getpass
from dotenv import load_dotenv

#################### FOR DEV PURPOSE #########################
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google AI API key: ")
#################### FOR DEV PURPOSE #########################

MODEL_NAME = "gemini-3-pro-preview"

class SearchQueries(BaseModel):
    queries: List[str] = Field(
        default_factory=list,
        description="검색 엔진용으로 최적화된 3~6개의 검색 쿼리 리스트"
    )

class AgentState(TypedDict):
    question: str
    search_queries: List[str]

def generate_queries(state: AgentState):
    """
    Pydantic과 Structured Output을 사용하여 구조화된 검색 쿼리를 생성.
    """
    question = state["question"]
    print(f"\n--- [Node: Query Generator] 분석 중: {question} ---")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 검색 전문가입니다. 사용자의 질문을 분석하여 
        가장 정확하고 전문적인 검색 결과를 얻을 수 있는 다각도의 검색 쿼리를 생성하세요.
        결과는 영어 및 한국어 각각 3개 내외로 작성하세요."""),
        ("human", "{question}")
    ])
    
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.1)
    structured_llm = llm.with_structured_output(SearchQueries)
    
    query_chain = prompt | structured_llm
    result = query_chain.invoke({"question": question})
    
    return {"search_queries": result.queries}

workflow = StateGraph(AgentState)

workflow.add_node("query_gen", generate_queries)

workflow.add_edge(START, "query_gen")
workflow.add_edge("query_gen", END)

app = workflow.compile()

if __name__ == '__main__':
    inputs = {"question": "게임 시스템 개선을 위한 기획서 양식이 필요해."}
    config = {"configurable": {"thread_id": "1"}}

    output = app.invoke(inputs, config)

    print("\n--- [최종 결과] ---")
    for i, q in enumerate(output["search_queries"], 1):
        print(f"{i}. {q}")