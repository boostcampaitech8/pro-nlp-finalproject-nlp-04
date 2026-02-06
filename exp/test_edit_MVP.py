
import sys
import os
from pprint import pprint

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from graph.edit_graph import edit_subgraph
from agents.plan_core.schemas import BlueprintItem

def test_regeneration():
    print(">>> Testing Section Regeneration MVP")
    
    # 1. Setup Mock Context
    blueprint_item = {
        "target_id": "item_1",
        "title": "AI의 장점",
        "guideline": "AI가 가져오는 생산성 향상과 비용 절감 효과에 대해 설명하세요.",
        "content": "기존 내용: AI는 좋습니다. 빨라요. 끝."
    }
    
    full_blueprint = [blueprint_item]
    
    context = {
        "planning_style": "Technical",
        "rationale": "기술적 관점 중요",
        "toc": ["1. AI의 장점"]
    }
    
    # 2. Setup Input State (EditInternalState which inherits GlobalState)
    input_state = {
        # GlobalState Fields
        "plan": {
            "blueprint": full_blueprint,
            "sections": [],
            "final_markdown": "",
            "output_path": "",
            "visual_artifacts": {}
        },
        "idea": {
            "planning_style": context["planning_style"],
            "rationale": context["rationale"],
            "toc": context["toc"],
            "blueprint": full_blueprint,
            "last_decision": "",
            "messages": ""
        },
        
        # EditInternalState Fields
        "target_section_id": "item_1", # Renamed from section_id
        "instruction": "에너지 소비 문제와 관련된 단점을 반론으로 포함해서 균형있게 다시 써줘.",
        "match_section_index": 0,
        # "full_blueprint": full_blueprint # Removed
    }
    
    print("-" * 50)
    print(f"Original Guideline: {blueprint_item['guideline']}")
    print(f"User Instruction: {input_state['instruction']}")
    print("-" * 50)
    
    # Collecting logs for report
    execution_logs = []
    critique_history = []
    final_content = ""
    used_guideline = ""
    
    # 3. Invoke Pipeline
    try:
        print("\n>>> Pipeline Execution Log:")
        for event in edit_subgraph.stream(input_state):
            for key, value in event.items():
                node_log = f"\n[Node: {key}]"
                print(node_log)
                execution_logs.append(node_log)
                
                if "used_guideline" in value:
                    used_guideline = value['used_guideline']
                
                if "critique" in value:
                    log = f"Critique: {value['critique']}"
                    print(log)
                    critique_history.append(log)
                
                if "feedback" in value and value['feedback']:
                    log = f"Feedback Created: {value['feedback']} (Retry: {value.get('retry_count')})"
                    print(log)
                    critique_history.append(log)
                    
                if "regenerated_content" in value:
                    print(f"Content Generated (Length: {len(value['regenerated_content'])})")
                    final_content = value['regenerated_content']
        
        # 4. Generate Report Markdown
        report_path = "edit_experiment_result.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Edit Experiment Result\n\n")
            
            f.write("## 1. Input Context\n")
            f.write(f"- **Section**: {blueprint_item['title']}\n")
            f.write(f"- **Instruction**: {input_state['instruction']}\n\n")
            
            f.write("## 2. Blueprint Transformation\n")
            f.write("### Original Guideline\n")
            f.write(f"> {blueprint_item['guideline']}\n\n")
            
            f.write("### Modified Guideline (Injected)\n")
            f.write(f"```text\n{used_guideline}\n```\n\n")
            
            f.write("## 3. Comparison\n")
            f.write("### Original Content\n")
            f.write(f"{blueprint_item['content']}\n\n")
            
            f.write("### Regenerated Content\n")
            f.write(f"{final_content}\n\n")
            
            f.write("## 4. Evaluation Process\n")
            if critique_history:
                for item in critique_history:
                    f.write(f"- {item}\n")
            else:
                f.write("- No evaluation issues (First Pass)\n")
                
        print(f"\n>>> Report saved to {report_path}")
            
    except Exception as e:
        print(f"\n[ERROR] 파이프라인 실행 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_regeneration()
