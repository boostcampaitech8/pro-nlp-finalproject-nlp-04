"""
시각화 생성 에이전트 - 표, 다이어그램, 이미지 생성/검색
"""
from __future__ import annotations
from typing import Dict, Any

from models.llm import get_llm
from agents.plan_core.visual.schemas import Decision, VisualMeta, VisualArtifact


def render_table(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    표 생성 - 마크다운 테이블 생성
    """
    text = state.get("section_text", "")
    d = Decision(**state.get("decision", {}))
    visual_meta = state.get("visual_meta", {})
    
    # 이전 시도 피드백 확인
    feedback_text = ""
    v_result = state.get("validation_result")
    if v_result and not v_result.get("is_valid"):
        feedback_text = f"\n[이전 시도 피드백]: {v_result.get('suggestion')}\n위 피드백을 반영하여 다시 작성해줘."

    prompt = f"""
    다음 텍스트를 기반으로 '{d.table_type.value}' 스타일의 Markdown Table을 작성해줘.{feedback_text}
    
    규칙:
    - 표만 출력해. 제목(#, ##, ### 등)이나 설명 텍스트 없이 오직 표만.
    - 표는 완전하고 읽기 쉽게 작성해.
    
    내용: {text}
    """
    chat = get_llm(max_tokens=8192, reasoning_effort="low")
    response = chat.invoke(prompt)
    
    # visual_meta 업데이트
    if visual_meta:
        visual_meta["content"] = response.content
    
    state.setdefault("artifacts", {})["table"] = {
        "content": response.content,
        "type": d.table_type.value
    }
    state["visual_meta"] = visual_meta
    return state


def render_diagram(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    다이어그램 생성 - Mermaid 코드 생성
    """
    text = state.get("section_text", "")
    d = Decision(**state.get("decision", {}))
    visual_meta = state.get("visual_meta", {})
    
    # 이전 시도 피드백 확인
    feedback_text = ""
    v_result = state.get("validation_result")
    if v_result and not v_result.get("is_valid"):
        feedback_text = f"\n[이전 시도 피드백]: {v_result.get('suggestion')}\n위 피드백을 반영하여 오류를 수정해서 다시 작성해줘."

    prompt = f"""
    다음 텍스트를 기반으로 '{d.diagram_type.value}' 스타일의 Mermaid 다이어그램 코드를 작성해줘.{feedback_text}
    
    규칙:
    1. 오직 Mermaid 코드 블록만 출력해. 제목이나 설명 텍스트 없이.
    2. 마크다운 코드 블록 안에 작성해.
    3. **Syntax 중요**: 노드 라벨에 괄호()가 포함될 경우, 반드시 따옴표로 감싸거나(예: A["텍스트(괄호)"]) 괄호를 제거해. (Mermaid 구문 오류 방지)
    4. 흐름이 논리적이고 명확해야 해.
    
    내용: {text}
    """
    chat = get_llm(max_tokens=8192, reasoning_effort="low")
    response = chat.invoke(prompt)
    
    if visual_meta:
        visual_meta["content"] = response.content
    
    state.setdefault("artifacts", {})["diagram"] = {
        "content": response.content,
        "type": d.diagram_type.value
    }
    state["visual_meta"] = visual_meta
    return state


def render_chart(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    차트 생성 - Plotly를 사용하여 이미지 생성
    """
    import plotly.express as px
    import pandas as pd
    import os
    from pathlib import Path
    from agents.plan_core.visual.schemas import ChartType

    text = state.get("section_text", "")
    d = Decision(**state.get("decision", {}))
    visual_meta = state.get("visual_meta", {})
    
    # 1. 데이터 추출 (구조화된 출력 사용)
    class ChartData(BaseModel):
        title: str = Field(..., description="차트 제목")
        labels: List[str] = Field(..., description="항목 이름 리스트")
        values: List[float] = Field(..., description="수치 데이터 리스트")
        x_label: str = Field(default="항목", description="X축 이름")
        y_label: str = Field(default="수치", description="Y축 이름")

    chat = get_llm(max_tokens=8192, reasoning_effort="low")
    structured_llm = chat.with_structured_output(ChartData)

    prompt = f"""
    다음 텍스트에서 '{d.chart_type.value}' 차트를 그리기 위한 수치 데이터를 추출해줘.
    내용에 수치가 직접적으로 없더라도, 문맥상 적절한 추정치를 사용해서 차트 데이터를 만들어줘.
    
    내용: {text[:1000]}
    """
    
    try:
        data = structured_llm.invoke(prompt)
        df = pd.DataFrame({
            data.x_label: data.labels,
            data.y_label: data.values
        })

        # 2. Plotly 차트 생성
        fig = None
        if d.chart_type == ChartType.pie:
            fig = px.pie(df, names=data.x_label, values=data.y_label, title=data.title)
        elif d.chart_type == ChartType.bar:
            fig = px.bar(df, x=data.x_label, y=data.y_label, title=data.title, text_auto=True)
        elif d.chart_type == ChartType.line:
            fig = px.line(df, x=data.x_label, y=data.y_label, title=data.title, markers=True)
        else:
            # 기본값 막대 차트
            fig = px.bar(df, x=data.x_label, y=data.y_label, title=data.title)

        fig.update_layout(template="plotly_white", title_x=0.5)

        # 3. 이미지 저장
        # 프로젝트 루트 경로 찾기 (src의 상위 디렉토리)
        project_root = Path(__file__).parent.parent.parent.parent
        artifacts_dir = project_root / "output" / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        filename = f"chart_{os.urandom(4).hex()}.png"
        file_path = artifacts_dir / filename
        
        # kaleido가 설치되어 있어야 함
        fig.write_image(str(file_path))

        # 4. 메타데이터 업데이트
        if visual_meta:
            visual_meta["content"] = f"![{data.title}](artifacts/{filename})"
            visual_meta["image_path"] = str(file_path)
            visual_meta["image_url"] = None 

        state.setdefault("artifacts", {})["chart"] = {
            "path": str(file_path),
            "type": d.chart_type.value,
            "data": data.model_dump()
        }
        
    except Exception as e:
        print(f"Chart Generation Error: {e}")
        if visual_meta:
            visual_meta["placeholder"] = f"(차트 생성 실패: {str(e)})"
            
    state["visual_meta"] = visual_meta
    return state


def image_search(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    이미지 검색 - placeholder 생성 (실제 검색은 미구현)
    """
    d = Decision(**state.get("decision", {}))
    visual_meta = state.get("visual_meta", {})
    
    # 검색 쿼리가 있으면 placeholder에 포함
    queries = d.image_query or ["관련 이미지"]
    placeholder_text = f"(이미지 검색 후 삽입: {', '.join(queries)})"
    
    if visual_meta:
        visual_meta["placeholder"] = placeholder_text
        visual_meta["content"] = None  # 실제 이미지 없음
    
    state.setdefault("artifacts", {})["image_search"] = {
        "status": "placeholder",
        "queries": queries,
        "placeholder": placeholder_text
    }
    state["visual_meta"] = visual_meta
    return state


def image_gen(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    이미지 생성 - placeholder 생성 (실제 생성은 미구현)
    """
    d = Decision(**state.get("decision", {}))
    visual_meta = state.get("visual_meta", {})
    
    prompt_text = d.image_gen_prompt or "관련 이미지"
    placeholder_text = f"(이미지 생성 후 삽입: {prompt_text[:50]})"
    
    if visual_meta:
        visual_meta["placeholder"] = placeholder_text
        visual_meta["content"] = None
    
    state.setdefault("artifacts", {})["image_gen"] = {
        "status": "placeholder",
        "prompt": prompt_text,
        "placeholder": placeholder_text
    }
    state["visual_meta"] = visual_meta
    return state


def create_visual_artifact(
    section_number: str,
    state: Dict[str, Any]
) -> VisualArtifact:
    """
    상태에서 VisualArtifact 생성
    """
    visual_meta_dict = state.get("visual_meta")
    if not visual_meta_dict:
        return None
    
    meta = VisualMeta(**visual_meta_dict)
    
    # placeholder 여부 판단
    is_placeholder = meta.visual_type in ["image_search", "image_gen"] or not meta.content
    
    return VisualArtifact(
        section_number=section_number,
        meta=meta,
        is_placeholder=is_placeholder
    )
