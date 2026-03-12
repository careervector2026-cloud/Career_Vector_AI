# placement_probability.py

from placement_probability_logger import log_placement_probability_sample


# -------------------------------------------------
# ML SWITCH
# -------------------------------------------------

USE_ML = False


# -------------------------------------------------
# MARKET CALIBRATION
# -------------------------------------------------

ROLE_MARKET_FACTOR = {
    "frontend developer": 1.05,
    "backend developer": 1.0,
    "full stack developer": 1.02,
    "data analyst": 0.95,
    "machine learning engineer": 0.90
}


# -------------------------------------------------
# CRITICAL TECH STACK (STATIC)
# -------------------------------------------------

CRITICAL_TECH_STACK = {

    "backend developer": [
        "spring boot",
        "microservices",
        "rest api",
        "database",
        "sql"
    ],

    "frontend developer": [
        "react",
        "angular",
        "javascript",
        "html",
        "css"
    ],

    "full stack developer": [
        "react",
        "node.js",
        "rest api",
        "database",
        "javascript"
    ],

    "data analyst": [
        "python",
        "sql",
        "data analysis",
        "statistics",
        "excel"
    ],

    "machine learning engineer": [
        "python",
        "machine learning",
        "tensorflow",
        "pytorch",
        "data preprocessing"
    ],

    "devops engineer": [
        "docker",
        "kubernetes",
        "ci/cd",
        "aws",
        "linux"
    ],

    "software engineer": [
        "data structures",
        "algorithms",
        "git",
        "problem solving"
    ]
}


# -------------------------------------------------
# DYNAMIC JD CRITICAL SKILL DETECTOR
# -------------------------------------------------

def detect_dynamic_critical_skills(jd_weights):

    dynamic_skills = []

    for skill, weight in jd_weights.items():

        if weight >= 2.5:

            dynamic_skills.append(skill)

    return dynamic_skills


# -------------------------------------------------
# CORE PROBABILITY FUNCTION
# -------------------------------------------------

def compute_placement_probability(analysis: dict):

    resume_jd = analysis["resume_jd"]
    github = analysis["github"]
    leetcode = analysis["leetcode"]

    readiness = analysis["job_readiness"]["job_readiness_score"]

    role_policy = analysis.get("role_policy", "resume_only")
    role_name = analysis.get("role_name", "").lower()

    final_score = analysis.get(
        "final_score",
        resume_jd["final_match_score"]
    )

    threshold = analysis.get("threshold", 0.35)

    status = analysis.get("status", "")

    # -------------------------------------------------
    # BASE SIGNALS
    # -------------------------------------------------

    resume_score = resume_jd["final_match_score"] * 100
    github_score = github.get("score", 0) * 100
    leetcode_score = leetcode.get("score", 0) * 100

    # -------------------------------------------------
    # ROLE POLICY FIT SCORE
    # -------------------------------------------------

    if role_policy == "resume_only":

        fit_score = resume_score

    elif role_policy == "resume_github":

        fit_score = (
            0.80 * resume_score +
            0.20 * github_score
        )

    elif role_policy == "resume_leetcode":

        fit_score = (
            0.80 * resume_score +
            0.20 * leetcode_score
        )

    else:

        fit_score = (
            0.65 * resume_score +
            0.20 * github_score +
            0.15 * leetcode_score
        )

    # -------------------------------------------------
    # WEIGHTED SKILL COVERAGE
    # -------------------------------------------------

    weights = resume_jd.get("jd_skill_weights", {})

    matched_weight = sum(
        weights.get(skill, 1)
        for skill in resume_jd.get("matched_skills", [])
    )

    total_weight = sum(weights.values()) or 1

    weighted_skill_score = (
        matched_weight / total_weight
    ) * 100

    # -------------------------------------------------
    # CRITICAL SKILL PENALTY (WEIGHT BASED)
    # -------------------------------------------------

    critical_skills = [
        skill
        for skill in resume_jd.get("missing_skills", [])
        if weights.get(skill, 1) >= 2.5
    ]

    if critical_skills:

        penalty_weight = sum(
            weights.get(skill, 1)
            for skill in critical_skills
        )

        critical_skill_penalty = (
            penalty_weight / total_weight
        ) * 20

    else:

        critical_skill_penalty = 0

    # -------------------------------------------------
    # TECHNOLOGY STACK PENALTY
    # -------------------------------------------------

    tech_penalty = 0

    missing_skills = resume_jd.get("missing_skills", [])

    static_tech = CRITICAL_TECH_STACK.get(role_name, [])

    dynamic_tech = detect_dynamic_critical_skills(weights)

    critical_tech = list(set(static_tech + dynamic_tech))

    for tech in critical_tech:

        if tech in missing_skills:

            tech_penalty += 4

    tech_penalty = min(tech_penalty, 10)

    # -------------------------------------------------
    # THRESHOLD ADVANTAGE
    # -------------------------------------------------

    margin = max(final_score - threshold, 0)

    threshold_advantage = min(
        (margin / (1 - threshold)) * 100,
        100
    )

    # -------------------------------------------------
    # JD DIFFICULTY NORMALIZATION
    # -------------------------------------------------

    jd_skill_count = len(weights)

    if jd_skill_count > 15:
        difficulty_factor = 0.95
    elif jd_skill_count > 10:
        difficulty_factor = 0.98
    else:
        difficulty_factor = 1.0

    # -------------------------------------------------
    # MARKET CALIBRATION
    # -------------------------------------------------

    market_factor = ROLE_MARKET_FACTOR.get(
        role_name,
        1.0
    )

    # -------------------------------------------------
    # BASE PROBABILITY
    # -------------------------------------------------

    deterministic_probability = (
        0.35 * fit_score +
        0.30 * readiness +
        0.25 * weighted_skill_score +
        0.10 * threshold_advantage
        - critical_skill_penalty
        - tech_penalty
    )

    deterministic_probability = (
        deterministic_probability *
        difficulty_factor *
        market_factor
    )

    # -------------------------------------------------
    # STATUS BOOST
    # -------------------------------------------------

    status_boost = 0

    if status == "shortlist":
        status_boost = 5

    elif status == "review":
        status_boost = 2

    deterministic_probability += status_boost

    deterministic_probability = max(
        min(deterministic_probability, 100),
        0
    )

    # -------------------------------------------------
    # ML HOOK
    # -------------------------------------------------

    if USE_ML:

        try:

            from placement_probability_ml import predict_probability_ml

            final_probability = predict_probability_ml({
                "fit_score": fit_score,
                "job_readiness": readiness,
                "weighted_skill_score": weighted_skill_score,
                "threshold_advantage": threshold_advantage
            })

            method = "ml"

        except Exception:

            final_probability = deterministic_probability
            method = "rule_based_fallback"

    else:

        final_probability = deterministic_probability
        method = "rule_based"

    final_probability = round(final_probability, 2)

    # -------------------------------------------------
    # PROBABILITY LEVEL
    # -------------------------------------------------

    level_score = round(final_probability)

    if level_score >= 85:
        level = "Very High"
    elif level_score >= 70:
        level = "High"
    elif level_score >= 45:
        level = "Medium"
    elif level_score >= 25:
        level = "Low"
    else:
        level = "Very Low"

    # -------------------------------------------------
    # EXPLAINABILITY BREAKDOWN
    # -------------------------------------------------

    breakdown = {
        "fit_score": round(fit_score, 2),
        "job_readiness": round(readiness, 2),
        "weighted_skill_score": round(weighted_skill_score, 2),
        "threshold_advantage": round(threshold_advantage, 2),
        "critical_skill_penalty": round(critical_skill_penalty, 2),
        "tech_penalty": tech_penalty,
        "jd_difficulty_factor": difficulty_factor,
        "market_factor": market_factor,
        "status_boost": status_boost,
        "resume_signal": round(resume_score, 2),
        "github_signal": round(github_score, 2),
        "leetcode_signal": round(leetcode_score, 2),
        "role_policy": role_policy
    }

    # -------------------------------------------------
    # LOG FOR ML TRAINING
    # -------------------------------------------------

    log_placement_probability_sample(
        breakdown=breakdown,
        probability=final_probability,
        status=status
    )

    # -------------------------------------------------
    # FINAL OUTPUT
    # -------------------------------------------------

    return {
        "placement_probability": final_probability,
        "probability_level": level,
        "method": method,
        "factors": breakdown
    }