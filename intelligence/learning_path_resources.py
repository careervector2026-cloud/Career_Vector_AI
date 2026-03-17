# learning_path_resources.py

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCE_FILE = os.path.join(BASE_DIR, "../data/learning_resources.json")


def load_resources():
    """
    Dynamic loader for learning resources.
    Can later be replaced by DB / API without touching logic.
    """
    if not os.path.exists(RESOURCE_FILE):
        return {}

    with open(RESOURCE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
