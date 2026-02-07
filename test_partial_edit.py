# -*- coding: utf-8 -*-
import sys
import os
import io

# 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from state.edit import EditInternalState
from agents.edit_core.nodes import regenerate_section_node

# Mock State 생성
test_state = EditInternalState(
    target_section_id="test_section_1",
    instruction="이 문장 좀 더 자연스럽게 매끄럽게 다듬어줘",
    granularity="sentence",
    edit_range_start=2,  # 3번째 줄
    # edit_range_end는 일부러 넣지 않음 (자동 계산 테스트)
    match_section_index=0,
    retry_count=0,
    idea={
        "blueprint": [
            {
                "target_id": "test_section_1",
                "title": "테스트 섹션",
                "content": "첫 번째 줄입니다.\n두 번째 줄입니다.\n세 번째 줄은 좀 어색합니다.\n네 번째 줄입니다.",
                "guideline": "테스트 가이드라인"
            }
        ]
    }
)

print("=== Partial Edit Test (Start Only) ===")
print(f"Input Start Line: {test_state['edit_range_start']}")

try:
    result_state = regenerate_section_node(test_state)
    
    with open("test_partial_result.txt", "w", encoding="utf-8") as f:
        f.write(f"Calculated End Line: {result_state.get('edit_range_end')}\n")
        f.write(f"Used Guideline: {result_state.get('used_guideline')}\n")
        f.write("\n--- Regenerated Content ---\n")
        f.write(result_state.get("regenerated_content"))
        f.write("\n---------------------------\n")
        
        if result_state.get("edit_range_end") == 2:
            f.write("\n✅ PASS: edit_range_end automatically set to start_line")
            print("\n✅ PASS: Result saved to test_partial_result.txt")
        else:
            f.write(f"\n❌ FAIL: Expected end_line 2, got {result_state.get('edit_range_end')}")
            print("\n❌ FAIL: Check test_partial_result.txt")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n❌ ERROR: {e}")
