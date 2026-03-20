#student_profile_engine.py
import asyncio

from analyzers.matcher import resume_jd_match
from analyzers.github_analyzer import analyze_github_async
from analyzers.leetcode_analyzer import analyze_leetcode_async
from intelligence.job_readiness import compute_job_readiness_score
from chatbot.next_action_engine import recommend_next_action
from intelligence.placement_probability import compute_placement_probability
from intelligence.failure_diagnosis import generate_failure_diagnosis


async def build_student_profile(
    resume_url,
    jd_text,
    github_url=None,
    leetcode_username=None
):

    # -------------------------------------------------
    # Resume ↔ JD Matching
    # -------------------------------------------------

    resume_jd = await asyncio.to_thread(
        resume_jd_match,
        resume_url,
        jd_text
    )

    resume_score = resume_jd["final_match_score"]

    # -------------------------------------------------
    # External Signals
    # -------------------------------------------------

    github_result = {"score": 0.0, "evidence": []}
    leetcode_result = {"score": 0.0}

    if github_url:

        github_result = await analyze_github_async(
            github_url,
            set(resume_jd["jd_skill_weights"].keys())
        )

    if leetcode_username:

        leetcode_result = await analyze_leetcode_async(
            leetcode_username
        )

    # -------------------------------------------------
    # Job Readiness
    # -------------------------------------------------

    job_readiness = compute_job_readiness_score({
        "resume_jd": resume_jd,
        "github": github_result,
        "leetcode": leetcode_result,
        "role_level": "junior"
    })

    # -------------------------------------------------
    # Placement Probability
    # -------------------------------------------------

    placement_probability = compute_placement_probability({
        "resume_jd": resume_jd,
        "github": github_result,
        "leetcode": leetcode_result,
        "job_readiness": job_readiness
    })

    # -------------------------------------------------
    # Simple Final Score Estimate
    # (used for failure diagnosis)
    # -------------------------------------------------

    final_score = round(
        0.6 * resume_score
        + 0.25 * github_result["score"]
        + 0.15 * leetcode_result["score"],
        2
    )

    threshold = 0.40  # junior baseline threshold

    # -------------------------------------------------
    # Failure Diagnosis
    # -------------------------------------------------

    failure_diagnosis = None

    if final_score < threshold:

        failure_diagnosis = generate_failure_diagnosis(
            final_score=final_score,
            threshold=threshold,
            resume_jd=resume_jd,
            github=github_result,
            leetcode=leetcode_result,
            role_policy="resume_github_leetcode",
            role_level="junior"
        )

    # -------------------------------------------------
    # Return Student Profile
    # -------------------------------------------------
    next_action = recommend_next_action({
        "job_readiness": job_readiness,
        "missing_skills": resume_jd["missing_skills"],
        "github_score": github_result["score"],
        "leetcode_score": leetcode_result["score"]
    })
    return {
        "skills": resume_jd["matched_skills"],
        "missing_skills": resume_jd["missing_skills"],
        "github_score": github_result["score"],
        "leetcode_score": leetcode_result["score"],
        "job_readiness": job_readiness,
        "placement_probability": placement_probability,
        "failure_diagnosis": failure_diagnosis,
        "next_action": next_action
    }
