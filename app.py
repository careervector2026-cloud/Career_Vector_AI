#app.py
from fastapi import FastAPI, Request, HTTPException, Query

from admin.admin_dashboard import get_placement_funnel, get_top_students, get_at_risk_students, get_skill_gap_trends, \
    get_student_progression
# ATS
from ats.ats_resume_fixer import generate_ats_fix_suggestions
from ats.ats_screening import compute_ats_screening

# PIPELINE
from pipeline.orchestrator import (
    build_jd_context,
    analyze_candidate_async,
    rank_candidates_against_jd_async,
    match_student_against_multiple_jds_async,
    generate_skill_gap_report,
    recommend_career_paths,
    generate_market_demand_heatmap
)

# OTHER MODULES
from intelligence.failure_analytics import generate_failure_analytics
from intelligence.talent_search import search_talent_pool
from intelligence.learning_path import generate_learning_path

from chatbot.student_chatbot import student_chatbot_router

from interview.interview_engine import generate_questions
from interview.answer_analyzer import evaluate_interview
from interview.github_repo_fetcher import fetch_github_repositories
from interview.adaptive_interview_engine import AdaptiveInterview

from analyzers.resume_parser import parse_resume_from_url
from analyzers.matcher import resume_jd_match_async  # ✅ FIXED

app = FastAPI()

interview_sessions = {}

# -------------------------------------------------
# ANALYZE SINGLE CANDIDATE
# -------------------------------------------------
@app.post("/analyze")
async def analyze(request: Request):

    data = await request.json()

    student_id = data.get("student_id")

    if not data.get("resume_url") or not data.get("job_description") or not student_id:
        raise HTTPException(422, "resume_url, job_description and student_id required")

    jd_context = await build_jd_context(data["job_description"])

    return await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_context=jd_context,
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username"),
        college_name=data.get("college_name"),
        student_id=student_id   # 🔥 NEW
    )

# -------------------------------------------------
# RANK CANDIDATES
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


@app.post("/rank-candidates-summary")
async def rank_candidates_summary(request: Request):

    data = await request.json()

    results = await rank_candidates_against_jd_async(
        jd_text=data["job_description"],
        candidates=data["candidates"]
    )

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
# MATCH STUDENT VS MULTIPLE JDs
# -------------------------------------------------
@app.post("/match-student-jds")
async def match_student_jds(
    request: Request,
    mode: str = Query("full", enum=["full", "lite"])
):

    data = await request.json()

    # ✅ FIXED FIELD NAME
    student = data.get("student_profile")
    jds = data.get("jds")

    if not student or not jds:
        raise HTTPException(
            status_code=422,
            detail="student_profile and jds are required"
        )

    # Handle string JDs
    if isinstance(jds[0], str):
        jds = [{"job_description": jd} for jd in jds]

    results = await match_student_against_multiple_jds_async(
        student_profile=student,
        jds=jds
    )

    if mode == "lite":
        return [
            {
                "jd_id": r.get("jd_id"),
                "rank": r.get("rank"),
                "final_score": r.get("final_score"),
                "status": r.get("status"),
                "reason": r.get("reason"),
                "role_level": r.get("role_level"),
                "job_readiness_score": r["job_readiness"]["job_readiness_score"],
                "readiness_level": r["job_readiness"]["readiness_level"],
            }
            for r in results
        ]

    return results

# -------------------------------------------------
# SKILL GAP
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
# CAREER PATH
# -------------------------------------------------
@app.post("/career-path")
async def career_path(request: Request):

    data = await request.json()

    return await recommend_career_paths(
        resume_url=data["resume_url"],
        jd_text=data["job_description"]
    )

# -------------------------------------------------
# MARKET DEMAND
# -------------------------------------------------
@app.post("/market-demand")
async def market_demand(request: Request):

    data = await request.json()

    return await generate_market_demand_heatmap(
        jds=data["job_descriptions"]
    )

# -------------------------------------------------
# JOB READINESS
# -------------------------------------------------
@app.post("/job-readiness")
async def job_readiness(request: Request):

    data = await request.json()

    student_id = data.get("student_id")

    if not student_id:
        raise HTTPException(422, "student_id required")

    jd_context = await build_jd_context(data["job_description"])

    result = await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_context=jd_context,
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username"),
        college_name=data.get("college_name"),
        student_id=student_id
    )

    return {
        "job_readiness": result["job_readiness"],
        "status": result["status"]
    }
# -------------------------------------------------
# FAILURE DIAGNOSIS
# -------------------------------------------------
@app.post("/failure-diagnosis")
async def failure_diagnosis(request: Request):

    data = await request.json()

    student_id = data.get("student_id")

    if not student_id:
        raise HTTPException(422, "student_id required")

    jd_context = await build_jd_context(data["job_description"])

    result = await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_context=jd_context,
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username"),
        college_name=data.get("college_name"),
        student_id=student_id
    )

    if result["status"] == "shortlist":
        return {"message": "Candidate shortlisted"}

    return {
        "status": result["status"],
        "final_score": result["final_score"],
        "failure_diagnosis": result.get("failure_diagnosis")
    }
# -------------------------------------------------
# FAILURE ANALYTICS
# -------------------------------------------------
@app.get("/failure-analytics")
async def failure_analytics(
    decision_filter: str = "ALL",
    college_name: str = None
):
    """
    Query Params:
    - decision_filter: ALL | reject | review | shortlist
    - college_name: optional
    """

    return await generate_failure_analytics(
        decision_filter=decision_filter,
        college_name=college_name
    )

# -------------------------------------------------
# ATS CHECK (FIXED)
# -------------------------------------------------
@app.post("/ats-check")
async def ats_check(request: Request):

    data = await request.json()

    resume_url = data.get("resume_url")
    jd_text = data.get("job_description")

    if not resume_url or not jd_text:
        raise HTTPException(422, "resume_url and job_description required")

    # ✅ FIX: use async matcher
    resume_jd = await resume_jd_match_async(resume_url, jd_text)

    ats_result = compute_ats_screening(resume_jd)

    suggestions = generate_ats_fix_suggestions(resume_jd, ats_result)

    return {
        "ats_screening": ats_result,
        "resume_jd": resume_jd,
        "fix_suggestions": suggestions
    }

# -------------------------------------------------
# TALENT SEARCH
# -------------------------------------------------
@app.post("/talent-search")
async def talent_search(request: Request):

    data = await request.json()

    return await search_talent_pool(
        data["query"],
        data["candidates"],
        data.get("top_k", 10)
    )

# -------------------------------------------------
# INTERVIEW QUESTIONS
# -------------------------------------------------
@app.post("/generate-interview-questions")
async def generate_interview_questions(payload: dict):

    jd_text = payload.get("jd_text", "")
    resume_url = payload.get("resume_url", "")

    # ✅ FIX: async matcher
    match_result = await resume_jd_match_async(resume_url, jd_text)

    github_data = {"repositories": []}

    if payload.get("github_url"):
        try:
            github_data = await fetch_github_repositories(payload["github_url"])
        except:
            pass

    questions = generate_questions(
        match_result["missing_skills"],
        match_result["matched_skills"],
        github_data,
        0.6, 0.5, 0.6,
        payload.get("n_questions", 10)
    )

    return {
        "matched_skills": match_result["matched_skills"],
        "missing_skills": match_result["missing_skills"],
        "questions": questions
    }

# -------------------------------------------------
# EVALUATE INTERVIEW
# -------------------------------------------------
@app.post("/evaluate-interview")
def evaluate_interview_api(payload: dict):

    result = evaluate_interview(payload.get("answers", []))

    scores = result.get("question_scores", [])

    for q in scores:
        q["score"] = float(q["score"])

    overall = round(sum(q["score"] for q in scores) / len(scores), 3) if scores else 0

    return {
        "question_scores": scores,
        "overall_score": overall
    }

# -------------------------------------------------
# ADAPTIVE INTERVIEW
# -------------------------------------------------
@app.post("/start-adaptive-interview")
async def start_adaptive_interview(payload: dict):

    session = AdaptiveInterview(
        payload["jd_text"],
        payload["resume_url"],
        payload.get("github_url"),
        payload.get("n_questions", 7)
    )

    await session.initialize_pipeline()

    interview_sessions[payload["candidate_id"]] = session

    return {"question": session.next_question()}


@app.post("/adaptive-interview-answer")
def adaptive_answer(payload: dict):

    session = interview_sessions.get(payload["candidate_id"])

    if not session:
        return {"error": "Interview session not found"}

    score = session.submit_answer(payload["answer"])

    return {
        "score": score,
        "next_question": session.next_question()
    }

# -------------------------------------------------
# CHATBOT
# -------------------------------------------------
@app.post("/student-chatbot")
async def student_chatbot(request: Request):

    data = await request.json()

    return await student_chatbot_router(
        query=data["query"],
        resume_url=data["resume_url"],
        job_description=data.get("job_description"),
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username"),
        jds=data.get("jds"),
        student_id=data.get("student_id"),     # 🔥 NEW
        college_name=data.get("college_name")  # 🔥 IMPORTANT
    )
# -------------------------------------------------
# LEARNING PATH FROM JD (RESTORE)
# -------------------------------------------------
def infer_target_role_from_jd(jd_text: str) -> str:
    jd = jd_text.lower()

    role_scores = {
        "Frontend Developer": 0,
        "Backend Developer": 0,
        "Machine Learning Engineer": 0
    }

    frontend_keywords = ["react", "angular", "vue", "html", "css", "javascript"]
    backend_keywords = ["spring boot", "java", "microservices", "sql"]
    ml_keywords = ["machine learning", "tensorflow", "pytorch"]

    for kw in frontend_keywords:
        if kw in jd:
            role_scores["Frontend Developer"] += 1

    for kw in backend_keywords:
        if kw in jd:
            role_scores["Backend Developer"] += 1

    for kw in ml_keywords:
        if kw in jd:
            role_scores["Machine Learning Engineer"] += 1

    return max(role_scores, key=role_scores.get)


@app.post("/learning-path")
async def learning_path_from_jd(request: Request):

    data = await request.json()

    jd_context = await build_jd_context(data["job_description"])

    result = await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_context=jd_context
    )

    resume_jd = result["resume_jd"]

    missing = resume_jd.get("missing_skills", [])
    matched = resume_jd.get("matched_skills", [])
    weights = resume_jd.get("jd_skill_weights", {})

    weak_skills = [s for s in matched if weights.get(s, 0) >= 2.0]

    role = infer_target_role_from_jd(data["job_description"])

    return generate_learning_path(
        target_role=role,
        missing_skills=missing,
        weak_skills=weak_skills,
        student_id=data.get("student_id")  # 🔥 NEW
    )

# -------------------------------------------------
# ADMIN DASHBOARD APIs
# -------------------------------------------------

@app.get("/admin/placement-funnel")
async def placement_funnel(college_name: str):
    return await get_placement_funnel(college_name)


@app.get("/admin/top-students")
async def top_students(college_name: str):
    return await get_top_students(college_name)


@app.get("/admin/at-risk-students")
async def at_risk_students(college_name: str):
    return await get_at_risk_students(college_name)


@app.get("/admin/skill-gap-trends")
async def skill_gap_trends(college_name: str):
    return await get_skill_gap_trends(college_name)


@app.get("/admin/student-progression")
async def student_progression(student_id: str):
    return await get_student_progression(student_id)