
import json
import os
import sys
from pprint import pprint

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from graph.edit_graph import edit_subgraph
from agents.plan_core.schemas import BlueprintItem

def run_batch_edit_test():
    input_path = os.path.join("exp", "batch_generated_sections.json")
    output_json_path = os.path.join("exp", "batch_edit_results.json")
    output_md_path = os.path.join("exp", "batch_edit_report.md")
    
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found. Please run batch generation first.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    # Instructions for testing diverse scenarios
    instruction_types = [
        "분량을 2배로 늘리고 구체적인 예시를 2개 이상 추가해서 상세하게 작성해줘.",
        "톤앤매너를 매우 전문적이고 학술적인 어조로 변경하고, 객관적인 수치를 인용하는 형태로 수정해줘.",
        "이 내용에 대한 치명적인 반론이나 단점을 별도 단락으로 추가해서 균형 잡힌 시각을 보여줘.",
        "초등학생도 이해할 수 있을 만큼 쉽고 친근한 용어로 풀어서 다시 써줘.",
        "핵심 내용만 남기고 불렛 포인트 위주로 간결하게 요약해줘."
    ]
    
    results = []

    print(f"Starting batch edit test for {len(samples)} items...")
    
    for i, sample in enumerate(samples):
        # Rotate instructions
        instruction = instruction_types[i % len(instruction_types)]
        
        blueprint_data = sample['blueprint'][0]
        # Ensure content exists (it should be populated by batch generation)
        original_content = blueprint_data.get('content', "")
        
        print(f"[{i+1}/{len(samples)}] Editing: {blueprint_data['title']}")
        print(f"  - Instruction: {instruction[:50]}...")

        # Construct Input State
        full_blueprint = sample['blueprint'] # List of 1 item
        
        input_state = {
            # GlobalState Fields
            "plan": {
                "blueprint": full_blueprint,
                "sections": [], # Not strictly needed for single item edit
                "final_markdown": "",
                "output_path": "",
                "visual_artifacts": {}
            },
            "idea": {
                "planning_style": sample['planning_style'],
                "rationale": sample['rationale'],
                "toc": sample['toc'],
                "blueprint": full_blueprint,
                "last_decision": "",
                "messages": ""
            },
            
            # EditInternalState Fields
            "target_section_id": blueprint_data['target_id'],
            "instruction": instruction,
            "match_section_index": 0,
            
            # Pre-load generated content into state if needed? 
            # No, the graph starts with regenerate node which uses blueprint content. 
            # WAIT: regenerate_section_node currently uses state["plan"]["blueprint"] to get the item.
            # The item in 'plan' state already has the 'content' because we loaded 'sample' which has it.
            # So the generator will see 'content' is present.
            # IN regenerate_section_node:
            # "content" in BlueprintItem causes generator to skip generation if valid?
            # Let's check regenerate_section_node logic. 
            # It modifies the blueprint item to have content="" before calling generator!
            # So it will force regeneration regardless of existing content. Correct.
        }
        
        # Execute
        try:
            final_output = None
            logs = []
            
            for event in edit_subgraph.stream(input_state):
                for key, value in event.items():
                    # Capture logs/audit
                    if "critique" in value:
                        logs.append(f"[Critique] {value['critique']}")
                    if "feedback" in value and value['feedback']:
                        logs.append(f"[Feedback] {value['feedback']}")
                    if "regenerated_content" in value:
                        final_output = value # this is the state dict
                        
            # Extract final result
            if final_output:
                regenerated_content = final_output.get("regenerated_content", "")
                critique = final_output.get("critique", "")
                used_guideline = final_output.get("used_guideline", "")
                
                result_entry = {
                    "id": i+1,
                    "title": blueprint_data['title'],
                    "style": sample['planning_style'],
                    "instruction": instruction,
                    "original_guideline": blueprint_data['guideline'],
                    "used_guideline": used_guideline,
                    "original_content": original_content,
                    "regenerated_content": regenerated_content,
                    "critique": critique,
                    "logs": logs
                }
                results.append(result_entry)
                print(f"  -> Done. Length: {len(regenerated_content)}")
            else:
                print("  -> Failed to get partial output.")
                
        except Exception as e:
            print(f"  -> Error: {e}")
            import traceback
            traceback.print_exc()

    # Save Results
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    # Generate Markdown Report
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write("# Batch Edit Test Report\n\n")
        f.write("| ID | Title | Style | Instruction Type | Result Length | Pass? |\n")
        f.write("|---|---|---|---|---|---|\n")
        
        for r in results:
            pass_fail = "PASS" if "[PASS]" in r['critique'] else "FAIL"
            inst_short = r['instruction'][:20] + "..."
            f.write(f"| {r['id']} | {r['title']} | {r['style']} | {inst_short} | {len(r['regenerated_content'])} | {pass_fail} |\n")
            
        f.write("\n## Detailed Results\n")
        for r in results:
            f.write(f"\n### {r['id']}. {r['title']}\n")
            f.write(f"- **Style**: {r['style']}\n")
            f.write(f"- **Instruction**: {r['instruction']}\n")
            f.write(f"- **Critique**: {r['critique']}\n")
            
            f.write("\n#### Modified Guideline\n")
            f.write(f"```text\n{r['used_guideline']}\n```\n")
            
            f.write("\n#### Content Comparison\n")
            f.write("<details><summary>Original Content</summary>\n\n")
            f.write(r['original_content'])
            f.write("\n</details>\n\n")
            
            f.write("<details><summary>Regenerated Content</summary>\n\n")
            f.write(r['regenerated_content'])
            f.write("\n</details>\n")
            f.write("\n---\n")

    print(f"\nBatch edit test complete. Report saved to {output_md_path}")

if __name__ == "__main__":
    run_batch_edit_test()
