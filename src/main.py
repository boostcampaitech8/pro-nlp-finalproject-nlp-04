import streamlit as st
from graph.supervisor_graph import supervisor_app
from langchain_core.messages import HumanMessage, AIMessage
from front.ui_components import render_question_view, render_plan_view

# 페이지 설정
st.set_page_config(page_title="Vibe Planner", layout="wide")

# --- 커스텀 CSS ---
st.markdown("""
    <style>
    /* 헤더의 배경과 투명도를 조절해 배경과 일치시키기 */
    header {
        background-color: rgba(0,0,0,0) !important; /* 배경 투명하게 */
        border-bottom: none !important;
    }

    /* 메인 배경색 변경 */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #eee;
    }
    
    /* 블록 스타일 */
    .block-container {
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e0e0e0;
        min-height: 800px;
    }
    
    /* 에디터 영역 테두리 제거 및 폰트 설정 */
    .stTextArea textarea {
        border: none !important;
        font-family: 'Pretendard', sans-serif;
        font-size: 16px;
        line-height: 1.6;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

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
        chat_container = st.container(height=600, width="stretch")
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
        render_question_view(st.session_state.state['input_request'])