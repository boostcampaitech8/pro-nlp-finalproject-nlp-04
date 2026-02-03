from state.base import GlobalState


def research_generate(state: GlobalState) -> GlobalState:
    # 생성
    return state

def research_evaluate(state: GlobalState) -> GlobalState:
    # 평가
    return state

def research_eval_router(state: GlobalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"