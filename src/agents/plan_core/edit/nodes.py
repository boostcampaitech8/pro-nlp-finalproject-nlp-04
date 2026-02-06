"""
Edit Pipeline Nodes
"""
from agents.plan_core.generator import generate_section_from_blueprint
from agents.plan_core.schemas import StructuredInput, BlueprintItem
from state.edit import EditInternalState

def regenerate_section_node(state: EditInternalState) -> EditInternalState:
    """
    기존 섹션 재생성 노드
    - User Instruction을 Blueprint Guideline에 주입하여 재생성 유도
    """
    print(f"[Edit] 섹션 {state['target_section_id']} 재생성 중... (요청: {state['instruction']})")
    
    # GlobalState에서 데이터 추출
    blueprint_list = state.get("plan", {}).get("blueprint", []) if state.get("plan") else []
    target_index = state["match_section_index"]
    
    if not blueprint_list or target_index >= len(blueprint_list):
        print(f"[Edit] Error: Blueprint not found or index out of range.")
        return state

    # 1. Target Blueprint Item 가져오기
    target_item_dict = blueprint_list[target_index]
    target_item = BlueprintItem(**target_item_dict)
    
    # 2. Instruction Injection
    # 기존 가이드라인 뒤에 유저 요청을 강력하게 붙입니다.
    original_guideline = target_item.guideline or ""
    injected_guideline = f"{original_guideline}\n\n[USER REVISION REQEUST]: {state['instruction']}"
    
    # Feedback Injection (If Retry)
    if state.get("feedback"):
        injected_guideline += f"\n\n[PREVIOUS FEEDBACK (Must Fix)]: {state['feedback']}"
        print(f"[Edit] 피드백 반영하여 재생성: {state['feedback']}")
    
    injected_guideline += "\n(기존 기획의 톤앤매너와 양식을 유지하면서, 위 요청 사항을 자연스럽게 반영하여 섹션을 업데이트하세요.)"
    
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
    
    # 4. Generator 호출 (Reuse Core Logic)
    # previous_sections는 문맥상 필요하다면 GlobalState에서 가져와야 하지만, 
    # 단일 섹션 수정 MVP에서는 일단 비워둡니다 (혹은 context에 포함 가능)
    # TODO: context['previous_sections']가 있다면 전달
    
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
