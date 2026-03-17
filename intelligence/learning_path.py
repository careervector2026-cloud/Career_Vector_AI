# learning_path.py

from intelligence.learning_path_resources import load_resources
from config.skill_roadmaps_loader import load_skill_roadmaps
from config.skill_prerequisites_loader import load_skill_prerequisites
from learning_progress import load_progress


# -------------------------------------------------
# Skill Categories
# -------------------------------------------------

ROLE_CLUSTERS = {
    "frontend": {
    "html", "css", "javascript", "typescript",
    "react", "angular", "vue", "redux",
    "next.js",
    "rest api", "git", "ci/cd", "docker", "node","system design"
    },
    "backend": {
        "java", "python", "spring boot",
        "django", "node", "sql", "rest api","system design"
    },
    "ml": {
        "python", "machine learning",
        "tensorflow", "pytorch"
    }
}


# -------------------------------------------------
# Utility Functions
# -------------------------------------------------

def normalize(skill: str) -> str:
    return skill.lower().strip()


def detect_primary_cluster(target_role: str) -> str:
    role = target_role.lower()

    if "frontend" in role:
        return "frontend"
    if "backend" in role:
        return "backend"
    if "machine learning" in role or "ml" in role:
        return "ml"

    return "backend"  # fallback


# -------------------------------------------------
# Dependency Resolution
# -------------------------------------------------

def resolve_dependencies(skill, prerequisites_map, resolved, seen):
    skill = normalize(skill)

    if skill in seen:
        return
    seen.add(skill)

    for pre in prerequisites_map.get(skill, []):
        resolve_dependencies(pre, prerequisites_map, resolved, seen)

    if skill not in resolved:
        resolved.append(skill)


# -------------------------------------------------
# Framework Specialization
# -------------------------------------------------

def filter_frameworks(skills, cluster):
    if cluster != "frontend":
        return skills

    frameworks = {"react", "angular", "vue"}
    present = [s for s in skills if s in frameworks]

    if len(present) <= 1:
        return skills

    # Prefer React if multiple detected
    preferred = "react"
    filtered = [s for s in skills if s not in frameworks]
    filtered.append(preferred)

    return filtered


# -------------------------------------------------
# Duration Estimation
# -------------------------------------------------

def estimate_time(skill, roadmap):
    if roadmap:
        return roadmap.get("estimated_total_weeks", 3)
    return 3


# -------------------------------------------------
# MAIN GENERATOR
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

    cluster = detect_primary_cluster(target_role)

    # ------------------------------------------------
    # Normalize skills
    # ------------------------------------------------
    base_skills = [
        normalize(s)
        for s in (missing_skills + weak_skills)
        if isinstance(s, str) and s.strip()
    ]

    # ------------------------------------------------
    # Keep cluster-relevant skills ONLY
    # ------------------------------------------------
    cluster_skills = [
        s for s in base_skills
        if s in ROLE_CLUSTERS.get(cluster, set())
    ]

    # Framework specialization (frontend only)
    cluster_skills = filter_frameworks(cluster_skills, cluster)

    # ------------------------------------------------
    # Resolve dependencies
    # ------------------------------------------------
    resolved = []
    for skill in cluster_skills:
        resolve_dependencies(skill, prerequisites_map, resolved, set())

    # Remove duplicates (preserve order)
    ordered_skills = []
    for s in resolved:
        if s not in ordered_skills:
            ordered_skills.append(s)

    # ------------------------------------------------
    # STAGE ORDERING (Strict + Stable)
    # ------------------------------------------------

    STAGE_ORDER = {
        "frontend": [
            ["html", "css"],
            ["javascript", "typescript"],
            ["react", "angular", "vue"],
            ["redux"],
            ["rest api"],
            ["next.js"],
            ["ci/cd", "docker", "git"]
        ],
        "backend": [
            ["java", "python"],
            ["sql"],
            ["spring boot", "django", "node"],
            ["rest api"],
            ["system design"],
            ["ci/cd", "docker", "git"]
        ],
        "ml": [
            ["python"],
            ["machine learning"],
            ["tensorflow", "pytorch"],
            ["system design"],
            ["docker", "git"]
        ]
    }

    stage_groups = STAGE_ORDER.get(cluster, [])

    def get_stage_index(skill):
        for idx, group in enumerate(stage_groups):
            if skill in group:
                return idx
        return len(stage_groups)

    ordered_skills.sort(key=get_stage_index)

    # ------------------------------------------------
    # Build Final Learning Path
    # ------------------------------------------------
    learning_path = []
    total_weeks = 0
    step = 1

    for skill in ordered_skills:
        roadmap = roadmaps.get(skill)
        weeks = estimate_time(skill, roadmap)
        total_weeks += weeks

        progress = None
        if student_id:
            progress = (
                progress_data
                .get(student_id, {})
                .get(skill)
            )

        learning_path.append({
            "step": step,
            "skill": skill,
            "skill_type": "Missing" if skill in missing_skills else "Weak",
            "priority": "High" if skill in missing_skills else "Medium",
            "estimated_time_weeks": weeks,
            "resources": resources.get(skill, []),
            "detailed_roadmap": roadmap,
            "prerequisites": prerequisites_map.get(skill, []),
            "progress": progress,
            "outcome": f"Master {skill} for {target_role}"
        })

        step += 1

    return {
        "target_role": target_role,
        "estimated_readiness_weeks": total_weeks,
        "learning_path": learning_path
    }