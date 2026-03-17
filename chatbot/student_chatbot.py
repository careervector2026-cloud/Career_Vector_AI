from chatbot.career_advisor import recommend_best_roles

from chatbot.chatbot_memory import update_session, read_session
from chatbot.chatbot_intent_engine import detect_intent_semantic
from chatbot.chatbot_response_generator import generate_response
from chatbot.analysis_cache import get_cached_analysis, store_analysis

from pipeline.orchestrator import (
    analyze_candidate_async,
    generate_skill_gap_report,
    match_student_against_multiple_jds_async,
    build_jd_context
)

from intelligence.learning_path import generate_learning_path

# -------------------------------------------------
# MAIN CHATBOT ROUTER
# -------------------------------------------------

async def student_chatbot_router(
    query: str,
    resume_url: str,
    job_description: str = None,
    github_url: str = None,
    leetcode_username: str = None,
    jds: list = None
):

    intent = detect_intent_semantic(query)

    cache_key = f"{resume_url}:{job_description}"

    # -----------------------------------------
    # JOB READINESS
    # -----------------------------------------

    if intent == "JOB_READINESS":

        jd_context = await build_jd_context(job_description)

        cached = get_cached_analysis(cache_key)

        if cached:
            result = cached
        else:
            result = await analyze_candidate_async(
                resume_url=resume_url,
                jd_context=jd_context,
                github_url=github_url,
                leetcode_username=leetcode_username
            )
            store_analysis(cache_key, result)

        update_session(resume_url, "last_analysis", result)
        update_session(resume_url, "last_jd", job_description)

        response = {
            "intent": intent,
            "job_readiness": result["job_readiness"]
        }

        response["message"] = generate_response(intent, response)

        return response

    # -----------------------------------------
    # SKILL GAP
    # -----------------------------------------

    elif intent == "SKILL_GAP":

        last_analysis = read_session(resume_url, "last_analysis")

        if last_analysis:

            skill_gap = {
                "matched_skills": last_analysis["resume_jd"]["matched_skills"],
                "missing_skills": last_analysis["resume_jd"]["missing_skills"]
            }

        else:

            cached = get_cached_analysis(cache_key)

            if cached:
                skill_gap = {
                    "matched_skills": cached["resume_jd"]["matched_skills"],
                    "missing_skills": cached["resume_jd"]["missing_skills"]
                }

            else:

                result = await generate_skill_gap_report(
                    resume_url,
                    job_description,
                    github_url,
                    leetcode_username
                )

                skill_gap = result

        update_session(resume_url, "last_skill_gap", skill_gap)

        response = {
            "intent": intent,
            "skill_gap": skill_gap
        }

        response["message"] = generate_response(intent, response)

        return response

    # -----------------------------------------
    # JOB MATCHING
    # -----------------------------------------

    elif intent == "JOB_MATCH":
        student_profile = {
            "resume_url": resume_url,
            "github_url": github_url,
            "leetcode_username": leetcode_username
        }
        # convert single JD to list
        if not jds and job_description:
            jds = [{"job_description": job_description}]
        # convert string JDs to dict format
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
        update_session(resume_url, "last_jds", jds)
        response = {

            "intent": intent,
            "matches": result[:5]

        }
        response["message"] = generate_response(intent, response)
        return response

    # -----------------------------------------
    # FAILURE DIAGNOSIS
    # -----------------------------------------

    elif intent == "FAILURE_REASON":

        last_analysis = read_session(resume_url, "last_analysis")

        if last_analysis:

            result = last_analysis

        else:

            cached = get_cached_analysis(cache_key)

            if cached:
                result = cached
            else:

                jd_context = await build_jd_context(job_description)

                result = await analyze_candidate_async(
                    resume_url,
                    jd_context,
                    github_url,
                    leetcode_username
                )

                store_analysis(cache_key, result)

        if result["status"] == "shortlist":

            response = {
                "intent": intent,
                "message": "You are shortlisted. Failure diagnosis is not applicable."
            }

            return response

        response = {
            "intent": intent,
            "failure_diagnosis": result.get("failure_diagnosis")
        }

        response["message"] = generate_response(intent, response)

        return response

    # -----------------------------------------
    # LEARNING PATH
    # -----------------------------------------

    elif intent == "LEARNING_PATH":

        skill_gap = read_session(resume_url, "last_skill_gap")

        if not skill_gap:

            result = await generate_skill_gap_report(
                resume_url,
                job_description
            )

            skill_gap = result

        missing = [
            x["skill"] if isinstance(x, dict) else x
            for x in skill_gap["missing_skills"]
        ]

        roadmap = generate_learning_path(
            target_role="backend developer",
            missing_skills=missing,
            weak_skills=[]
        )

        response = {
            "intent": intent,
            "learning_path": roadmap
        }

        response["message"] = generate_response(intent, response)

        return response

    # -----------------------------------------
    # CAREER ADVICE
    # -----------------------------------------

    elif intent == "CAREER_ADVICE":

        stored_jds = read_session(resume_url, "last_jds")

        if not jds and stored_jds:
            jds = stored_jds

        student_profile = {
            "resume_url": resume_url,
            "github_url": github_url,
            "leetcode_username": leetcode_username
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

    # -----------------------------------------
    # INTERVIEW PRACTICE
    # -----------------------------------------

    elif intent == "INTERVIEW":

        jd_context = await build_jd_context(job_description)

        result = await analyze_candidate_async(
            resume_url=resume_url,
            jd_context=jd_context,
            github_url=github_url,
            leetcode_username=leetcode_username
        )

        role = result.get("role_inference", {}).get("role", "software engineer")

        response = {
            "intent": intent,
            "message": f"Let's start your interview practice for the role: {role}.",
            "next_action": "interview",
            "role": role
        }

        return response
    # -----------------------------------------
    # UNKNOWN
    # -----------------------------------------

    response = {
        "intent": "UNKNOWN"
    }

    response["message"] = "I'm not sure how to answer that. You can ask about job readiness, skill gaps, career advice, or interview preparation."

    return response