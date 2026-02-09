import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), "src"))

from agents.edit_core.nodes import _calculate_range_end, regenerate_section_node
from agents.plan_core.schemas import BlueprintItem

def test_calculate_range_end():
    print("\n=== Testing _calculate_range_end logic ===\n")
    
    # Sample content
    content = """Line 0: Header
Line 1: Paragraph start
Line 2: Paragraph continue
Line 3: 
Line 4: Next Paragraph
Line 5:   Block start (indent 2)
Line 6:   Block continue
Line 7:     Nested block (indent 4)
Line 8:   Block end
Line 9: Out of block
"""
    lines = content.split('\n')
    
    # Test 1: Paragraph (stops at empty line)
    # Start at Line 1. Should end at Line 2 (Line 3 is empty)
    start = 1
    end = _calculate_range_end(lines, start, "paragraph")
    expected = 2
    print(f"Test 1 (Paragraph): Start={start}, End={end}, Expected={expected} -> {'PASS' if end == expected else 'FAIL'}")
    
    # Test 2: Block (stops at lower indentation)
    # Start at Line 5. Base indent 2.
    # Line 6: indent 2 (continue)
    # Line 7: indent 4 (continue)
    # Line 8: indent 2 (continue)
    # Line 9: indent 0 (STOP) -> End should be 8.
    start = 5
    end = _calculate_range_end(lines, start, "block")
    expected = 8
    print(f"Test 2 (Block): Start={start}, End={end}, Expected={expected} -> {'PASS' if end == expected else 'FAIL'}")
    
    # Test 3: Sentence (default 1 line)
    start = 0
    end = _calculate_range_end(lines, start, "sentence")
    expected = 0
    print(f"Test 3 (Sentence): Start={start}, End={end}, Expected={expected} -> {'PASS' if end == expected else 'FAIL'}")

def test_regenerate_section_with_location():
    print("\n=== Testing regenerate_section_node with location ===\n")
    
    # Mock content
    mock_content = """This is the first paragraph.
It has two lines.

This is the second paragraph.
It should be preserved.
"""
    
    mock_state = {
        "idea": {
            "blueprint": [
                {
                    "title": "Test Section",
                    "content": mock_content,
                    "guideline": "Test Guideline"
                }
            ]
        },
        "match_section_index": 0,
        "target_section_id": "1",
        "instruction": "Rewrite the first paragraph.",
        "granularity": "paragraph",
        "edit_range_start": 0,  # Start at line 0
        # edit_range_end should be calculated as 1 automatically
    }
    
    print(f"Initial Content:\n---\n{mock_content}---")
    print(f"Instruction: {mock_state['instruction']}")
    print(f"Granularity: {mock_state['granularity']}")
    print(f"Start Line: {mock_state['edit_range_start']}")
    
    # Run Node
    try:
        # We need to filter print because regenerate_section_node calls generate_partial_edit which uses LLM
        # For this test, we accept that LLM is called, or we could mock generate_partial_edit if needed.
        # But here we mainly want to see the log about range calculation.
        
        result_state = regenerate_section_node(mock_state)
        
        print("\n[Result verification]")
        print(f"Calculated Edit Range End: {result_state.get('edit_range_end')}")
        
        # Expected range end is 1
        if result_state.get('edit_range_end') == 1:
            print("SUCCESS: Range end correctly calculated as 1.")
        else:
            print(f"FAILURE: Range end is {result_state.get('edit_range_end')}, expected 1.")
            
        print("\nRegenerated Content:\n---")
        print(result_state.get("regenerated_content"))
        print("---")
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_calculate_range_end()
    test_regenerate_section_with_location()
