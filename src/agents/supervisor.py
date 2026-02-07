from state.base import GlobalState
from models.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from prompts.supervisor_prompt import ROUTING_PROMPT, MESSAGE_SUMMARY_PROMPT, SUPERVISOR_CHAT_PROMPT
from langchain_core.output_parsers import JsonOutputParser

def supervisor_node(state: GlobalState) -> GlobalState:
    # 사용자 응답이 있으면, 해당 내용을 메시지에 추가
    if state['awaiting_input'] == True:
        if state['supervision']['request_type'] == 'text':
            return {
                "messages": [
                    HumanMessage(content=state["user_response"])
                ],
                'awaiting_input': False,
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'supervisor_node',
                }
            }
        elif state['supervision']['request_type'] == 'idea_form':
            return {
                'awaiting_input': False,
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'RUN_IDEA_STRUCTURING',
                    'request_type': 'text',
                }
            }

    # 초기 상태
    if state['supervision']['last_decision'] == '':
        return {
            'supervision': {
                **state['supervision'],
                'last_decision': 'ASK_USER',
                'current_task': 'idea_structuring',
                'pending_request': '안녕하세요. 기획서 작성을 도와드릴까요?',
            }
        }
    # 서브에이전트 호출 이후
    elif state['supervision']['last_decision'] not in ['ASK_USER', 'supervisor_node']:
        last_decision = state['supervision']['last_decision']

        # 아이디어 에이전트 호출 이후
        if last_decision == 'RUN_IDEA_STRUCTURING':
            # 유저의 추가 입력이 필요한 경우 (질문지 처리 필요)
            if state['idea']['last_decision'] == 'WAIT_FOR_USER':
                return {
                    'supervision': {
                        **state['supervision'],
                        'last_decision': 'ASK_USER',
                        'current_task': 'idea_structuring',
                        'pending_request': state['idea']['form'],
                        'request_type': 'idea_form',
                    }
            }
            # 아이디어 에이전트 컨펌 or 완료
            elif state['idea']['last_decision'] in ['CONFIRM', 'COMPLETE']:
                return {
                    'completed_steps': 'idea_structuring',
                    'supervision': {
                        **state['supervision'],
                        'last_decision': 'RUN_PLANNING',
                        'current_task': 'planning',
                    }
                }
        elif last_decision == 'RUN_PLANNING':
            return {
                'completed_steps': 'planning',
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'ASK_USER',
                    'current_task': 'planning',
                    'pending_request': '기획서 작성이 완료되었습니다. 추가 수정이 필요하신 부분을 알려주세요.',
                    'request_type': 'text',
                }
            }
        elif last_decision == 'RUN_RESEARCH':
            # TODO
            return {
                'supervision': {
                    **state['supervision'],
                    'last_decision': 'ASK_USER',
                }
            }
    # 사용자 응답과 현재 상태를 파악 후, 분기
    else:
        routing_context = summary_state(state)
        response = get_llm(max_tokens=10000).invoke([
            SystemMessage(content=ROUTING_PROMPT),
            HumanMessage(content=routing_context),
            ])
        response_json = JsonOutputParser().parse(response.content)
        return {
            'supervision': {
                **state['supervision'],
                'last_decision': response_json['next_action'],
                'current_task': response_json['next_action'],
                'reason': response_json['reason'],
                'summary': routing_context,
            }
        }

def summarize_messages(messages: list[BaseMessage]) -> str:
    if not messages:
        return ""

    joined_msgs = "대화 내용:\n- " + "\n- ".join([f"{m.type}: {m.content}" for m in messages])

    result = get_llm(max_tokens=5000).invoke([SystemMessage(content=MESSAGE_SUMMARY_PROMPT), HumanMessage(content=joined_msgs)])
    return result.content.strip()

def prepare_idea_structuring(state: GlobalState) -> GlobalState:
    user_msgs = [m for m in state['messages'] if isinstance(m, HumanMessage) and m.content]
    user_idea = summarize_messages(user_msgs)
    return {
        'user_response': user_idea,
    }

def ask_user(state: GlobalState) -> GlobalState:
    # 다른 에이전트가 사용자에게 전달할 내용이 있을 시
    if state['supervision']['pending_request']:
        if state['supervision']['request_type'] == 'text':
            return {
                'supervision': {
                    **state['supervision'],
                    'pending_request': None,
                },
                "messages": [
                    AIMessage(content=state['supervision']['pending_request'])
                ],
                'input_request': state['supervision']['pending_request'],
                "awaiting_input": True,
            }
        elif state['supervision']['request_type'] == 'idea_form':
            return {
                'supervision': {
                    **state['supervision'],
                    'pending_request': None,
                },
                'input_request': state['supervision']['pending_request'],
                "awaiting_input": True,
            }
    # 수퍼바이저와 사용자와의 대화시
    else:
        # 현재 상태와 메시지 기록을 바탕으로 생성된 응답을 사용자에게 전달
        response = get_llm(max_tokens=10000).invoke([SystemMessage(content=SUPERVISOR_CHAT_PROMPT), HumanMessage(content=state['supervision']['summary'])])
        return {
            "messages": [
                AIMessage(content=response.content)
            ],
            'input_request': response.content,
            "awaiting_input": True,
        }

def supervisor_router(state: GlobalState) -> str:
    return state['supervision']['last_decision']


# 필요한 내용
# 1. goal
# 2. completed_steps
# 3. current_outputs
# 4. missing_information
# 5. known_constraints
# 6. last_user_input
# 7. message_history
# 8. confidence_levels (if provided)
def summary_state(state: GlobalState) -> str:
    completed_steps = state['completed_steps']

    current_outputs = {}
    if "idea" in state:
        current_outputs["idea_structuring"] = [
            f"{section['title']}: {section['guideline']}"
            for section in state["idea"].get("blueprint", [])
            if section.get("is_required_from_user") == False
        ]
    
    if "plan" in state:
        current_outputs["planning"] = state["plan"].get("final_markdown", "")
    
    required_info = [section.get('title') for section in state['idea']['blueprint']]
    
    filled_info = [section.get('title') for section in state['idea']['blueprint'] if section.get('is_required_from_user') == False]
    missing_information = [title for title in required_info if title not in filled_info]

    message_history = summarize_messages(state["messages"])
    
    return f'''
        Goal: {state['supervision']['goal']}
        Completed steps: {completed_steps}
        Current task: {state['supervision']['current_task']}
        Current outputs: {current_outputs}
        Required information: {required_info}
        Missing information: {missing_information}
        Message history: {message_history}
        Last user input: {state['user_response']}
        '''
        # Confidence levels: {state['supervision']['confidence_levels']}