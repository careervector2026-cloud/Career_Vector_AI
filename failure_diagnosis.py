from typing import Dict, List
from policy_config import ROLE_POLICIES


def generate_failure_diagnosis(
    *,
    final_score: float,
    threshold: float,
    resume_jd: Dict,
    github: Dict,
    leetcode: Dict,
    role_policy: str,
    role_level: str
) -> Dict:
    """
    Deterministic, explainable failure diagnosis.
    Used for REVIEW / REJECT cases.
    """

    policy = ROLE_POLICIES.get(role_policy, ROLE_POLICIES["default"])

    primary_reasons: List[Dict] = []
    secondary_reasons: List[Dict] = []
    recommendations: List[str] = []

    resume_score = resume_jd.get("final_match_score", 0)

    # 1️⃣ Below-threshold decision
    if final_score < threshold:
        primary_reasons.append({
            "reason": f"Final score {round(final_score, 2)} below threshold {threshold}",
            "severity": "HIGH"
        })

    # 2️⃣ Missing critical skills
    missing_skills = resume_jd.get("missing_skills", [])
    if missing_skills:
        primary_reasons.append({
            "reason": f"Missing critical job skills: {', '.join(missing_skills[:5])}",
            "severity": "HIGH"
        })
        recommendations.append(
            f"Acquire skills: {', '.join(missing_skills[:3])}"
        )

    # 3️⃣ Resume–JD alignment
    if resume_score < policy["resume_min"]:
        secondary_reasons.append({
            "reason": f"Low resume–JD alignment ({round(resume_score, 2)})",
            "severity": "MEDIUM"
        })
        recommendations.append(
            "Improve resume keyword coverage and align projects with JD"
        )

    # 4️⃣ GitHub weakness
    if "github" in role_policy:
        github_score = github.get("score", 0)
        if github_score < policy["github_min"]:
            secondary_reasons.append({
                "reason": f"Weak GitHub signal ({round(github_score, 2)})",
                "severity": "MEDIUM"
            })
            recommendations.append(
                "Build 2–3 role-relevant GitHub projects"
            )

    # 5️⃣ LeetCode / DSA weakness
    if "leetcode" in role_policy:
        leetcode_score = leetcode.get("score", 0)
        if leetcode_score < policy["leetcode_min"]:
            secondary_reasons.append({
                "reason": f"Insufficient DSA strength ({round(leetcode_score, 2)})",
                "severity": "MEDIUM"
            })
            recommendations.append(
                "Practice DSA consistently (medium problems)"
            )

    # 6️⃣ Resume critical failure edge case
    if resume_score < policy["resume_critical"] and not resume_jd.get("matched_skills"):
        primary_reasons.append({
            "reason": "Resume lacks role-relevant skills or projects",
            "severity": "HIGH"
        })
        recommendations.append(
            "Add role-specific projects and technologies"
        )

    decision = "reject" if final_score < threshold else "review"

    return {
        "decision": decision,
        "primary_reasons": primary_reasons,
        "secondary_reasons": secondary_reasons,
        "actionable_recommendations": recommendations,
        "explainability": "Rule-based failure diagnosis with severity levels"
    }
