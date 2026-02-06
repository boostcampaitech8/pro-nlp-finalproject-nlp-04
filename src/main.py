import streamlit as st
from graph.supervisor_graph import supervisor_app


# 초기 상태 생성 함수
def create_initial_state():
    return {
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

# 세션 상태 초기화
if "state" not in st.session_state:
    st.session_state.state = supervisor_app.invoke(create_initial_state())

st.title("Vibe Planning Assistant")

# 메시지 출력
st.subheader("Conversation")
if st.session_state.state["messages"]:
    for message in st.session_state.state["messages"]:
        st.info(message.content)

# 사용자 입력
user_input = st.chat_input("답변 입력")
if user_input:
    st.info(user_input)
    st.session_state.state["user_response"] = user_input
    
    # 그래프 실행
    st.session_state.state = supervisor_app.invoke(st.session_state.state)
    st.rerun()