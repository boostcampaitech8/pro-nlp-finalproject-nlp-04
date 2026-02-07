import sys
import os

# 현재 파일의 부모의 부모 폴더(src)를 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from state.idea import InternalState
from models.llm import get_mini_llm, get_llm
from prompts.idea_prompts import ANALYZER_PROMPT, CREATOR_PROMPT, UPDATER_PROMPT, QUESTIONER_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.plan_core.logger import get_logger, LogLevel

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
    logger = get_logger()
    user_input = state.get('user_response')
    
    if isinstance(user_input, dict) and any(key in user_input for key in ["selected_option", "value"]):
        result = {
            "intent": "FILL_CONTENT",
            "target_sections": list(user_input.keys()),
            "reason": "Structured JSON response detected. Bypassing LLM inference."
        }
        logger.log(LogLevel.INFO, "idea_analyzer", "Analyzer 노드 (JSON 입력 감지)", result)
        return result

    blueprint = state.get('blueprint')
    if not blueprint:
        result = {
            "target_sections": None,
            "internal_user_intent": "RESTRUCTURE", 
        }
        logger.log(LogLevel.INFO, "idea_analyzer", "Analyzer 노드 (블루프린트 없음 - RESTRUCTURE)", result)
        return result

    analyzer_llm = get_llm(temperature=0.1, max_tokens=2048, reasoning_effort='high').bind(response_format={"type": "json_object"})
    formatted_prompt = ANALYZER_PROMPT.format(
        user_input=state['user_response'],
        blueprint=[item['title'] for item in blueprint],
    )

    response = analyzer_llm.invoke(formatted_prompt)
    result = json.loads(response.content)
    
    logger.log(LogLevel.INFO, "idea_analyzer", f"Analyzer 노드 완료 (intent: {result['intent']})", {
        "intent": result['intent'],
        "target_sections": result.get('target_sections'),
        "user_input_preview": str(user_input)[:100]
    })

    return {
        "target_sections": result['target_sections'],
        "internal_user_intent": result['intent'],
    }

def creator_node(state: InternalState):
    logger = get_logger()
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
    
    # 블루프린트 생성 결과 로깅
    logger.log(LogLevel.INFO, "idea_creator", f"Creator 노드 완료 (style: {result['planning_style']})", {
        "planning_style": result['planning_style'],
        "rationale": result['rationale'][:200] if result.get('rationale') else None,
        "blueprint_count": len(result.get('blueprint', [])),
        "blueprint_titles": [b.get('title') for b in result.get('blueprint', [])]
    })
    
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
    logger = get_logger()
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
    
    # 블루프린트 업데이트 결과 로깅
    logger.log(LogLevel.INFO, "idea_updater", "Updater 노드 완료", {
        "target_sections": state.get('target_sections'),
        "blueprint_count": len(result.get('blueprint', [])),
        "blueprint_titles": [b.get('title') for b in result.get('blueprint', [])]
    })
    
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
    logger = get_logger()
    # 검수 로직  
    blueprint = state['idea'].get('blueprint', [])
    is_valid = True # 검증 로직 결과
    
    if not is_valid:
        logger.log(LogLevel.WARNING, "idea_evaluator", "Evaluator 노드: 검증 실패 (REJECTED)", {})
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
    
    # 최종 결과 로깅 (COMPLETE인 경우 블루프린트 전체 내용 로깅)
    log_data = {
        "decision": decision,
        "remaining_sections_count": len(remaining_sections),
        "total_sections": len(blueprint)
    }
    if decision == "COMPLETE":
        log_data["final_blueprint"] = blueprint
        log_data["toc"] = [section.get('title') for section in blueprint]
    
    logger.log(LogLevel.INFO, "idea_evaluator", f"Evaluator 노드 완료 (decision: {decision})", log_data)
    
    return {
        "idea":{
            **state['idea'],
            "last_decision": decision
        }
    }

def idea_eval_router(state: InternalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"