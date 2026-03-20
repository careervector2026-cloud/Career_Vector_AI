def generate_action_plan(result: dict):
    """
    Converts gaps + weak signals into top 3 actionable improvements.
    """

    actions = []

    missing_skills = result.get("resume_jd", {}).get("missing_skills", [])
    github_score = result.get("github", {}).get("score", 0)
    leetcode_score = result.get("leetcode", {}).get("score", 0)

    # -----------------------------
    # Skill gaps → high priority
    # -----------------------------
    for skill in missing_skills[:2]:
        actions.append({
            "action": f"Learn {skill}",
            "expected_impact": "+5 to +10 score",
            "priority": 1
        })

    # -----------------------------
    # GitHub improvement
    # -----------------------------
    if github_score < 60:
        actions.append({
            "action": "Build 2 strong GitHub projects",
            "expected_impact": "+8 to +12 score",
            "priority": 2
        })

    # -----------------------------
    # DSA improvement
    # -----------------------------
    if leetcode_score < 60:
        actions.append({
            "action": "Solve 100+ DSA problems",
            "expected_impact": "+6 to +10 score",
            "priority": 3
        })

    # fallback
    if not actions:
        actions.append({
            "action": "Improve advanced system design concepts",
            "expected_impact": "+5 score",
            "priority": 1
        })

    # limit to top 3
    actions = actions[:3]

    return {
        "action_plan": actions
    }