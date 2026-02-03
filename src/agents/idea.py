from state.base import GlobalState


def idea_generate(state: GlobalState) -> GlobalState:
    # 실제로는 LLM 호출
    idea = {
        "planning_style": "자동 기획서 생성",
        "rationale": "기획에 시간이 오래 걸림",
        "toc": "LLM 기반 자동화",
    }
    return {"idea": idea}

def idea_evaluate(state: GlobalState) -> GlobalState:
    # 평가
    return state

def idea_eval_router(state: GlobalState) -> str:
    # 평가 결과에 따라 pass retry 결정
    return "pass"