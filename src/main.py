from graph.supervisor_graph import supervisor_app


# 테스트
initial_state = {
    "messages": [],
    "awaiting_input": False,
    "input_request": None,
    "user_response": None,
    "current_task": None,
    "idea": {
        "planning_style": "",
        "rationale": "",
        "toc": [],
    },
    "supervision": {
        "last_decision": "",
    },
}

while True:
    state = supervisor_app.invoke(initial_state)
    
    if state.get("awaiting_input"):
        print(state["input_request"])
        user_input = input("> ")

        state["user_response"] = user_input
        initial_state = state