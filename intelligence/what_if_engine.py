def generate_what_if_analysis(result: dict):
    """
    Simulates score improvement scenarios using existing scoring logic.
    No ML, pure deterministic simulation.
    """

    current_score = result.get("final_score", 0)
    threshold = result.get("threshold", 0)
    status = result.get("status", "reject")

    resume_score = result.get("resume_jd", {}).get("final_match_score", 0)
    github_score = result.get("github", {}).get("score", 0)
    leetcode_score = result.get("leetcode", {}).get("score", 0)

    role_policy = result.get("role_policy", "resume_only")

    scenarios = []

    # -----------------------------
    # Helper: recompute score
    # -----------------------------
    def compute_score(resume, github, leetcode):
        if role_policy == "resume_only":
            return resume
        elif role_policy == "resume_github":
            return 0.6 * resume + 0.4 * github
        elif role_policy == "resume_leetcode":
            return 0.6 * resume + 0.4 * leetcode
        else:
            return 0.5 * resume + 0.3 * github + 0.2 * leetcode

    def get_status(score):
        if score >= threshold:
            return "shortlist"
        elif score >= threshold - 0.05:
            return "review"
        return "reject"

    # -----------------------------
    # Scenario 1: Improve GitHub
    # -----------------------------
    boosted_github = min(github_score + 20, 100)
    new_score = round(compute_score(resume_score, boosted_github, leetcode_score), 2)

    scenarios.append({
        "change": "Improve GitHub projects (add strong real-world projects)",
        "new_score": new_score,
        "new_status": get_status(new_score),
        "impact": round(new_score - current_score, 2)
    })

    # -----------------------------
    # Scenario 2: Improve DSA
    # -----------------------------
    boosted_leetcode = min(leetcode_score + 20, 100)
    new_score = round(compute_score(resume_score, github_score, boosted_leetcode), 2)

    scenarios.append({
        "change": "Improve DSA (solve more LeetCode problems)",
        "new_score": new_score,
        "new_status": get_status(new_score),
        "impact": round(new_score - current_score, 2)
    })

    # -----------------------------
    # Scenario 3: Improve Skills
    # -----------------------------
    boosted_resume = min(resume_score + 15, 100)
    new_score = round(compute_score(boosted_resume, github_score, leetcode_score), 2)

    scenarios.append({
        "change": "Improve missing core skills",
        "new_score": new_score,
        "new_status": get_status(new_score),
        "impact": round(new_score - current_score, 2)
    })

    # sort by highest impact
    scenarios.sort(key=lambda x: x["impact"], reverse=True)

    return {
        "current_status": status,
        "current_score": current_score,
        "what_if_scenarios": scenarios[:3]
    }