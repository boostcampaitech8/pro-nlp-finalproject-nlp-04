import json
import os

def fix_json():
    path = r"e:\project\pro-nlp-finalproject-nlp-04\exp\sample_blueprints_20.json"
    if not os.path.exists(path):
        print(f"File {path} not found.")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        if "blueprint" in item and len(item["blueprint"]) > 0:
            # Sync TOC with the title from the single blueprint item
            blueprint_title = item["blueprint"][0]["title"]
            item["toc"] = [blueprint_title]
            print(f"Updated TOC for: {blueprint_title}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("Successfully updated exp/sample_blueprints_20.json")

if __name__ == "__main__":
    fix_json()
