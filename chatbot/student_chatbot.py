from chatbot.career_advisor import recommend_best_roles

from chatbot.chatbot_memory import update_session, read_session
from chatbot.chatbot_intent_engine import detect_intent_semantic
from chatbot.chatbot_response_generator import generate_response

from db.cache_repo import get_cached_analysis

from pipeline.orchestrator import (
    analyze_candidate_async,
    match_student_against_multiple_jds_async,
    build_jd_context
)

from intelligence.learning_path import generate_learning_path

from utils.cache import generate_cache_key


# -------------------------------------------------
# 🔥 CENTRALIZED CACHE HANDLER
# -------------------------------------------------
async def get_or_compute_analysis(
    resume_url,
    job_description,
    github_url,
    leetcode_username,
    college_name=None,
    student_id=None
):
    cache_key = generate_cache_key(
        resume_url,
        job_description,
        github_url,
        leetcode_username,
        student_id
    )

    cached = await get_cached_analysis(cache_key)
    if cached:
        return cached

    jd_context = await build_jd_context(job_description)

    result = await analyze_candidate_async(
        resume_url=resume_url,
        jd_context=jd_context,
        github_url=github_url,
        leetcode_username=leetcode_username,
        college_name=college_name,
        student_id=student_id
    )

    return result


# -------------------------------------------------
# MAIN CHATBOT ROUTER
# -------------------------------------------------
async def student_chatbot_router(
    query: str,
    resume_url: str,
    job_description: str = None,
    github_url: str = None,
    leetcode_username: str = None,
    jds: list = None,
    student_id: str = None,
    college_name: str = None
):

    intent = detect_intent_semantic(query)

    # 🔥 SESSION KEY FIX
    session_key = f"{student_id}:{resume_url}"

    # 🔥 JD REQUIRED CHECK
    if intent in ["JOB_READINESS", "SKILL_GAP", "FAILURE_REASON", "LEARNING_PATH", "INTERVIEW"]:
        if not job_description:
            return {
                "intent": intent,
                "message": "Please provide a job description to proceed."
            }

    # -------------------------------------------------
    # JOB READINESS
    # -------------------------------------------------
    if intent == "JOB_READINESS":

        result = await get_or_compute_analysis(
            resume_url,
            job_description,
            github_url,
            leetcode_username,
            college_name,
            student_id
        )

        update_session(session_key, "last_analysis", result)
        update_session(session_key, "last_jd", job_description)

        response = {
            "intent": intent,
            "job_readiness": result["job_readiness"]
        }

        response["message"] = generate_response(intent, response)
        return response

    # -------------------------------------------------
    # SKILL GAP
    # -------------------------------------------------
    elif intent == "SKILL_GAP":

        last_analysis = read_session(session_key, "last_analysis")

        if last_analysis:
            skill_gap = {
                "matched_skills": last_analysis["resume_jd"]["matched_skills"],
                "missing_skills": last_analysis["resume_jd"]["missing_skills"]
            }
        else:
            result = await get_or_compute_analysis(
                resume_url,
                job_description,
                github_url,
                leetcode_username,
                college_name,
                student_id
            )

            skill_gap = {
                "matched_skills": result["resume_jd"]["matched_skills"],
                "missing_skills": result["resume_jd"]["missing_skills"]
            }

        update_session(session_key, "last_skill_gap", skill_gap)

        response = {
            "intent": intent,
            "skill_gap": skill_gap
        }

        response["message"] = generate_response(intent, response)
        return response

    # -------------------------------------------------
    # JOB MATCH
    # -------------------------------------------------
    elif intent == "JOB_MATCH":

        student_profile = {
            "resume_url": resume_url,
            "github_url": github_url,
            "leetcode_username": leetcode_username,
            "student_id": student_id,
            "college_name": college_name
        }

        if not jds and job_description:
            jds = [{"job_description": job_description}]

        if jds and isinstance(jds[0], str):
            jds = [{"job_description": jd} for jd in jds]

        if not jds:
            return {
                "intent": intent,
                "message": "Please provide at least one job description."
            }

        result = await match_student_against_multiple_jds_async(
            student_profile,
            jds
        )

        update_session(session_key, "last_jds", jds)

        response = {
            "intent": intent,
            "matches": result[:5]
        }

        response["message"] = generate_response(intent, response)
        return response

    # -------------------------------------------------
    # FAILURE DIAGNOSIS
    # -------------------------------------------------
    elif intent == "FAILURE_REASON":

        last_analysis = read_session(session_key, "last_analysis")

        if last_analysis:
            result = last_analysis
        else:
            result = await get_or_compute_analysis(
                resume_url,
                job_description,
                github_url,
                leetcode_username,
                college_name,
                student_id
            )

        if result["status"] == "shortlist":
            return {
                "intent": intent,
                "message": "You are shortlisted. Failure diagnosis is not applicable."
            }

        response = {
            "intent": intent,
            "failure_diagnosis": result.get("failure_diagnosis")
        }

        response["message"] = generate_response(intent, response)
        return response

    # -------------------------------------------------
    # LEARNING PATH
    # -------------------------------------------------
    elif intent == "LEARNING_PATH":

        skill_gap = read_session(session_key, "last_skill_gap")

        if not skill_gap:
            result = await get_or_compute_analysis(
                resume_url,
                job_description,
                github_url,
                leetcode_username,
                college_name,
                student_id
            )

            skill_gap = {
                "missing_skills": result["resume_jd"]["missing_skills"]
            }

        missing = [
            x["skill"] if isinstance(x, dict) else x
            for x in skill_gap["missing_skills"]
        ]

        if not missing:
            return {
                "intent": intent,
                "message": "You already match most required skills. Focus on projects and interviews."
            }

        roadmap = generate_learning_path(
            target_role="backend developer",
            missing_skills=missing,
            weak_skills=[],
            student_id=student_id
        )

        response = {
            "intent": intent,
            "learning_path": roadmap
        }

        response["message"] = generate_response(intent, response)
        return response

    # -------------------------------------------------
    # CAREER ADVICE
    # -------------------------------------------------
    elif intent == "CAREER_ADVICE":

        stored_jds = read_session(session_key, "last_jds")

        if not jds and stored_jds:
            jds = stored_jds

        student_profile = {
            "resume_url": resume_url,
            "github_url": github_url,
            "leetcode_username": leetcode_username,
            "student_id": student_id,
            "college_name": college_name
        }

        recommendations = await recommend_best_roles(
            student_profile,
            jds
        )

        response = {
            "intent": intent,
            "career_recommendations": recommendations
        }

        response["message"] = generate_response(intent, response)
        return response

    # -------------------------------------------------
    # INTERVIEW
    # -------------------------------------------------
    elif intent == "INTERVIEW":

        result = await get_or_compute_analysis(
            resume_url,
            job_description,
            github_url,
            leetcode_username,
            college_name,
            student_id
        )

        role = result.get("role_level", "software engineer")

        return {
            "intent": intent,
            "message": f"Let's start your interview practice for the role: {role}.",
            "next_action": "interview",
            "role": role
        }

    # -------------------------------------------------
    # UNKNOWN
    # -------------------------------------------------
    return {
        "intent": "UNKNOWN",
        "message": "I'm not sure how to answer that. You can ask about job readiness, skill gaps, career advice, or interview preparation."
    }