
import json
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from agents.plan_core.generator import generate_section_from_blueprint, compose_plan_markdown
from agents.plan_core.schemas import StructuredInput, BlueprintItem, GeneratedPlan, StructuredIdea, TableOfContents, TableOfContentsItem, PlanSection

def batch_generate():
    input_path = "sample_blueprints_20.json"
    output_path = "batch_generated_sections.json"
    output_dir = "exp/generated_samples"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if not os.path.exists(input_path):
        # Check if it was moved to exp/
        input_path = os.path.join("exp", "sample_blueprints_20.json") 
        if not os.path.exists(input_path):
            print(f"Error: {input_path} not found.")
            return

    with open(input_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    generated_results = []

    print(f"Starting batch generation for {len(samples)} items...")

    for i, sample in enumerate(samples):
        # Construct Input objects
        blueprint_data = sample['blueprint'][0]
        blueprint_item = BlueprintItem(**blueprint_data)

        print(f"[{i+1}/{len(samples)}] Generating: {blueprint_item.title} ({sample['planning_style']})")

        structured_input = StructuredInput(
            planning_style=sample['planning_style'],
            rationale=sample['rationale'],
            toc=sample['toc'],
            blueprint=[blueprint_item]
        )

        # Determine section index
        section_index = 0
        for idx, toc_text in enumerate(sample['toc']):
            if blueprint_item.title.strip() == toc_text.strip():
                section_index = idx
                break
        
        try:
            # Call Generator
            section = generate_section_from_blueprint(
                structured_input=structured_input,
                blueprint_item=blueprint_item,
                section_index=section_index,
                previous_sections=[] 
            )
            
            # Create GeneratedPlan object for Markdown composition
            # We need to reconstruct StructuredIdea and TableOfContents from the sample dict
            idea_obj = StructuredIdea(
                title=f"Sample Plan {i+1}", 
                summary=f"A {sample['planning_style']} plan regarding {sample['rationale']}",
                problem="Sample Problem",
                target_users=["Sample User"],
                core_features=["Feature A"],
                differentiators=["Diff A"],
                business_model="Sample Biz Model",
                tech_stack=[],
                constraints=[]
            )
            
            toc_items = [TableOfContentsItem(section_number=str(idx+1), title=t) for idx, t in enumerate(sample['toc'])]
            toc_obj = TableOfContents(items=toc_items)
            
            # Since we only generated one section, we'll put it in the plan. 
            # Note: The other TOC items won't have content, but compose_plan_markdown handles sections list.
            generated_plan = GeneratedPlan(
                idea=idea_obj,
                toc=toc_obj,
                sections=[section],
                method="blueprint"
            )
            
            # Generate Markdown
            markdown_content = compose_plan_markdown(generated_plan)
            
            # Save Markdown File
            md_filename = f"sample_{i+1:02d}_{sample['planning_style']}.md"
            md_path = os.path.join(output_dir, md_filename)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Store result: 
            # We keep putting content in blueprint for the edit test script compatibility,
            # BUT we also store the markdown path/content if needed.
            # The User said "generate된거는 content에 넣는게 아니라 markdown을 만들어야지".
            # This implies the artifacts we care about are the Markdowns. 
            # I will ensure the JSON reflects that we have a 'final_markdown' available.
            sample_with_content = sample.copy()
            sample_with_content['blueprint'][0]['content'] = section.content # Still needed for currently implemented test
            sample_with_content['final_markdown'] = markdown_content
            sample_with_content['markdown_path'] = md_path
            
            generated_results.append(sample_with_content)
            
        except Exception as e:
            print(f"Error generating item {i+1}: {e}")
            sample_with_content = sample.copy()
            sample_with_content['error'] = str(e)
            generated_results.append(sample_with_content)

    # Save JSON Results (now in exp/)
    output_json_path = os.path.join("exp", output_path)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(generated_results, f, ensure_ascii=False, indent=4)
        
    print(f"\nBatch generation complete. \n- JSON saved to {output_json_path}\n- Markdown files saved in {output_dir}")

if __name__ == "__main__":
    batch_generate()
