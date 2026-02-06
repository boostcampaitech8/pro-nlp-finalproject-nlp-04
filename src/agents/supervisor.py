from state.base import GlobalState
from models.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage

def supervisor_node(state: GlobalState) -> GlobalState:
    if state['user_response']:
        return {
            "messages": [
                HumanMessage(content=state["user_response"])
            ],
            'awaiting_input': False,
            'user_response': None,
            'input_request': None,
            'form_request': None, # Clear form request
        }

    return {}

def ask_user(state: GlobalState) -> GlobalState:
    if state['messages']:
        response = get_llm(max_tokens=1000).invoke(state['messages'])
        return {
            "messages": [
                AIMessage(content=response.content)
            ],
            "awaiting_input": True,
            'input_request': response.content,
            'form_request': None, # Default to None
        }
    return {
        "awaiting_input": True,
        'input_request': None,
        'form_request': None,
    }

def supervisor_router(state: GlobalState):    
    return 'ask_user'