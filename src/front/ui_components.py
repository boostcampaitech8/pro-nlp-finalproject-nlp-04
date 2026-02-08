import streamlit as st
from graph.supervisor_graph import supervisor_app
from pathlib import Path
import re
import streamlit.components.v1 as components

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
        st.session_state.phase = 'form_response'
        st.rerun()

def st_mermaid(code: str):
    components.html(
        f"""
        <style>
            body {{
                margin: 0;
                padding: 0;
            }}

            .mermaid-wrapper {{
                display: flex;
                justify-content: center;   /* 가로 중앙 */
                align-items: center;       /* 세로 중앙 */
                width: 100%;
            }}

            .mermaid svg {{
                max-width: 100%;
                height: auto;
            }}
        </style>
        <div class="mermaid-wrapper">
            <div class="mermaid">
                {code}
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({{
                startOnLoad: true,
                theme: "default"
            }});
        </script>
        """,
        height=400,
        scrolling=True,
    )


def extract_heading_line_map(markdown: str):
    """
    return:
    {
        "h1-3": {
            "level": 1,
            "title": "기능 개요",
            "line": 12
        },
        ...
    }
    """
    heading_map = {}
    lines = markdown.splitlines()

    h1_count = 0
    h2_count = 0

    for idx, line in enumerate(lines):
        if line.startswith("# "):
            h1_count += 1
            key = f"h1-{h1_count}"
            heading_map[key] = {
                "level": 1,
                "title": line[2:].strip(),
                "line": idx,   # ✅ 0-based line number
            }

        elif line.startswith("## "):
            h2_count += 1
            key = f"h2-{h2_count}"
            heading_map[key] = {
                "level": 2,
                "title": line[3:].strip(),
                "line": idx,
            }

    return heading_map


def _render_text_and_images(text: str):
    parts = re.split(r"!\[(.*?)\]\((.*?)\)", text)
    for i, part in enumerate(parts):
        if i % 3 == 0:
            if part.strip():
                st.markdown(part)
        elif i % 3 == 1:
            title = part # 이미지 제목, 필요시 caption으로 사용
        else:
            st.image(part)


def render_heading(level: int, text: str, key: str):
    is_active = st.session_state.get("active_heading") == key
    heading_map = st.session_state.get("heading_line_map", {})

    def activate():
        if is_active:
            st.session_state["active_heading"] = None
        else:
            st.session_state["active_heading"] = key

    with st.container():
        cols = st.columns([0.85, 0.15])

        with cols[0]:
            st.markdown(f"{'#' * level} {text}")

        with cols[1]:
            st.button("", key=f"btn-{key}", icon="✏️", on_click=activate)

        # 👉 버튼 바로 아래에 입력창 렌더
        if is_active:
            user_input = st.text_area(
                "이 섹션에 대한 지시",
                key=f"input-{key}",
                placeholder="이 섹션에 대한 지시를 입력하세요",
            )
            if st.button("적용", key=f"apply-{key}"):
                meta = heading_map.get(key)

                st.session_state.state['user_response'] = user_input
                st.session_state.state['supervision']['edit_request'] = {
                    'require_edit': True,
                    'target_section_id': meta['title'],
                    "instruction": user_input,
                    "granularity": "section",
                    "edit_range_start": meta["line"] if meta else 0,
                }

                st.session_state["active_heading"] = None
                st.session_state.phase = 'edit'
                st.rerun()


def _render_text_images_and_headings(text: str, h1_key_idx: int, h2_key_idx: int):
    lines = text.splitlines()
    buffer = []

    def flush():
        if buffer:
            _render_text_and_images("\n".join(buffer))
            buffer.clear()

    for idx, line in enumerate(lines):
        if line.startswith("# "):
            flush()
            render_heading(1, line[2:].strip(), f"h1-{h1_key_idx}")
            h1_key_idx += 1
        elif line.startswith("## "):
            flush()
            render_heading(2, line[3:].strip(), f"h2-{h2_key_idx}")
            h2_key_idx += 1
        else:
            buffer.append(line)

    flush()

    return h1_key_idx, h2_key_idx


def parse_markdown_blocks(markdown_string: str):
    lines = markdown_string.splitlines()
    blocks = []

    buffer = []
    in_mermaid = False
    mermaid_lines = []

    def flush_text():
        if buffer:
            blocks.append({
                "type": "text",
                "content": "\n".join(buffer)
            })
            buffer.clear()

    for line in lines:
        if line.strip().startswith("```mermaid"):
            flush_text()
            in_mermaid = True
            mermaid_lines.clear()
            continue

        if in_mermaid:
            if line.strip().startswith("```"):
                blocks.append({
                    "type": "mermaid",
                    "content": "\n".join(mermaid_lines)
                })
                in_mermaid = False
            else:
                mermaid_lines.append(line)
            continue

        buffer.append(line)

    flush_text()
    return blocks

# md에서 머메이드와 그 외를 분류 하여 순서대로 저장해두고, 한번에 렌더링
def st_markdown(markdown_string: str):
    blocks = parse_markdown_blocks(markdown_string)
    h1_key_idx = 1
    h2_key_idx = 1

    for block in blocks:
        if block["type"] == "mermaid":
            st_mermaid(block["content"])
        else:
            h1_key_idx, h2_key_idx = _render_text_images_and_headings(block["content"], h1_key_idx, h2_key_idx)


def render_plan_view():
    st.markdown('<p class="section-title">📄 Drafting Canvas</p>', unsafe_allow_html=True)
    
    with st.container(height=700, border=True):
        # 1. 표시할 내용(content) 준비
        if st.session_state.state['plan']['output_path']:
            md_path = Path(st.session_state.state['plan']['output_path'])
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                st.session_state["heading_line_map"] = extract_heading_line_map(content)
            else:
                content = "기획서를 불러오는 중 오류가 발생했습니다."
            st_markdown(content)
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