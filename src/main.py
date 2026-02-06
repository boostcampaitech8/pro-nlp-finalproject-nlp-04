from graph.supervisor_graph import supervisor_app


# 테스트
initial_state = {
    "messages": [],
    "awaiting_input": False,
    "input_request": None,
    "user_response": None,
    "idea": {
        "planning_style": "",
        "rationale": "",
        "toc": [],
        "blueprint": [],
        "last_decision": "",
        "messages": "",
    },
    "supervision": {
        "goal": "Produce a high-quality vibe-based planning document",
        "last_decision": "",
        "current_task": None,
        "reason": "",
        "pending_request": None,
    },
}

while True:
    state = supervisor_app.invoke(initial_state)
    
    if state.get("awaiting_input"):
        print(state["input_request"])
        user_input = input("> ")

        state["user_response"] = user_input
        initial_state = state