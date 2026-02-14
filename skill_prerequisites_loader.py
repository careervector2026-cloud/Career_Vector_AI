# skill_prerequisites_loader.py
import json

def load_skill_prerequisites():
    try:
        with open("skill_prerequisites.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
