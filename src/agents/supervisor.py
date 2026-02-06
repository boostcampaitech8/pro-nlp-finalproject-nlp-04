from state.base import GlobalState
from models.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from prompts.supervisor_prompt import ROUTING_PROMPT

def supervisor_node(state: GlobalState) -> GlobalState:
    # 사용자 응답이 있으면, 해당 내용을 메시지에 추가
    if state['awaiting_input'] == True:
        return {
            "messages": [
                HumanMessage(content=state["user_response"])
            ],
            'awaiting_input': False,
            'input_request': None,
            'supervision': {
                'last_decision': 'supervisor_node',
            }
        }

    # 초기 상태
    if state['supervision']['last_decision'] == '':
        return {
            'input_request': '안녕하세요. 기획서 작성을 도와드릴까요?',
            'supervision': {
                'last_decision': 'ask_user',
            }
        }
    # 서브에이전트 호출 이후 (TODO)
    elif state['supervision']['last_decision'] not in ['ask_user', 'supervisor_node']:
        last_decision = state['supervision']['last_decision']

        # 아이디어 에이전트 호출 이후
        if last_decision == 'invoke_idea':
            # 유저의 추가 입력이 필요한 경우
            if state['idea']['last_decision'] == 'WAIT_FOR_USER':
                return {
                    'input_request': state['idea']['messages'],
                    'supervision': {
                        'last_decision': 'ask_user',
                    }
            }
            # 아이디어 에이전트 컨펌
            elif state['idea']['last_decision'] == 'CONFIRM':
                return {
                    'supervision': {
                        'last_decision': 'invoke_plan',
                    }
                }
        elif last_decision == 'invoke_plan':
            # TODO
            return {
                'supervision': {
                    'last_decision': 'ask_user',
                }
            }
        elif last_decision == 'invoke_research':
            # TODO
            return {
                'supervision': {
                    'last_decision': 'ask_user',
                }
            }
    # 사용자 응답과 현재 상태를 파악 후, 분기 (TODO)
    # 필요한 내용
    # 1. 사용자 응답
    # 2. 진행 상황
    # 3. 
    # 
    else:
        # 임시로 invoke_idea로 설정 (TODO)
        # routing_context = f'Latest user input: {state['user_response']}'
        # response = get_llm(max_tokens=10000).invoke([
        #     SystemMessage(content=ROUTING_PROMPT),
        #     HumanMessage(content=routing_context),
        #     ])
        return {
            'supervision': {
                'last_decision': 'invoke_idea',#response.content.strip(),
            }
        }

def ask_user(state: GlobalState) -> GlobalState:
    # 에이전트가 사용자에게 전달할 내용이 있을 시
    if state['input_request']:
        return {
            "messages": [
                AIMessage(content=state['input_request'])
            ],
            "awaiting_input": True,
        }
    # 에이전트가 사용자에게 전달할 내용이 없을 시 (TODO)
    else:
        response = get_llm(max_tokens=1000).invoke(state['messages'])
        return {
            "messages": [
                AIMessage(content=response.content)
            ],
            "awaiting_input": True,
            'input_request': response.content,
        }

def supervisor_router(state: GlobalState) -> str:
    return state['supervision']['last_decision']