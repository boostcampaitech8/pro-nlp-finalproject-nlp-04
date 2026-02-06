"""
Edit Pipeline Graph
"""
import sys
import os

# Add src to path if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langgraph.graph import StateGraph, END
from state.edit import EditInternalState
from agents.plan_core.edit.nodes import regenerate_section_node
from agents.plan_core.edit.evaluation import evaluate_section_node, route_evaluation

def build_edit_pipeline():
    """
    단일 섹션 재생성 파이프라인 (Self-Correction Loop 포함)
    Node: regenerate -> evaluate -> (loop) or end
    """
    workflow = StateGraph(EditInternalState)
    
    # Node 추가
    workflow.add_node("regenerate", regenerate_section_node)
    workflow.add_node("evaluate", evaluate_section_node)
    
    # Flow 정의
    workflow.set_entry_point("regenerate")
    workflow.add_edge("regenerate", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        route_evaluation,
        {
            "regenerate": "regenerate",
            "end": END
        }
    )
    
    return workflow.compile()

# Singleton Instance
edit_subgraph = build_edit_pipeline()

if __name__ == "__main__":
    from pathlib import Path
    import re
    import sys
    
    # ==========================================
    # 0. Helper: Simulate Frontend Selection
    # ==========================================
    def find_target_range(full_text: str, target_snippet: str):
        """
        Simulates the frontend identifying the line range for a selected text block.
        """
        lines = full_text.split('\n')
        # Use first line of snippet to locate start
        first_line_snippet = target_snippet.strip().split('\n')[0].strip()
        
        start_idx = -1
        end_idx = -1
        
        # Simple search for the starting line
        first_line_cleaned = first_line_snippet.replace("*", "").strip()
        
        for i, line in enumerate(lines):
            # Relaxed match: check if key content exists
            line_cleaned = line.strip().replace("*", "")
            if first_line_cleaned in line_cleaned:
                start_idx = i
                break
        
        # Fallback: if exact match fails, try just finding "1." and "1~2학년"
        if start_idx == -1:
            for i, line in enumerate(lines):
                if "1." in line and "1~2학년" in line:
                    start_idx = i
                    break
        
        if start_idx == -1:
            print(f"[Error] Failed to find snippet: {repr(first_line_snippet)}")
            print(">>> DEBUG: Available lines in section:")
            for i, line in enumerate(lines[:10]): # Print first 10 for check
                print(f"{i}: {repr(line)}")
        
        if start_idx != -1:
            end_idx = start_idx
            # Heuristic: Include indented children lines (for subtree edit)
            for i in range(start_idx + 1, len(lines)):
                line = lines[i]
                stripped = line.strip()
                
                # Stop if hitting next top-level item or header
                if re.match(r"^\d+\.", stripped) and not line.startswith(" "):
                    break
                if stripped.startswith("#"):
                    break
                    
                end_idx = i
                
        return start_idx, end_idx

    # ==========================================
    # 1. Load Real File
    # ==========================================
    project_root = Path(__file__).parent.parent.parent
    sample_file = project_root / "sample_markdown.md"
    
    if not sample_file.exists():
        print("[Error] sample_markdown.md not found.")
        sys.exit(1)
        
    with open(sample_file, "r", encoding="utf-8") as f:
        full_content = f.read()

    # ==========================================
    # 2. Define User Inputs (The "Real Inputs")
    # ==========================================
    # Scenario: User selects "1. 1~2학년..." block in Section 2
    USER_TARGET_SNIPPET = "1. **1~2학년(신입생/저학년)**"
    USER_INSTRUCTION = "1~2학년 타겟층의 니즈를 '중고 서적'과 '전공 자료' 중심으로 구체화하고, 구매력을 강조해줘."
    
    print(f"\n[{'='*20} Test Scenario Input {'='*20}]")
    print(f"1. Target Snippet: {USER_TARGET_SNIPPET}")
    print(f"2. Instruction: {USER_INSTRUCTION}")

    # ==========================================
    # 3. Simulate Frontend: Get Range & Context
    # ==========================================
    # We find Section 2 content first (simulating section focus)
    section_match = re.search(r"(## 2\. 시장 분석 및 타겟층 정의\n+.*?)(?=\n## |\Z)", full_content, re.DOTALL)
    if not section_match:
        print("[Error] Section 2 not found.")
        sys.exit(1)
        
    section_content = section_match.group(1).strip()
    
    # Calculate Range relative to the SECTION content
    start_line, end_line = find_target_range(section_content, USER_TARGET_SNIPPET)
    
    if start_line == -1:
        print("[Error] Target snippet not found in section.")
        sys.exit(1)
        
    print(f"\n[{'='*20} Frontend Simulation {'='*20}]")
    print(f"Calculated Range (in Section): Lines {start_line} ~ {end_line}")
    print(f"Target Text Block:\n" + "-"*30)
    print("\n".join(section_content.split('\n')[start_line:end_line+1]))
    print("-"*30)

    # ==========================================
    # 4. Execute Backend (Edit Graph)
    # ==========================================
    mock_item = {
        "target_id": "sec-2",
        "title": "시장 분석 및 타겟층 정의",
        "content": section_content,
        "guideline": "시장 현황 및 타겟 분석 Report Style"
    }

    state = EditInternalState(
        target_section_id="sec-2",
        match_section_index=0,
        instruction=USER_INSTRUCTION,
        granularity="subtree",
        edit_range_start=start_line,
        edit_range_end=end_line,
        plan={"blueprint": [mock_item]},
        regenerated_content="",
        retry_count=0
    )
    
    print(f"\n[{'='*20} Backend Execution {'='*20}]")
    print(">>> Invoking Edit Graph...")
    final_state = edit_subgraph.invoke(state)
    
    result_content = final_state["regenerated_content"]

    # ==========================================
    # 5. Output Result
    # ==========================================
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{sample_file.stem}_edit_result.md"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Original Content (Section 2)\n\n")
        f.write(section_content)
        f.write("\n\n" + "="*40 + "\n\n")
        f.write("# Edited Result (Whole Section)\n\n")
        f.write(result_content)
        
    print(f"\n>>> Execution Complete.")
    print(f">>> Result saved to: {output_file}")
