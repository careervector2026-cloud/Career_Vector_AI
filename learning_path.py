# learning_path.py

import math

from learning_path_resources import load_resources
from skill_roadmaps_loader import load_skill_roadmaps
from skill_prerequisites_loader import load_skill_prerequisites
from learning_progress import load_progress


# -------------------------------------------------
# Skill categorization (for base complexity)
# -------------------------------------------------
SKILL_CATEGORY = {
    "sql": "foundational",
    "data structures": "foundational",

    "python": "language",
    "java": "language",

    "rest api": "framework",
    "spring boot": "framework",
    "django": "framework",
    "node": "framework",
    "react": "framework",

    "system design": "advanced",
    "machine learning": "advanced"
}

# -------------------------------------------------
# Base duration by complexity
# -------------------------------------------------
BASE_WEEKS = {
    "foundational": 2,
    "language": 2,
    "framework": 2,
    "advanced": 3
}

# -------------------------------------------------
# Priority impact on duration
# -------------------------------------------------
PRIORITY_WEIGHT = {
    "High": 1.5,
    "Medium": 1.2,
    "Low": 1.0
}

# -------------------------------------------------
# Skill normalization (minimal, safe)
# -------------------------------------------------
SKILL_NORMALIZATION = {
    "springboot": "spring boot",
    "spring-boot": "spring boot",
    "rest apis": "rest api",
    "apis": "rest api",
    "nodejs": "node",
    "js": "javascript"
}


def normalize_skill(skill: str) -> str:
    skill = skill.lower().strip()
    return SKILL_NORMALIZATION.get(skill, skill)


def estimate_time(skill: str, priority: str) -> int:
    category = SKILL_CATEGORY.get(skill, "framework")
    base = BASE_WEEKS.get(category, 2)
    weight = PRIORITY_WEIGHT.get(priority, 1.0)
    return math.ceil(base * weight)


# -------------------------------------------------
# Graph schema for frontend (roadmap.sh style)
# -------------------------------------------------
def build_graph_schema(skill, roadmap, prerequisites):
    nodes = []
    edges = []

    # Root skill
    nodes.append({
        "id": skill,
        "label": skill,
        "type": "skill"
    })

    # Prerequisites
    for pre in prerequisites:
        nodes.append({
            "id": pre,
            "label": pre,
            "type": "prerequisite"
        })
        edges.append({
            "from": pre,
            "to": skill
        })

    # Roadmap levels and topics
    if roadmap:
        for level in roadmap.get("levels", []):
            level_id = f"{skill}_level_{level['level']}"
            nodes.append({
                "id": level_id,
                "label": level["name"],
                "type": "level"
            })
            edges.append({
                "from": skill,
                "to": level_id
            })

            for topic in level.get("topics", []):
                topic_id = f"{level_id}_{topic}"
                nodes.append({
                    "id": topic_id,
                    "label": topic,
                    "type": "topic"
                })
                edges.append({
                    "from": level_id,
                    "to": topic_id
                })

    return {
        "nodes": nodes,
        "edges": edges
    }


# -------------------------------------------------
# MAIN LEARNING PATH GENERATOR
# -------------------------------------------------
def generate_learning_path(
    target_role: str,
    missing_skills: list,
    weak_skills: list,
    student_id: str | None = None
):
    resources = load_resources()
    roadmaps = load_skill_roadmaps()
    prerequisites_map = load_skill_prerequisites()
    progress_data = load_progress()

    learning_path = []
    step = 1
    total_weeks = 0

    def add_skill(skill, skill_type, priority):
        nonlocal step, total_weeks

        normalized = normalize_skill(skill)
        weeks = estimate_time(normalized, priority)
        total_weeks += weeks

        roadmap = roadmaps.get(normalized)
        prerequisites = prerequisites_map.get(normalized, [])
        graph = build_graph_schema(normalized, roadmap, prerequisites)

        progress = None
        if student_id:
            progress = (
                progress_data
                .get(student_id, {})
                .get(normalized)
            )

        learning_path.append({
            "step": step,
            "skill": skill,
            "skill_type": skill_type,
            "priority": priority,
            "estimated_time_weeks": weeks,
            "resources": resources.get(normalized, []),
            "detailed_roadmap": roadmap,
            "prerequisites": prerequisites,
            "graph": graph,
            "progress": progress,
            "outcome": f"Improve competency in {skill}"
        })
        step += 1

    # Missing skills → High priority
    for skill in missing_skills:
        add_skill(skill, "Missing", "High")

    # Weak skills → Medium priority
    for skill in weak_skills:
        add_skill(skill, "Weak", "Medium")

    return {
        "target_role": target_role,
        "estimated_readiness_weeks": max(total_weeks - 1, total_weeks),
        "learning_path": learning_path
    }
