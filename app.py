import asyncio

from fastapi import FastAPI, Request, HTTPException
from urllib.parse import parse_qs

from ats_resume_fixer import generate_ats_fix_suggestions
from ats_screening import compute_ats_screening
from interview.github_question_generator import generate_github_questions
from interview.github_repo_fetcher import fetch_github_repositories
from learning_path import generate_learning_path
from failure_analytics import generate_failure_analytics
from fastapi import Query

from matcher import resume_jd_match, extract_skills
from orchestrator import build_jd_context
import json

from orchestrator import (
    analyze_candidate_async,
    rank_candidates_against_jd_async,
    match_student_against_multiple_jds_async,
    generate_skill_gap_report,
    recommend_career_paths,
    generate_market_demand_heatmap
)
from talent_search import search_talent_pool

app = FastAPI()


# -------------------------------------------------
# ANALYZE SINGLE CANDIDATE
# -------------------------------------------------
@app.post("/analyze")
async def analyze(request: Request):

    data = await request.json()

    if not data.get("resume_url") or not data.get("job_description"):
        raise HTTPException(422, "resume_url and job_description required")

    jd_context = await build_jd_context(data["job_description"])

    return await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_context=jd_context,
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username")
    )
# -------------------------------------------------
# RANK MULTIPLE CANDIDATES AGAINST ONE JD
# -------------------------------------------------
@app.post("/rank-candidates")
async def rank_candidates(request: Request):
    data = await request.json()

    if not data.get("job_description") or not data.get("candidates"):
        raise HTTPException(422, "job_description and candidates required")

    return await rank_candidates_against_jd_async(
        jd_text=data["job_description"],
        candidates=data["candidates"]
    )

# --------------------------------------------------------------------------
# RANK MULTIPLE CANDIDATES AGAINST ONE JD with minimal data sent as response
# --------------------------------------------------------------------------
@app.post("/rank-candidates-summary")
async def rank_candidates_summary(request: Request):
    data = await request.json()

    if not data.get("job_description") or not data.get("candidates"):
        raise HTTPException(422, "job_description and candidates required")

    results = await rank_candidates_against_jd_async(
        jd_text=data["job_description"],
        candidates=data["candidates"]
    )

    # Return only minimal fields for Java backend
    return [
        {
            "candidate_id": r["candidate_id"],
            "rank": r["rank"],
            "final_score": r["final_score"],
            "status": r["status"]
        }
        for r in results
    ]


# -------------------------------------------------
# MATCH ONE STUDENT AGAINST MULTIPLE JDs
# -------------------------------------------------

@app.post("/match-student-jds")
async def match_student_jds(
    request: Request,
    mode: str = Query("full", enum=["full", "lite"])
):
    try:
        data = await request.json()

        student = data.get("student_profile")
        jds = data.get("jds")

        if not student or not jds:
            raise HTTPException(
                status_code=422,
                detail="student_profile and jds are required"
            )

        results = await match_student_against_multiple_jds_async(
            student_profile=student,
            jds=jds
        )

        # 🔹 LITE RESPONSE FOR SPRING BOOT
        if mode == "lite":
            return [
                {
                    "jd_id": r["jd_id"],
                    "rank": r["rank"],
                    "final_score": r["final_score"],
                    "status": r["status"],
                    "reason": r["reason"],
                    "role_level": r["role_level"],
                    "job_readiness_score": r["job_readiness"]["job_readiness_score"],
                    "readiness_level": r["job_readiness"]["readiness_level"],
                }
                for r in results
            ]

        # 🔹 FULL RESPONSE (default)
        return results

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# SKILL GAP REPORT
# -------------------------------------------------
@app.post("/skill-gap-report")
async def skill_gap_report(request: Request):
    data = await request.json()

    return await generate_skill_gap_report(
        resume_url=data["resume_url"],
        jd_text=data["job_description"],
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username")
    )

# -------------------------------------------------
# CAREER PATH RECOMMENDATION
# -------------------------------------------------
@app.post("/career-path")
async def career_path(request: Request):
    data = await request.json()

    return await recommend_career_paths(
        resume_url=data["resume_url"],
        jd_text=data["job_description"]
    )

# -------------------------------------------------
# MARKET DEMAND HEATMAP
# -------------------------------------------------
@app.post("/market-demand")
async def market_demand(request: Request):
    data = await request.json()

    return await generate_market_demand_heatmap(
        jds=data["job_descriptions"]
    )

# -------------------------------------------------
# JOB READINESS (EXISTING)
# -------------------------------------------------
@app.post("/job-readiness")
async def job_readiness(request: Request):
    data = await request.json()

    if not data.get("resume_url") or not data.get("job_description"):
        raise HTTPException(422, "resume_url and job_description required")

    result = await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_text=data["job_description"],
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username")
    )

    return {
        "job_readiness": result["job_readiness"],
        "status": result["status"]
    }

# -------------------------------------------------
# 🆕 FAILURE DIAGNOSIS (NEW FEATURE)
# -------------------------------------------------
@app.post("/failure-diagnosis")
async def failure_diagnosis(request: Request):
    """
    Returns explainable failure diagnosis
    ONLY if candidate is rejected or review.
    """
    data = await request.json()

    if not data.get("resume_url") or not data.get("job_description"):
        raise HTTPException(422, "resume_url and job_description required")

    result = await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_text=data["job_description"],
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username")
    )

    if result["status"] == "shortlist":
        return {
            "message": "Candidate shortlisted. Failure diagnosis not applicable."
        }

    return {
        "status": result["status"],
        "final_score": result["final_score"],
        "threshold": result["threshold"],
        "failure_diagnosis": result.get("failure_diagnosis")
    }
# -------------------------------------------------
# 🆕 LEARNING PATH FROM JD (FIXED)
# -------------------------------------------------
from learning_path import generate_learning_path

def infer_target_role_from_jd(jd_text: str) -> str:
    jd = jd_text.lower()

    role_scores = {
        "Frontend Developer": 0,
        "Backend Developer": 0,
        "Machine Learning Engineer": 0
    }

    # -------------------------
    # Frontend Indicators
    # -------------------------
    frontend_keywords = [
        "react", "angular", "vue",
        "frontend developer",
        "responsive web",
        "ui/ux",
        "html", "css",
        "javascript", "typescript"
    ]

    # -------------------------
    # Backend Indicators
    # -------------------------
    backend_keywords = [
        "spring boot",
        "backend developer",
        "java",
        "microservices",
        "hibernate",
        "jpa",
        "sql",
        "database"
    ]

    # -------------------------
    # ML Indicators
    # -------------------------
    ml_keywords = [
        "machine learning",
        "data scientist",
        "deep learning",
        "tensorflow",
        "pytorch"
    ]

    for kw in frontend_keywords:
        if kw in jd:
            role_scores["Frontend Developer"] += 1

    for kw in backend_keywords:
        if kw in jd:
            role_scores["Backend Developer"] += 1

    for kw in ml_keywords:
        if kw in jd:
            role_scores["Machine Learning Engineer"] += 1

    # Choose highest score
    return max(role_scores, key=role_scores.get)
@app.post("/learning-path")
async def learning_path_from_jd(request: Request):
    data = await request.json()

    if not data.get("resume_url") or not data.get("job_description"):
        raise HTTPException(
            422,
            "resume_url and job_description are required"
        )

    # Step 1: Analyze candidate
    result = await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_text=data["job_description"],
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username")
    )

    resume_jd = result["resume_jd"]

    missing_skills = resume_jd.get("missing_skills", [])
    matched_skills = resume_jd.get("matched_skills", [])

    # Optional: define weak skills (example rule)
    weights = resume_jd["jd_skill_weights"]

    weak_skills = [
        s for s in matched_skills
        if weights.get(s, 0) >= 2.0
    ]
    # Step 2: Infer correct role
    target_role = infer_target_role_from_jd(data["job_description"])

    # Step 3: Generate roadmap
    roadmap = generate_learning_path(
        target_role=target_role,
        missing_skills=missing_skills,
        weak_skills=weak_skills,
        student_id=None
    )

    return roadmap


@app.post("/ats-check")
async def ats_check(request: Request):

    try:
        data = await request.json()

        resume_url = data.get("resume_url")
        jd_text = data.get("job_description")

        if not resume_url or not jd_text:

            raise HTTPException(
                status_code=422,
                detail="resume_url and job_description are required"
            )

        # Resume ↔ JD match
        resume_jd = await asyncio.to_thread(
            resume_jd_match,
            resume_url,
            jd_text
        )

        # ATS Screening
        ats_result = compute_ats_screening(resume_jd)

        # ATS Fix Suggestions
        suggestions = generate_ats_fix_suggestions(
            resume_jd,
            ats_result
        )

        return {
            "ats_screening": ats_result,
            "resume_jd": resume_jd,
            "fix_suggestions": suggestions
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/talent-search")
async def talent_search(request: Request):

    try:

        data = await request.json()

        query = data.get("query")
        candidates = data.get("candidates")
        top_k = data.get("top_k", 10)

        if not query or not candidates:

            raise HTTPException(
                status_code=422,
                detail="query and candidates are required"
            )

        results = await search_talent_pool(
            query,
            candidates,
            top_k
        )

        return {
            "query": query,
            "results": results
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/failure-analytics")
def failure_analytics(decision_filter: str = "ALL"):
    return generate_failure_analytics(decision_filter)

from interview.interview_engine import generate_questions
from interview.answer_analyzer import evaluate_interview
from interview.github_repo_fetcher import fetch_github_repositories


@app.post("/generate-interview-questions")
async def generate_interview_questions(payload: dict):

    missing_skills = payload.get("missing_skills", [])
    matched_skills = payload.get("matched_skills", [])

    github_url = payload.get("github_url")

    github_score = payload.get("github_score", 0.0)
    leetcode_score = payload.get("leetcode_score", 0.0)
    readiness_score = payload.get("readiness_score", 0.0)

    n_questions = payload.get("n_questions", 10)

    github_data = {"repositories": []}

    if github_url:
        github_data = await fetch_github_repositories(github_url)

    questions = generate_questions(
        missing_skills,
        matched_skills,
        github_data,
        github_score,
        leetcode_score,
        readiness_score,
        n_questions
    )

    return {"questions": questions}


@app.post("/evaluate-interview")
def evaluate_interview_api(payload: dict):

    answers = payload.get("answers", [])

    result = evaluate_interview(answers)

    return result

from interview.adaptive_interview_engine import AdaptiveInterview

interview_sessions = {}


@app.post("/start-adaptive-interview")
async def start_adaptive_interview(payload: dict):

    candidate_id = payload["candidate_id"]
    jd_text = payload["jd_text"]
    resume_url = payload["resume_url"]
    github_url = payload.get("github_url")

    n_questions = payload.get("n_questions", 7)

    session = AdaptiveInterview(jd_text, resume_url, github_url, n_questions)

    await session.initialize_pipeline()
    interview_sessions[candidate_id] = session

    question = session.next_question()

    return {"question": question}

@app.post("/adaptive-interview-answer")
def adaptive_answer(payload: dict):

    candidate_id = payload["candidate_id"]
    answer = payload["answer"]

    session = interview_sessions.get(candidate_id)

    if not session:
        return {"error": "Interview session not found"}

    score = session.submit_answer(answer)

    next_q = session.next_question()

    return {
        "score": score,
        "next_question": next_q
    }