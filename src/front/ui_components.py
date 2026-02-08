import streamlit as st
from graph.supervisor_graph import supervisor_app
from pathlib import Path


def init_page():
    # 페이지 설정
    st.set_page_config(page_title="Vibe Planner", layout="wide")

    # --- 커스텀 CSS 수정 버전 ---
    st.markdown("""
        <style>
        .stApp {
            height: 100vh;
            overflow: hidden;
        }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        /* 헤더 전체를 투명하게 만들고 높이 조절 */
        header {
            background-color: rgba(0,0,0,0) !important;
            border-bottom: none !important;
        }

        /* 사이드바 열기/닫기 버튼 위치 및 스타일 조정 (선택 사항) */
        /* 버튼이 너무 위에 붙어 있다면 top 값을 조절하세요 */
        [data-testid="stSidebarCollapseButton"] {
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 10px;
        }

        /* 배경 및 레이아웃 설정 (이전과 동일) */
        .stApp {
            background-color: #f0f2f5;
        }
        
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        /* 캔버스 컨테이너 스타일 */
        .canvas-container {
            background-color: white;
            padding: 60px 80px; /* 실제 종이 여백 느낌 */
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border: 1px solid #E5E7EB;
            
            /* --- 스크롤 핵심 설정 --- */
            height: calc(100vh - 100px); /* 헤더 등을 제외한 나머지 높이 전부 사용 */
            overflow-y: auto;       /* 내용이 많아지면 내부 스크롤 발생 */
            
            color: #1F2937;
            line-height: 1.8;
            word-break: keep-all;   /* 한글 줄바꿈 최적화 */
        }
        /* 스크롤바 디자인 (크롬/사파리) - 선택 사항 */
        .canvas-container::-webkit-scrollbar {
            width: 6px;
        }
        .canvas-container::-webkit-scrollbar-thumb {
            background-color: #d1d5db;
            border-radius: 10px;
        }
        .canvas-container::-webkit-scrollbar-track {
            background-color: #f9fafb;
        }
        /* 캔버스 내부 마크다운 텍스트 스타일 강제 적용 */
        .canvas-container h1, .canvas-container h2, .canvas-container h3 {
            color: #111827 !important;
            border-bottom: 2px solid #F3F4F6;
            padding-bottom: 8px;
            margin-top: 1.5em;
        }
        .canvas-container p, .canvas-container li {
            font-size: 1.05rem;
            line-height: 1.8;
            color: #374151;
        }
        /* 채팅 입력창 전체 영역 스타일 */
        [data-testid="stChatInput"] {
            border: 1px solid #D1D5DB !important; /* 채팅창 컨테이너와 동일한 선 */
            border-radius: 12px !important;       /* 모서리 곡률 통일 */
            padding: 2px !important;              /* 내부 미세 여백 */
            box-shadow: 0 -2px 10px rgba(0,0,0,0.03); /* 상단으로 살짝 퍼지는 그림자 */
        }
        /* 채팅 메시지 버블 스타일 */
        [data-testid="stChatMessage"] {
            border-radius: 12px !important;       /* 모서리 곡률 통일 */
            padding: 10px 14px !important;        /* 내부 여백 */
            background-color: white !important; /* 흰색 배경 */
        }
        </style>
    """, unsafe_allow_html=True)

def render_question_view(questions):
    idea_answers = {}

    for idx, q in enumerate(questions):
        # 질문을 감싸는 div 추가
        st.markdown(f"""
            <div class="question-card">
                <span style="color: #2563EB; font-weight: 700;">Q{idx+1}.</span>
                <span style="font-size: 1.1rem; font-weight: 600;"> {q.get('question', '질문 내용이 없습니다.')}</span>
                <p style="color: #6B7280; font-size: 0.9rem; margin-top: 4px;">{q.get('guide_text', '')}</p>
            </div>
        """, unsafe_allow_html=True)

        # 실제 입력 컨트롤은 카드 바로 아래 배치 (또는 내부 배치)
        option_labels = [opt.get("label", str(opt)) for opt in q["options"]]
        selected_label = st.radio(
            q["question"], # 질문 텍스트
            option_labels,
            captions=[opt.get("value", "") for opt in q["options"]],
            key=f"q_{idx}_radio",
            label_visibility="collapsed" # 중복 방지
        )

        selected_option = next(opt for opt in q["options"] if opt.get("label", str(opt)) == selected_label)
        user_extra = None

        if selected_option.get("value") == "user_input":
            user_extra = st.text_input("직접 입력", key=f"q_{idx}_extra", placeholder="여기에 의견을 적어주세요...")

        idea_answers[q["current_section"]] = {
            "question": q["question"],
            "selected_option": selected_label,
            "value": selected_option.get("value", "") if user_extra is None else user_extra,
        }
        st.markdown("<br>", unsafe_allow_html=True) # 간격 조절

    if st.button("✨ 기획서 생성하기"):
        st.session_state.state['user_response'] = idea_answers
        st.session_state.state = supervisor_app.invoke(st.session_state.state)

def render_plan_view():
    st.markdown('<p class="section-title">📄 Drafting Canvas</p>', unsafe_allow_html=True)

    # 1. 표시할 내용(content) 준비
    if st.session_state.state['plan']['output_path']:
        md_path = Path(st.session_state.state['plan']['output_path'])
        if md_path.exists():
            content = md_path.read_text(encoding="utf-8")
        else:
            content = "기획서를 불러오는 중 오류가 발생했습니다."
    else:
        # 기획서가 없을 때의 placeholder
        content = """
<div style="text-align: center; padding-top: 100px; color: #9ca3af;">
    <p style="font-size: 3rem;">📄</p>
    <p>기획서 초안이 이곳에 나타납니다.</p>
</div>
"""

    # 2. HTML 래퍼와 마크다운 내용을 하나로 합쳐서 한 번에 출력!
    # f-string 안에서 {content} 앞뒤로 줄바꿈(\n)을 꼭 넣어주어야 마크다운이 파싱됩니다.
    st.markdown(f"""
        <div class="canvas-container">
            
{content}  </div>
""", unsafe_allow_html=True)