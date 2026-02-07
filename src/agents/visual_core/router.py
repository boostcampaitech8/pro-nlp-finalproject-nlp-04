"""
시각화 결정 라우터 - 섹션 내용을 분석하여 필요한 시각화 유형 결정
"""
from __future__ import annotations
from typing import Any, Dict, TypedDict

from models.llm import get_llm
from agents.visual_core.schemas import Decision, VisualMeta
from agents.plan_core.logger import get_logger, LogLevel


class RouterState(TypedDict, total=False):
    section_id: str
    section_title: str
    section_text: str
    rule_hints: Dict[str, Any]
    decision: Dict[str, Any]
    visual_meta: Dict[str, Any]
    artifacts: Dict[str, Any]


def decide_node(state: RouterState) -> RouterState:
    """
    Solar Pro 2 LLM을 사용하여 시각화 필요성 판단
    """
    text = state.get("section_text") or ""
    title = state.get("section_title") or ""
    
    
    # LLM 호출, 라우팅은 빠른 판단을 위해 low 사용
    chat = get_llm(max_tokens=8192, reasoning_effort="low")
    structured_llm = chat.with_structured_output(Decision)
    
    prompt_text = f"""
    당신은 기획서 작성 도우미의 두뇌 역할을 하는 Router입니다.
    사용자가 작성한 기획서의 '섹션 제목'과 '내용'을 보고, 
    이 내용을 시각화하기 위해 표(Table), 다이어그램(Diagram), 차트(Chart), 이미지 검색(Search), 이미지 생성(Gen) 
    중 어떤 도구가 필요한지 판단하세요.

    [입력 정보]
    - 섹션 제목: {title}
    - 섹션 텍스트: {text}

    [판단 기준]
    1. Table: 정형 데이터, 비교, 요금표, 로드맵, 지표 등이 포함되면 True.
    2. Diagram: 구조, 흐름, 순서, 관계 등이 텍스트로 설명되어 있어 시각화가 좋으면 True (Mermaid 사용).
    3. Chart: 수치 데이터의 비중, 시간 흐름, 항목 간 수치 비교 등이 명확하여 시각적 그래프가 필요하면 True (Plotly 사용).
       - 반드시 chart_type(pie, bar, line, scatter) 중 하나를 선택하세요.
    4. Image Search: UI 참고, 레퍼런스, 실제 사례 이미지를 보고 싶어하면 True.
    5. Image Gen: "그려줘", "생성해줘", "일러스트" 등 없는 이미지를 만들어야 하면 True.

    필요한 도구와 그 구체적인 타입(table_type, diagram_type, chart_type)을 결정하고, 
    검색이나 생성이 필요하다면 쿼리/프롬프트도 제안하세요.
    차트와 표가 동시에 필요해 보인다면, 더 직관적인 'Chart'를 우선적으로 선택하세요.
    """
    
    try:
        decision = structured_llm.invoke(prompt_text)
    except Exception as e:
        print(f"LLM Error: {e}")
        decision = Decision(reason=f"Error: {str(e)}")

    if decision is None:
        decision = Decision(reason="LLM returned None")

    state["decision"] = decision.model_dump()
    return state


def generate_visual_meta(state: RouterState) -> RouterState:
    """
    시각화가 필요한 경우, 왜 필요한지 메타데이터 생성
    """
    decision = Decision(**state.get("decision", {}))
    text = state.get("section_text", "")
    title = state.get("section_title", "")
    
    if not any([decision.needs_table, decision.needs_diagram, decision.needs_chart,
                decision.needs_image_search, decision.needs_image_gen]):
        state["visual_meta"] = None
        return state
    
    # 시각화 타입 결정
    if decision.needs_table:
        visual_type = "table"
    elif decision.needs_diagram:
        visual_type = "diagram"
    elif decision.needs_image_search:
        visual_type = "image_search"
    else:
        visual_type = "image_gen"
    
    # LLM으로 메타데이터 생성
    prompt = f"""
    다음 섹션에 '{visual_type}' 시각화가 필요합니다.
    
    섹션 제목: {title}
    섹션 내용: {text[:500]}
    
    다음 정보를 JSON 형식으로 제공해주세요:
    1. purpose: 이 시각화가 왜 필요한지 (예: "가격 변동 추이를 직관적으로 비교하기 위해")
    2. why_this_format: 왜 이 형식(표/다이어그램/이미지)인지 (예: "정형 데이터 비교에는 표가 가장 효과적")
    3. data_source: 데이터 출처가 있다면 (예: "시장 조사 자료 기반")
    
    JSON만 출력하세요.
    """
    
    try:
        # 메타데이터 생성은 명확성이 중요하므로 medium 사용
        chat = get_llm(max_tokens=8192, reasoning_effort="medium")
        response = chat.invoke(prompt)
        import json
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        meta_data = json.loads(content)
        
        # [Fix] LLM이 리스트를 반환하는 경우 처리
        if isinstance(meta_data, list):
            if len(meta_data) > 0 and isinstance(meta_data[0], dict):
                meta_data = meta_data[0]
            else:
                raise ValueError("LLM returned a list without valid dict items")
                
    except Exception as e:
        print(f"[VisualRouter] Meta generation error: {e}")
        meta_data = {
            "purpose": f"{title} 내용을 시각적으로 표현",
            "why_this_format": f"{visual_type} 형식이 이 내용에 적합",
            "data_source": ""
        }
    
    # placeholder 생성
    placeholder_map = {
        "table": "(표 생성 후 삽입)",
        "diagram": "(다이어그램 생성 후 삽입)",
        "image_search": "(이미지 검색 후 삽입)",
        "image_gen": "(이미지 생성 후 삽입)"
    }
    
    # LLM이 리스트를 반환할 수 있으므로 문자열로 안전하게 변환
    def ensure_str(field_name: str, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            logger = get_logger()
            logger.log(
                LogLevel.WARNING,
                "llm_type_mismatch",
                f"LLM이 '{field_name}' 필드에 리스트를 반환함 (문자열 기대)",
                {
                    "section_title": title,
                    "field_name": field_name,
                    "original_value": value,
                    "converted_value": ", ".join(str(v) for v in value)
                }
            )
            return ", ".join(str(v) for v in value)
        return str(value)
    
    visual_meta = VisualMeta(
        visual_type=visual_type,
        purpose=ensure_str("purpose", meta_data.get("purpose", "")),
        why_this_format=ensure_str("why_this_format", meta_data.get("why_this_format", "")),
        data_source=ensure_str("data_source", meta_data.get("data_source", "")),
        placeholder=placeholder_map.get(visual_type, "(시각화 삽입 예정)")
    )
    
    state["visual_meta"] = visual_meta.model_dump()
    return state


def route_next(state: RouterState) -> str:
    """다음 노드 결정"""
    d = Decision(**(state.get("decision") or {}))

    if d.needs_diagram:
        return "render_diagram"
    if d.needs_table:
        return "render_table"
    if d.needs_image_search:
        return "image_search"
    if d.needs_image_gen:
        return "image_gen"
    return "end"
