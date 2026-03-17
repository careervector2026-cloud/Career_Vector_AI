# skill_roadmaps_loader.py
import json

def load_skill_roadmaps():
    try:
        with open("../data/skills_roadmap.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
