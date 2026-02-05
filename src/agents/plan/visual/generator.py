"""
시각화 생성 에이전트 - 표, 다이어그램, 이미지 생성/검색
"""
from __future__ import annotations
from typing import Dict, Any

from models.llm import chat
from agents.plan.visual.schemas import Decision, VisualMeta, VisualArtifact


def render_table(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    표 생성 - 마크다운 테이블 생성
    """
    text = state.get("section_text", "")
    d = Decision(**state.get("decision", {}))
    visual_meta = state.get("visual_meta", {})
    
    prompt = f"""
    다음 텍스트를 기반으로 '{d.table_type.value}' 스타일의 Markdown Table을 작성해줘.
    
    규칙:
    - 표만 출력해. 제목(#, ##, ### 등)이나 설명 텍스트 없이 오직 표만.
    - 표는 완전하고 읽기 쉽게 작성해.
    
    내용: {text}
    """
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
    
    prompt = f"""
    다음 텍스트를 기반으로 '{d.diagram_type.value}' 스타일의 Mermaid 다이어그램 코드를 작성해줘.
    
    규칙:
    - 오직 Mermaid 코드 블록만 출력해. 제목이나 설명 텍스트 없이.
    - 마크다운 코드 블록 안에 작성해.
    
    내용: {text}
    """
    response = chat.invoke(prompt)
    
    if visual_meta:
        visual_meta["content"] = response.content
    
    state.setdefault("artifacts", {})["diagram"] = {
        "content": response.content,
        "type": d.diagram_type.value
    }
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
