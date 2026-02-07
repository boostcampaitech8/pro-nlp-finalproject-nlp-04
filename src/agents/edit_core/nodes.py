"""
Edit Pipeline Nodes
"""
from agents.plan_core.generator import generate_section_from_blueprint, generate_partial_edit
from agents.plan_core.schemas import StructuredInput, BlueprintItem
from state.edit import EditInternalState
from prompts.edit_prompts import SECTION_REGENERATION_GUIDELINE_TEMPLATE

def regenerate_section_node(state: EditInternalState) -> EditInternalState:
    """
    섹션 또는 부분(문단/문장) 재생성 노드
    """
    print(f"[Edit] 섹션 {state['target_section_id']} 재생성 중... (요청: {state['instruction']})")
    
    # GlobalState에서 데이터 추출
    blueprint_list = state.get("idea", {}).get("blueprint", [])
    target_index = state["match_section_index"]
    
    if not blueprint_list or target_index >= len(blueprint_list):
        print(f"[Edit] Error: Blueprint not found or index out of range.")
        return state

    # 1. Target Blueprint Item 가져오기
    target_item_dict = blueprint_list[target_index]
    target_item = BlueprintItem(**target_item_dict)
    
    # -------------------------------------------------------
    # A. Granular Edit (Paragraph/Sentence) - Range Based
    # -------------------------------------------------------
    granularity = state.get("granularity", "section")
    range_start = state.get("edit_range_start")
    range_end = state.get("edit_range_end")
    
    # content가 존재하고, 범위가 명시된 경우 부분 수정 진행
    if granularity in ["paragraph", "sentence", "block", "subtree"] and range_start is not None:
        
        # 현재 컨텐츠 분리 (줄바꿈 기준)
        current_content = target_item.content or ""
        lines = current_content.split('\n')
        
        # range_end 자동 계산 (제공되지 않은 경우)
        if range_end is None:
            # 기본값: range_start와 동일 (한 줄 수정)
            range_end = range_start
            print(f"[Edit] range_end 미지정 -> {range_end}로 자동 설정")
            
        print(f"[Edit] 부분 수정 모드: {granularity} (Lines: {range_start}~{range_end})")
        
        # 범위 보정 (Index Out of Bounds 방지)
        safe_start = max(0, min(range_start, len(lines) - 1))
        safe_end = max(safe_start, min(range_end, len(lines) - 1))
        
        # Context 추출
        prefix_lines = lines[:safe_start]
        target_lines = lines[safe_start : safe_end + 1]
        suffix_lines = lines[safe_end + 1:]
        
        prefix_text = "\n".join(prefix_lines)
        target_text = "\n".join(target_lines)
        suffix_text = "\n".join(suffix_lines)
        
        # 생성 요청
        new_part = generate_partial_edit(
            instruction=state['instruction'],
            target_text=target_text,
            prefix_text=prefix_text,
            suffix_text=suffix_text,
            granularity=granularity
        )
        
        # 결과 재조립
        reassembled_lines = prefix_lines + [new_part] + suffix_lines
        state["regenerated_content"] = "\n".join(reassembled_lines)
        state["used_guideline"] = f"Partial Edit ({granularity}): {state['instruction']}"
        print(f"[Edit] 부분 수정 완료.")
        
        return {
            **state,
            "regenerated_content": "\n".join(reassembled_lines),
            "used_guideline": f"Partial Edit ({granularity}): {state['instruction']}",
            "edit_range_end": safe_end
        }

    # -------------------------------------------------------
    # B. Section Edit (Legacy) - Whole Section Regeneration
    # -------------------------------------------------------
    
    # 2. Instruction Injection
    # 기존 가이드라인 뒤에 유저 요청을 강력하게 붙입니다.
    original_guideline = target_item.guideline or ""
    
    # Feedback Injection (If Retry)
    feedback_section = ""
    if state.get("feedback"):
        feedback_section = f"\n\n[PREVIOUS FEEDBACK (Must Fix)]: {state['feedback']}"
        print(f"[Edit] 피드백 반영하여 재생성: {state['feedback']}")
        
    injected_guideline = SECTION_REGENERATION_GUIDELINE_TEMPLATE.format(
        original_guideline=original_guideline,
        instruction=state['instruction'],
        feedback_section=feedback_section
    )
    
    # 수정된 아이템 생성 (Generator에 전달용)
    modified_item = BlueprintItem(
        target_id=target_item.target_id,
        title=target_item.title,
        guideline=injected_guideline,
        content="" # content를 비워야 Generator가 LLM을 호출함
    )
    
    # 3. StructuredInput 구성
    # GlobalState.idea에서 정보 가져오기
    idea = state.get("idea", {})
    structured_input = StructuredInput(
        planning_style=idea.get("planning_style", "General"),
        rationale=idea.get("rationale", ""),
        toc=idea.get("toc", []),
        blueprint=[BlueprintItem(**b) for b in blueprint_list]
    )
    
    # 4. Generator 호출
    new_section = generate_section_from_blueprint(
        structured_input=structured_input,
        blueprint_item=modified_item,
        section_index=target_index,
        previous_sections=[] # MVP: 이전 섹션 문맥 없이 독립 생성
    )
    
    # 5. 결과 저장
    state["regenerated_content"] = new_section.content
    state["used_guideline"] = injected_guideline
    print(f"[Edit] 재생성 완료 (Length: {len(new_section.content)})")
    
    return state
