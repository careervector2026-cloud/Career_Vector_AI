# placement_probability.py

USE_ML = False


ROLE_MARKET_FACTOR = {
    "frontend developer": 1.05,
    "backend developer": 1.0,
    "full stack developer": 1.02,
    "data analyst": 0.95,
    "machine learning engineer": 0.90
}


CRITICAL_TECH_STACK = {
    "backend developer": ["spring boot", "microservices", "rest api", "database", "sql"],
    "frontend developer": ["react", "angular", "javascript", "html", "css"],
    "full stack developer": ["react", "node.js", "rest api", "database", "javascript"],
    "data analyst": ["python", "sql", "data analysis", "statistics", "excel"],
    "machine learning engineer": ["python", "machine learning", "tensorflow", "pytorch", "data preprocessing"],
    "devops engineer": ["docker", "kubernetes", "ci/cd", "aws", "linux"],
    "software engineer": ["data structures", "algorithms", "git", "problem solving"]
}


def detect_dynamic_critical_skills(jd_weights):
    return [skill for skill, weight in jd_weights.items() if weight >= 2.5]


def compute_placement_probability(analysis: dict):

    resume_jd = analysis["resume_jd"]
    github = analysis["github"]
    leetcode = analysis["leetcode"]

    readiness = analysis["job_readiness"]["job_readiness_score"]

    role_policy = analysis.get("role_policy", "resume_only")
    role_name = analysis.get("role_name", "").lower()

    final_score = analysis.get("final_score", resume_jd["final_match_score"])
    threshold = analysis.get("threshold", 0.35)
    status = analysis.get("status", "")

    resume_score = resume_jd["final_match_score"] * 100
    github_score = github.get("score", 0) * 100
    leetcode_score = leetcode.get("score", 0) * 100

    if role_policy == "resume_only":
        fit_score = resume_score
    elif role_policy == "resume_github":
        fit_score = 0.80 * resume_score + 0.20 * github_score
    elif role_policy == "resume_leetcode":
        fit_score = 0.80 * resume_score + 0.20 * leetcode_score
    else:
        fit_score = (
            0.65 * resume_score +
            0.20 * github_score +
            0.15 * leetcode_score
        )

    weights = resume_jd.get("jd_skill_weights", {})

    matched_weight = sum(
        weights.get(skill, 1)
        for skill in resume_jd.get("matched_skills", [])
    )

    total_weight = sum(weights.values()) or 1

    weighted_skill_score = (matched_weight / total_weight) * 100

    critical_skills = [
        skill for skill in resume_jd.get("missing_skills", [])
        if weights.get(skill, 1) >= 2.5
    ]

    penalty_weight = sum(weights.get(skill, 1) for skill in critical_skills)
    critical_skill_penalty = (penalty_weight / total_weight) * 20 if critical_skills else 0

    tech_penalty = 0
    missing_skills = resume_jd.get("missing_skills", [])

    static_tech = CRITICAL_TECH_STACK.get(role_name, [])
    dynamic_tech = detect_dynamic_critical_skills(weights)

    for tech in set(static_tech + dynamic_tech):
        if tech in missing_skills:
            tech_penalty += 4

    tech_penalty = min(tech_penalty, 10)

    margin = max(final_score - threshold, 0)
    threshold_advantage = min((margin / (1 - threshold)) * 100, 100)

    jd_skill_count = len(weights)

    if jd_skill_count > 15:
        difficulty_factor = 0.95
    elif jd_skill_count > 10:
        difficulty_factor = 0.98
    else:
        difficulty_factor = 1.0

    market_factor = ROLE_MARKET_FACTOR.get(role_name, 1.0)

    deterministic_probability = (
        0.35 * fit_score +
        0.30 * readiness +
        0.25 * weighted_skill_score +
        0.10 * threshold_advantage
        - critical_skill_penalty
        - tech_penalty
    )

    deterministic_probability *= difficulty_factor * market_factor

    if status == "shortlist":
        deterministic_probability += 5
    elif status == "review":
        deterministic_probability += 2

    deterministic_probability = max(min(deterministic_probability, 100), 0)

    if USE_ML:
        try:
            from placement_probability_ml import predict_probability_ml
            final_probability = predict_probability_ml({})
            method = "ml"
        except Exception:
            final_probability = deterministic_probability
            method = "rule_based_fallback"
    else:
        final_probability = deterministic_probability
        method = "rule_based"

    final_probability = round(final_probability, 2)

    if final_probability >= 85:
        level = "Very High"
    elif final_probability >= 70:
        level = "High"
    elif final_probability >= 45:
        level = "Medium"
    elif final_probability >= 25:
        level = "Low"
    else:
        level = "Very Low"

    return {
        "placement_probability": final_probability,
        "probability_level": level,
        "method": method
    }