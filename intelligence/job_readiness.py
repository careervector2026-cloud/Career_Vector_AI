# job_readiness.py

USE_ML = False


def normalize_0_100(x: float) -> float:
    return round(max(min(x * 100, 100), 0), 2)


def experience_alignment_score(role_level: str) -> int:
    return {
        "junior": 100,
        "mid": 75,
        "senior": 50
    }.get(role_level, 50)


def compute_job_readiness_score(analysis: dict) -> dict:

    resume_jd_score = normalize_0_100(
        analysis["resume_jd"]["final_match_score"]
    )

    matched = len(analysis["resume_jd"]["matched_skills"])
    missing = len(analysis["resume_jd"]["missing_skills"])
    total = matched + missing or 1

    skill_coverage = round((matched / total) * 100, 2)

    github_score = normalize_0_100(
        analysis["github"]["score"]
    )

    leetcode_score = normalize_0_100(
        analysis["leetcode"]["score"]
    )

    experience_score = experience_alignment_score(
        analysis["role_level"]
    )

    breakdown = {
        "resume_jd": resume_jd_score,
        "skill_coverage": skill_coverage,
        "experience": experience_score,
        "github": github_score,
        "leetcode": leetcode_score
    }

    deterministic_score = round(
        0.30 * resume_jd_score +
        0.25 * skill_coverage +
        0.20 * experience_score +
        0.15 * github_score +
        0.10 * leetcode_score,
        2
    )

    if USE_ML:
        try:
            from intelligence.job_readiness_ml import predict_job_readiness_ml
            final_score = predict_job_readiness_ml(breakdown)
            method = "ml"
        except Exception:
            final_score = deterministic_score
            method = "rule_based_fallback"
    else:
        final_score = deterministic_score
        method = "rule_based"

    if final_score >= 85:
        level = "Excellent"
    elif final_score >= 70:
        level = "Good"
    elif final_score >= 50:
        level = "Average"
    else:
        level = "Poor"

    return {
        "job_readiness_score": final_score,
        "readiness_level": level,
        "method": method,
        "breakdown": breakdown
    }