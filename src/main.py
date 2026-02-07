import streamlit as st
from graph.supervisor_graph import supervisor_app
from langchain_core.messages import HumanMessage, AIMessage
from front.ui_components import init_page, render_question_view, render_plan_view

init_page()

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
        "plan": {
            "sections": [],
            "final_markdown": "",
            "output_path": "",
            "visual_artifacts": {},
        },
        "supervision": {
            "goal": "Produce a high-quality vibe-based planning document",
            "last_decision": "",
            "current_task": None,
            "reason": "",
            "pending_request": None,
            "request_type": "text",
        },
    }

# 세션 상태 초기화
if "state" not in st.session_state:
    st.session_state.state = supervisor_app.invoke(create_initial_state())

# 좌측 Sidebar (자료 영역)
with st.sidebar:
    st.title("Vibe Planner")
    st.markdown("---")

    st.subheader("📁 Research Materials")
    st.markdown("📄 Notion API Documentation")
    st.markdown("📄 Tiptap Editor Guide")
    st.markdown("📄 Vercel AI SDK")
    st.markdown("📄 React Performance Optimization")

# 메인 3단 레이아웃
center_col, right_col = st.columns([5.0, 2.8], gap="large")

# 중앙: 문서 에디터
with center_col:
    render_plan_view()

# 우측: AI Assistant
with right_col:
    # 채팅 입력이 필요한 경우
    if st.session_state.state['supervision']['request_type'] == "text":
        st.markdown('<p style="font-size: 1.2rem; font-weight: 700; color: #666;">Assistant</p>', unsafe_allow_html=True)

        # 채팅창
        chat_container = st.container(height='stretch', width="stretch", border=True)
        with chat_container:
            for msg in st.session_state.state["messages"]:
                if isinstance(msg, HumanMessage):
                    with st.chat_message("user"):
                        st.markdown(msg.content)

                elif isinstance(msg, AIMessage):
                    with st.chat_message("assistant"):
                        st.markdown(msg.content)

        # 사용자 입력
        user_input = st.chat_input("사용자 입력")
        if user_input:
            st.session_state.state["user_response"] = user_input

            # 사용자 입력 채팅창 반영
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(user_input)

                # 로딩 표시
                with st.chat_message("assistant"):
                    st.markdown("⏳ 생각 중...")
            
            # 그래프 실행
            st.session_state.state = supervisor_app.invoke(st.session_state.state)
            st.rerun()

    # 질문지 입력이 필요한 경우
    elif st.session_state.state['supervision']['request_type'] == "idea_form":
        st.markdown('<p class="section-title">💡 Vibe Questions</p>', unsafe_allow_html=True)
        
        with st.container(height=700, border=True):
            render_question_view(st.session_state.state['input_request'])