from state.base import GlobalState
from models.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from prompts.supervisor_prompt import ROUTING_PROMPT

def supervisor_node(state: GlobalState) -> GlobalState:
    if state['awaiting_input'] == True:
        # 사용자 응답이 있으면, 해당 내용을 메시지에 추가
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
    elif state['supervision']['last_decision'] not in ['ask_user', 'supervisor_node']:
        # 서브에이전트 호출 이후 사용자에게 질문 (임시)
        return {
            'supervision': {
                'last_decision': 'ask_user',
            }
        }
    else:
        # 현재 상태를 파악 후, 분기
        # 필요한 내용
        # Latest user input: {state['user_response']}
        # Latest supervisor decision: {state['supervision']['last_decision']}
        #
        #
        #
        routing_context = f'Latest user input: {state['user_response']}\nLatest supervisor decision: {state['supervision']['last_decision']}'
        response = get_llm(max_tokens=10000).invoke([
            SystemMessage(content=ROUTING_PROMPT),
            HumanMessage(content=routing_context),
            ])
        return {
            'supervision': {
                'last_decision': response.content.strip(),
            }
        }

def ask_user(state: GlobalState) -> GlobalState:
    if state['messages']:
        response = get_llm(max_tokens=1000).invoke(state['messages'])
        return {
            "messages": [
                AIMessage(content=response.content)
            ],
            "awaiting_input": True,
            'input_request': response.content,
        }
    return {
        "awaiting_input": True,
        'input_request': '안녕하세요. 기획서 작성을 도와드릴까요?',
    }

def supervisor_router(state: GlobalState) -> str:
    return state['supervision']['last_decision']