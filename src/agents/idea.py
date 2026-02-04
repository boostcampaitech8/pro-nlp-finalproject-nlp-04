import json
from state.base import GlobalState
from models.llm import get_mini_llm, get_llm
from .idea_prompts import ANALYZER_PROMPT, GENERATOR_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

def idea_router(state: GlobalState) -> str:
    # analyzer에서 정한 intent를 가져옴
    intent = state['supervision'].get('user_intent')
    
    # 1. 구조를 짜거나 내용을 채워야 하면 generator로!
    if intent in ["RESTRUCTURE", "FILL_CONTENT"]:
        return "generator"
    
    # 2. 만약 질문이 더 필요하거나 모호하다면 (추후 질문 노드 연결용)
    # elif intent == "AMBIGUOUS":
    #     return "clarifier"
    
    # 3. 기본값은 일단 generator로 보내서 뭐라도 만들게 함
    return "generator"

def analyzer_node(state: GlobalState):
    current_blueprint = state['supervision'].get('blueprint')

    # 초기 상태 (Blueprint가 null이거나 비어있을 때)
    if not current_blueprint:
        return {
            "idea": {
                **state['idea'],
                "target_section": None 
            },
            "supervision": {
                **state['supervision'],
                "user_intent": "RESTRUCTURE", 
            }
        }

    analyzer_llm = get_mini_llm(temperature=0, max_tokens=500).bind(response_format={"type": "json_object"})
    formatted_prompt = ANALYZER_PROMPT.format(
        user_input=state['messages'][-1].content,
        blueprint=[item['title'] for item in current_blueprint]
    )

    response = analyzer_llm.invoke(formatted_prompt)
    result = json.loads(response.content)

    return {
        "idea": {
            **state['idea'],
            "target_sections": result['target_sections']
        },
        "supervision": {
            **state['supervision'],
            "user_intent": result['intent'],
        }
    }
    
def generator_node(state: GlobalState):
    system_msg = SystemMessage(content=GENERATOR_PROMPT)
    user_input = state['messages'][-1].content
    llm = get_llm(temperature=0.5, max_tokens=4000, reasoning_effort='high').bind(response_format={"type": "json_object"})
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
    현재 Blueprint: {state['supervision'].get('blueprint')}
    현재 Target Section: {state['idea'].get('target_section')}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}\n\n유저 요청: {user_input}")
    ])

    result = json.loads(response.content)
    
    return {
        "idea": {**state['idea'], "planning_style": result['planning_style'], "rationale": result['rationale'], "target_section": None, "required_data_points": result['required_data_points']},
        "supervision": {**state['supervision'], "blueprint": result['blueprint']}
    }

def evaluator_node(state: GlobalState):
    # 검수 로직  
    blueprint = state['supervision'].get('blueprint', [])
    is_valid = True # 검증 로직 결과
    
    if not is_valid:
        return {
            "supervision": {
                **state['supervision'],
                "last_decision": "REJECTED", # 다시 Generator로 보내는 신호
                "stage": "RE-GENERATION"
            }
        }

    # 검수 통과 시: 다음 단계 준비
    remaining_questions = state['idea'].get('required_data_points', [])
    
    if not remaining_questions:
        # 모든 데이터가 수집됨
        decision = "COMPLETE"
        next_stage = "FINAL_REPORT"
    else:
        # 유저의 추가 입력이 필요함
        decision = "WAIT_FOR_USER"
        next_stage = "USER_INTERACTION"

    return {
        "supervision": {
            **state['supervision'],
            "last_decision": decision,
            "stage": next_stage
        }
    }

def idea_eval_router(state: GlobalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"