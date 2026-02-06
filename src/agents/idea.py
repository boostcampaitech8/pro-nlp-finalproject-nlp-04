import sys
import os

# 현재 파일의 부모의 부모 폴더(src)를 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from state.idea import InternalState
from models.llm import get_mini_llm, get_llm
from prompts.idea_prompts import ANALYZER_PROMPT, CREATOR_PROMPT, UPDATER_PROMPT, QUESTIONER_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

def idea_router(state: InternalState) -> str:
    # analyzer에서 정한 intent를 가져옴
    intent = state.get('internal_user_intent')
    
    # 새로 짜야 하는 경우
    if intent in "RESTRUCTURE":
        return "creator"
    # 부분 수정만 필요한 경우
    elif intent in "FILL_CONTENT":
        return "updater"
    # 만약 질문이 더 필요하거나 모호하다면
    elif intent == "AMBIGUOUS":
        return "questioner"
    # 사용자가 현재 구조에 만족할 경우
    elif intent == "CONFIRM":
        return "evaluator"
    
    # 기본값은 일단 다시 질문함
    return "questioner"

def analyzer_node(state: InternalState):
    current_question = state.get("required_data_points")
    if current_question:
        # 질문이 있을 때는 실제 내용을 넣음
        q_context = f"현재 진행 중인 질문: {current_question}"
    else:
        # 질문이 없을 때는 AI가 헷갈리지 않게 명시
        q_context = "현재 진행 중인 질문 없음 (사용자의 일반적인 요청으로 처리할 것)"

    blueprint = state.get('blueprint')
    if not blueprint:
        return {
            "target_sections": None,
            "internal_user_intent": "RESTRUCTURE", 
        }

    analyzer_llm = get_llm(temperature=0.1, max_tokens=2048, reasoning_effort='high').bind(response_format={"type": "json_object"})
    formatted_prompt = ANALYZER_PROMPT.format(
        user_input=state['messages'][-1].content,
        blueprint=[item['title'] for item in blueprint],
        required_data_points=q_context
    )

    response = analyzer_llm.invoke(formatted_prompt)
    result = json.loads(response.content)

    return {
        "target_sections": result['target_sections'],
        "internal_user_intent": result['intent'],
    }

def creator_node(state: InternalState):
    system_msg = SystemMessage(content=CREATOR_PROMPT)
    user_input = state['messages'][-1].content
    llm = get_llm(temperature=0.3, max_tokens=5000, reasoning_effort='high').bind(response_format={"type": "json_object"})
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
<<<<<<< HEAD
    blueprint: {state.get('blueprint') or []}
=======
    blueprint: {state['idea'].get('blueprint') or []}
>>>>>>> main
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}\n\n유저 요청: {user_input}")
    ])

    result = json.loads(response.content)
    
    return {
<<<<<<< HEAD
        "idea": {**state['idea'], 
                 "planning_style": result['planning_style'], 
                 "rationale": result['rationale']
                 },
        "target_sections": None,
        "blueprint": result['blueprint']
=======
        "idea":
            {   
                **state['idea'],
                "planning_style": result['planning_style'], 
                "rationale": result['rationale'],
                "blueprint": result['blueprint'],   
            },
        "target_sections": None,
>>>>>>> main
    }
    
def updater_node(state: InternalState):
    system_msg = SystemMessage(content=UPDATER_PROMPT)
    user_input = state['messages'][-1].content
    llm = get_llm(temperature=0.5, max_tokens=5000, reasoning_effort='high').bind(response_format={"type": "json_object"})
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
<<<<<<< HEAD
    blueprint: {state.get('blueprint')}
=======
    blueprint: {state['idea'].get('blueprint')}
>>>>>>> main
    required_data_points : {state.get('required_data_points', '')}
    target_sections: {state.get('target_sections')}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}\n\n유저 요청: {user_input}")
    ])

    result = json.loads(response.content)
    
    return {
<<<<<<< HEAD
        "target_sections": None,
        "required_data_points": None,
        "blueprint": result['blueprint']
=======
        "idea":{
            **state['idea'],
            "blueprint": result['blueprint']
        },
        "target_sections": None,
        "required_data_points": None,
>>>>>>> main
    }

def questioner_node(state: InternalState):
    system_msg = SystemMessage(content=QUESTIONER_PROMPT)
    llm = get_mini_llm(temperature=0.3, max_tokens=1000)

    intent = state.get("internal_user_intent")
    # 의도가 불분명한 경우 (AMBIGUOUS)
    if intent == "AMBIGUOUS":
        # AI가 유저에게 다시 물어보는 프롬프트 생성
        response = llm.invoke(f"유저의 입력 '{state['user_input']}'이 모호합니다. 어떤 섹션을 수정하고 싶은지, 혹은 무엇을 도와드리면 될지 친절하게 되물어주세요.")
        return {
<<<<<<< HEAD
            "messages": [response],
            "supervision": {**state["supervision"], "last_decision": "WAIT_FOR_USER"}
        }
    
    
    blueprint = state.get('blueprint')
=======
            "idea": {
                **state["idea"], 
                "last_decision": "WAIT_FOR_USER", 
                "messages": response.content
            }
        }
    
    
    blueprint = state['idea'].get('blueprint')
>>>>>>> main
    not_completed_count = len([s for s in blueprint if s['is_required_from_user']])

    if not_completed_count == 0:
        # 더 이상 물어볼 게 없다면는 경우
        return {
<<<<<<< HEAD
            "messages": [AIMessage(content="모든 기획 섹션이 완료되었습니다! 최종 검토를 시작합니다.")],
            "supervision": {**state['supervision'], "internal_user_intent": "CONFIRM"} 
=======
            "idea": {
                **state["idea"],
                "messages": "모든 기획 섹션이 완료되었습니다! 최종 검토를 시작합니다.",
            },
            "internal_user_intent": "CONFIRM"
>>>>>>> main
        }
    
    # 현재 상황(Context)을 LLM이 알기 쉽게 정리
    context_info = f"""
    blueprint: {blueprint}
    current_status: {not_completed_count}
    """

    response = llm.invoke([
        system_msg,
        HumanMessage(content=f"{context_info}")
    ])
    question_content = response.content
    
    return {
<<<<<<< HEAD
        "messages": [response],
        "required_data_points": question_content
        
=======
        "idea":{
            **state['idea'],
            "messages": question_content,
        },
        "required_data_points": question_content
>>>>>>> main
    }

def evaluator_node(state: InternalState):
    # 검수 로직  
<<<<<<< HEAD
    blueprint = state['supervision'].get('blueprint', [])
=======
    blueprint = state['idea'].get('blueprint', [])
>>>>>>> main
    is_valid = True # 검증 로직 결과
    
    if not is_valid:
        return {
<<<<<<< HEAD
            "supervision": {
                **state['supervision'],
=======
            "idea": {
                **state['idea'],
>>>>>>> main
                "last_decision": "REJECTED", 
            }
        }

    # 검수 통과 시: 다음 단계 준비
    remaining_questions = state.get('required_data_points', [])
    
    if not remaining_questions:
        # 모든 데이터가 수집됨
        decision = "COMPLETE"
<<<<<<< HEAD
        state["idea"]["toc"] = [section.get('title') for section in state["supervision"]["blueprint"]]
    else:
        # 유저의 추가 입력이 필요함
        decision = "WAIT_FOR_USER"

    return {
        "blueprint": state["blueprint"],
        "idea": state["idea"],
        "messages": state["messages"],
        "last_decision": decision
=======
        state["idea"]["toc"] = [section.get('title') for section in blueprint]
    else:
        # 유저의 추가 입력이 필요함
        decision = "WAIT_FOR_USER"
    return {
        "idea":{
            **state['idea'],
            "last_decision": decision
        }
>>>>>>> main
    }

def idea_eval_router(state: InternalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"