# failure_diagnosis.py

from typing import Dict, List
from config.policy_config import ROLE_POLICIES


# -------------------------------------------------
# UTILITIES
# -------------------------------------------------
def compute_impact(weight: float, gap: float = 1.0) -> float:
    """
    impact = importance × gap severity
    """
    return round(weight * gap, 3)


def classify_root_cause(missing_skills, resume_score, github_score, leetcode_score):
    if missing_skills:
        return "Skill Gap"
    elif github_score < 0.4:
        return "Project Weakness"
    elif leetcode_score < 0.4:
        return "DSA Weakness"
    elif resume_score < 0.4:
        return "Profile Weakness"
    else:
        return "Mixed"


# -------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------
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
    Upgraded deterministic failure diagnosis.
    Fully compatible with ROLE_POLICIES.
    No learning path logic included.
    """

    policy = ROLE_POLICIES.get(role_policy, ROLE_POLICIES["default"])

    primary_reasons: List[Dict] = []
    secondary_reasons: List[Dict] = []
    recommendations: List[Dict] = []

    # Extract scores
    resume_score = resume_jd.get("final_match_score", 0)
    github_score = github.get("score", 0)
    leetcode_score = leetcode.get("score", 0)

    missing_skills = resume_jd.get("missing_skills", [])
    matched_skills = resume_jd.get("matched_skills", [])

    # -------------------------------------------------
    # ROOT CAUSE
    # -------------------------------------------------
    root_cause = classify_root_cause(
        missing_skills, resume_score, github_score, leetcode_score
    )

    # -------------------------------------------------
    # SKILL GAP ANALYSIS (PRIMARY DRIVER)
    # -------------------------------------------------
    for skill in missing_skills:
        # Default weight if not provided
        weight = 0.2 if isinstance(skill, str) else skill.get("weight", 0.2)
        skill_name = skill if isinstance(skill, str) else skill.get("skill")

        impact = compute_impact(weight, 1)

        reason_obj = {
            "reason": f"Missing skill: {skill_name}",
            "skill": skill_name,
            "impact_score": impact,
            "severity": "HIGH" if impact >= 0.15 else "MEDIUM"
        }

        if impact >= 0.15:
            primary_reasons.append(reason_obj)
        else:
            secondary_reasons.append(reason_obj)

        recommendations.append({
            "type": "skill",
            "priority": "HIGH" if impact >= 0.15 else "MEDIUM",
            "recommendation": skill_name,
            "linked_skill": skill_name,
            "source": "failure_diagnosis"
        })

    # -------------------------------------------------
    # RESUME–JD ALIGNMENT
    # -------------------------------------------------
    if resume_score < policy["resume_min"]:
        impact = round(policy["resume_min"] - resume_score, 3)

        secondary_reasons.append({
            "reason": "Low resume–JD alignment",
            "details": f"Score: {round(resume_score, 2)}",
            "impact_score": impact,
            "severity": "MEDIUM"
        })

        recommendations.append({
            "type": "resume",
            "priority": "MEDIUM",
            "recommendation": "improve_resume_alignment",
            "linked_skill": "resume",
            "source": "failure_diagnosis"
        })

    # -------------------------------------------------
    # GITHUB ANALYSIS
    # -------------------------------------------------
    if "github" in role_policy:
        if github_score < policy["github_min"]:
            impact = round(policy["github_min"] - github_score, 3)

            secondary_reasons.append({
                "reason": "Weak GitHub signal",
                "details": f"Score: {round(github_score, 2)}",
                "impact_score": impact,
                "severity": "MEDIUM"
            })

            recommendations.append({
                "type": "project",
                "priority": "MEDIUM",
                "recommendation": "github_projects",
                "linked_skill": "projects",
                "source": "failure_diagnosis"
            })

    # -------------------------------------------------
    # LEETCODE / DSA ANALYSIS
    # -------------------------------------------------
    if "leetcode" in role_policy:
        if leetcode_score < policy["leetcode_min"]:
            impact = round(policy["leetcode_min"] - leetcode_score, 3)

            secondary_reasons.append({
                "reason": "Insufficient DSA strength",
                "details": f"Score: {round(leetcode_score, 2)}",
                "impact_score": impact,
                "severity": "MEDIUM"
            })

            recommendations.append({
                "type": "dsa",
                "priority": "MEDIUM",
                "recommendation": "data_structures",
                "linked_skill": "data structures",
                "source": "failure_diagnosis"
            })

    # -------------------------------------------------
    # CRITICAL RESUME FAILURE
    # -------------------------------------------------
    if resume_score < policy["resume_critical"] and not matched_skills:
        primary_reasons.append({
            "reason": "No role-relevant skills or projects in resume",
            "impact_score": round(policy["resume_critical"] - resume_score, 3),
            "severity": "HIGH"
        })

        recommendations.append({
            "type": "resume",
            "priority": "HIGH",
            "recommendation": "add_projects_and_skills",
            "linked_skill": "resume",
            "source": "failure_diagnosis"
        })

    # -------------------------------------------------
    # SIGNAL BREAKDOWN (EXPLAINABILITY)
    # -------------------------------------------------
    total_skills = len(matched_skills) + len(missing_skills) + 1e-5

    signal_breakdown = {
        "skills": round(len(matched_skills) / total_skills, 2),
        "resume": round(resume_score, 2),
        "github": round(github_score, 2),
        "leetcode": round(leetcode_score, 2)
    }

    # -------------------------------------------------
    # DECISION
    # -------------------------------------------------
    decision = "reject" if final_score < threshold else "review"

    # -------------------------------------------------
    # FINAL OUTPUT
    # -------------------------------------------------
    return {
        "decision": decision,
        "root_cause": root_cause,
        "final_score": round(final_score, 2),

        "primary_reasons": primary_reasons,
        "secondary_reasons": secondary_reasons,

        "signal_breakdown": signal_breakdown,

        "actionable_recommendations": recommendations,

        "explainability": "Rule-based diagnosis with impact scoring and role-aware thresholds"
    }