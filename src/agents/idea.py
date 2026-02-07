import sys
import os

# 현재 파일의 부모의 부모 폴더(src)를 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from state.idea import InternalState
from models.llm import get_mini_llm, get_llm
from prompts.idea_prompts import CREATOR_PROMPT, UPDATER_PROMPT, QUESTIONER_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

def idea_router(state: InternalState) -> str:
    # analyzer에서 정한 intent를 가져옴
    intent = state.get('internal_user_intent')
    
    # 새로 짜야 하는 경우
    if intent == "RESTRUCTURE":
        return "creator"
    # 부분 수정만 필요한 경우
    elif intent == "FILL_CONTENT":
        return "updater"
    
    # 기본값은 일단 다시 질문함
    return "questioner"

def analyzer_node(state: InternalState):
    user_input = state.get('user_response')
    blueprint = state.get('blueprint') or state.get('idea', {}).get('blueprint')
    
    if isinstance(user_input, dict) and blueprint:
        return {
            "internal_user_intent": "FILL_CONTENT",
            "target_sections": list(user_input.keys()),
        }
    elif not blueprint:
        return {
            "internal_user_intent": "RESTRUCTURE", 
            "target_sections": None,
        }
    # else: #혹시 모를 예외 케이스: blueprint는 있는데 자연어가 들어온 경우
    #     return {
    #         "internal_user_intent": "RESTRUCTURE", 
    #         "target_sections": None,
    #     }


def creator_node(state: InternalState):
    system_msg = SystemMessage(content=CREATOR_PROMPT)
    user_input = state['user_response']
    llm = get_llm(temperature=0.3, max_tokens=5000, reasoning_effort='high').bind(response_format={"type": "json_object"})
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
    blueprint: {state['idea'].get('blueprint') or []}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}\n\n유저 요청: {user_input}")
    ])

    result = json.loads(response.content)
    
    return {
        "idea":
            {   
                **state['idea'],
                "planning_style": result['planning_style'], 
                "rationale": result['rationale'],
                "blueprint": result['blueprint'],   
            },
        "target_sections": None,
    }
    
def updater_node(state: InternalState):
    system_msg = SystemMessage(content=UPDATER_PROMPT)
    user_input = state['user_response']
    llm = get_llm(temperature=0.5, max_tokens=5000, reasoning_effort='high').bind(response_format={"type": "json_object"})
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
    blueprint: {state['idea'].get('blueprint')}
    required_data_points : {state.get('required_data_points', '')}
    target_sections: {state.get('target_sections')}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}\n\n유저 요청: {user_input}")
    ])

    result = json.loads(response.content)
    
    return {
        "idea":{
            **state['idea'],
            "blueprint": result['blueprint']
        },
        "target_sections": None,
        "required_data_points": None,
    }

def questioner_node(state: InternalState):
    system_msg = SystemMessage(content=QUESTIONER_PROMPT)
    llm = get_mini_llm(temperature=0.5, max_tokens=4000).bind(response_format={"type": "json_object"})

    intent = state.get("internal_user_intent")
    # 의도가 불분명한 경우 (AMBIGUOUS)
    if intent == "AMBIGUOUS":
        # AI가 유저에게 다시 물어보는 프롬프트 생성
        response = llm.invoke(f"유저의 입력 '{state['user_input']}'이 모호합니다. 어떤 섹션을 수정하고 싶은지, 혹은 무엇을 도와드리면 될지 친절하게 되물어주세요.")
        return {
            "idea": {
                **state["idea"], 
                "last_decision": "WAIT_FOR_USER", 
                "messages": response.content
            }
        }
    
    
    blueprint = state['idea'].get('blueprint')
    not_completed_count = len([s for s in blueprint if s['is_required_from_user']])

    if not_completed_count == 0:
        # 더 이상 물어볼 게 없다면는 경우
        return {
            "idea": {
                **state["idea"],
                "messages": "모든 기획 섹션이 완료되었습니다! 최종 검토를 시작합니다.",
            },
            "internal_user_intent": "CONFIRM"
        }
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
    blueprint: {blueprint}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}")
    ])
    result = json.loads(response.content)
    
    return {
        "idea":{
            **state['idea'],
            "form": result.get("forms", [])
        },
        "required_data_points": result.get("forms", [])
    }

def evaluator_node(state: InternalState):
    # 검수 로직  
    blueprint = state['idea'].get('blueprint', [])
    is_valid = True # 검증 로직 결과
    
    if not is_valid:
        return {
            "idea": {
                **state['idea'],
                "last_decision": "REJECTED", 
            }
        }

    # 검수 통과 시: 다음 단계 준비
    remaining_sections = [s for s in blueprint if s.get('is_required_from_user') == True]
    
    if not remaining_sections:
        # 모든 데이터가 수집됨
        decision = "COMPLETE"
        state["idea"]["toc"] = [section.get('title') for section in blueprint]
    else:
        # 유저의 추가 입력이 필요함
        decision = "WAIT_FOR_USER"
    return {
        "idea":{
            **state['idea'],
            "last_decision": decision
        }
    }

def idea_eval_router(state: InternalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"