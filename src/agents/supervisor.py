from state.base import GlobalState


def supervisor_node(state: GlobalState) -> GlobalState:
    return state

def ask_user(state: GlobalState) -> dict:
    return {
        "awaiting_input": True,
        "input_request": "아이디어의 대상 사용자와 목적을 알려주세요."
    }

def supervisor_router(state: GlobalState):
    return 'ask_user'