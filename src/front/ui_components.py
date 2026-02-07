import streamlit as st
from graph.supervisor_graph import supervisor_app
from pathlib import Path

def render_question_view(questions):
    st.markdown('<p style="font-size: 1.2rem; font-weight: 700; color: #666;">Question</p>', unsafe_allow_html=True)

    idea_answers = {}

    for idx, q in enumerate(questions):
        section_key = f"section_{idx}"

        with st.container(border=True):
            st.subheader(q["current_section"])
            st.caption(q["guide_text"])

            st.write(q["question"])

            # 옵션 라벨 리스트 생성
            option_labels = [opt["label"] for opt in q["options"]]

            selected_label = st.radio(
                "옵션 선택",
                option_labels,
                key=f"{section_key}_radio"
            )

            # 선택된 옵션 찾기
            selected_option = next(
                opt for opt in q["options"] if opt["label"] == selected_label
            )

            user_extra = None

            # 기타 선택 시 추가 입력
            if selected_option["value"] == "user_input":
                user_extra = st.text_input(
                    "추가 설명 입력",
                    key=f"{section_key}_extra"
                )

            # 결과 저장
            idea_answers[q["current_section"]] = {
                "selected_option": selected_label,
                "value": selected_option["value"] if user_extra == None else user_extra,
            }

    # 제출 버튼
    if st.button("제출"):
        st.session_state.state['user_response'] = idea_answers
        st.session_state.state = supervisor_app.invoke(st.session_state.state)
        st.rerun()

def render_plan_view():
    st.markdown('<p style="font-size: 1.2rem; font-weight: 700; color: #666;">Drafting Canvas</p>', unsafe_allow_html=True)

    if st.session_state.state['plan']['output_path']:
        md_path = Path(st.session_state.state['plan']['output_path'])
        if md_path.exists():
            content = md_path.read_text(encoding="utf-8")
            st.markdown(content)
    else:
        st.info("기획서가 아직 생성되지 않았습니다.")