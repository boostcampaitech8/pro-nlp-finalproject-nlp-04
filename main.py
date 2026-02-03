from state.base import GlobalState
from graph.supervisor_graph import supervisor_app


# 테스트
initial_state = GlobalState()
while True:
    state = supervisor_app.invoke(initial_state)

    if state.get("awaiting_input"):
        print(state["input_request"])
        user_input = input("> ")

        state["awaiting_input"] = False
        state["user_response"] = user_input
        state["messages"] = {"role": "user", "content": user_input}
        initial_state = state