"""
Edit Pipeline Nodes
"""
from agents.plan_core.generator import generate_section_from_blueprint, generate_partial_edit
from agents.plan_core.schemas import StructuredInput, BlueprintItem
from state.edit import EditInternalState
from prompts.edit_prompts import SECTION_REGENERATION_GUIDELINE_TEMPLATE

def regenerate_node(state: EditInternalState) -> EditInternalState:
    """
    섹션 또는 부분(문단/문장) 재생성 노드
    """

    # GlobalState에서 데이터 추출
    blueprint_list = state.get("idea", {}).get("blueprint", [])
    if not blueprint_list:
        print(f"[Edit] Error: Blueprint not found.")
        return state

    # [Fix] target의 section index 찾기
    blueprint_index = _calculate_section_index(state)
    if blueprint_index >= len(blueprint_list):
        print(f"[Edit] Error: Blueprint index out of range.")
        return state

    # 1. Target Blueprint Item 가져오기
    target_item_dict = blueprint_list[blueprint_index]
    target_item = BlueprintItem(**target_item_dict)
    
    granularity = state.get("granularity", "section")
    range_start = state.get("edit_range_start")
    
    # -------------------------------------------------------
    # Case A: Section Edit (전체 재생성)
    # -------------------------------------------------------
    if granularity == "section":
        print(f"[Edit] 섹션 전체 재생성 모드")
        
        # Instruction Injection
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
            title=target_item.title,
            guideline=injected_guideline,
            content=""
        )
        
        # StructuredInput 구성
        idea = state.get("idea", {})
        structured_input = StructuredInput(
            planning_style=idea.get("planning_style", "General"),
            rationale=idea.get("rationale", ""),
            toc=idea.get("toc", []),
            blueprint=[BlueprintItem(**b) for b in blueprint_list]
        )
        
        # Generator 호출
        new_section = generate_section_from_blueprint(
            structured_input=structured_input,
            blueprint_item=modified_item,
            section_index=target_index,
            previous_sections=[] 
        )
        
        # 결과 저장
        state["regenerated_content"] = new_section.content
        state["used_guideline"] = injected_guideline
        print(f"[Edit] 재생성 완료 (Length: {len(new_section.content)})")
        
        return state

    # -------------------------------------------------------
    # Case B: Granular Edit (Paragraph/Sentence)
    # -------------------------------------------------------
    elif granularity in ["paragraph", "sentence"] and range_start is not None:
        
        # 현재 컨텐츠 분리 (줄바꿈 기준)
        current_content = target_item.content or ""
        lines = current_content.split('\n')
        
        # range_end 자동 계산
        range_end = _calculate_range_end(lines, range_start, granularity)
        print(f"[Edit] range_end 계산: {range_start} ~ {range_end} (Granularity: {granularity})")
            
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
    
    else:
        print(f"[Edit] Error: Invalid granularity or missing range. (Granularity: {granularity})")
        return state


def _calculate_section_index(state: EditInternalState) -> int:
    """
    state의 정보를 바탕으로 Blueprint 리스트에서의 인덱스를 찾습니다.
    (edit_range_start & final_markdown 이용)
    """

    range_start = state.get("edit_range_start")
    final_markdown = state.get("plan", {}).get("final_markdown", "")
    
    if range_start is not None and final_markdown:
        lines = final_markdown.split('\n')
        if range_start < len(lines):
            # 위로 올라가며 # (Level 1 Header) 개수 세기
            header_count = 0
            safe_start = max(0, range_start)
            
            # 0번 라인부터 현재 라인까지 스캔하여 헤더 개수 카운트
            # (Blueprint 순서는 문서의 섹션 순서와 동일하다고 가정)
            for i in range(safe_start + 1): # 0 ~ safe_start
                line = lines[i]
                if line.lstrip().startswith('# ') or line.lstrip() == '#':
                    header_count += 1
            
            if header_count > 0:
                # 1번째 섹션 -> 인덱스 0
                return header_count - 1
            
    return -1

def _calculate_range_end(lines: list[str], start_idx: int, granularity: str) -> int:
    """
    문서 구조(헤더 레벨, 불릿 포인트 등)를 분석하여 range_end를 자동으로 계산합니다.
    """
    if start_idx >= len(lines):
        return start_idx
    
    start_line = lines[start_idx]
    
    # --- Case 1: Heading Block ('#') ---
    if start_line.lstrip().startswith('#'):
        # 현재 헤더 레벨 계산 (예: ## -> 2)
        base_level = len(start_line) - len(start_line.lstrip('#'))
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            # 빈 줄은 포함
            if not line.strip():
                continue
                
            # 다른 헤더를 만났을 때 레벨 비교
            if line.lstrip().startswith('#'):
                current_level = len(line) - len(line.lstrip('#'))
                # 같거나 더 상위(작은 숫자) 레벨의 헤더가 나오면 종료
                if current_level <= base_level:
                    return i - 1
        return len(lines) - 1

    # --- Case 2: List Item Block ('-', '*', '+', '1.') ---
    # 간단한 불릿 포인트/번호 매기기 확인
    is_list_item = start_line.lstrip().startswith(('-', '*', '+')) or \
                   (len(start_line.lstrip()) > 1 and start_line.lstrip()[0].isdigit() and start_line.lstrip()[1] == '.')
                   
    if is_list_item:
        base_indent = len(start_line) - len(start_line.lstrip())
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            # 빈 줄은 포함 (리스트 아이템 사이의 간격일 수 있음)
            if not line.strip():
                continue
                
            current_indent = len(line) - len(line.lstrip())
            
            # 들여쓰기가 더 적거나 같으면, 새로운 아이템/블록의 시작으로 간주하고 종료
            if current_indent <= base_indent:
                 return i - 1
                 
        return len(lines) - 1

    # --- Case 3: Paragraph (Text Block) ---
    # 다음 빈 줄 전까지, 혹은 새로운 헤더/리스트가 나오기 전까지
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        
        # 1. 빈 줄을 만나면 종료
        if not line.strip():
            return i - 1
            
        # 2. 헤더나 리스트 아이템을 만나면 종료 (다른 구조의 시작)
        if line.lstrip().startswith(('#', '-', '*', '+')) or \
           (len(line.lstrip()) > 1 and line.lstrip()[0].isdigit() and line.lstrip()[1] == '.'):
            return i - 1
            
    return len(lines) - 1
