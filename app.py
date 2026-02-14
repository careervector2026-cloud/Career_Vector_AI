from fastapi import FastAPI, Request, HTTPException
from urllib.parse import parse_qs
from learning_path import generate_learning_path
from failure_analytics import generate_failure_analytics

import json

from orchestrator import (
    analyze_candidate_async,
    rank_candidates_against_jd_async,
    match_student_against_multiple_jds_async,
    generate_skill_gap_report,
    recommend_career_paths,
    generate_market_demand_heatmap
)

app = FastAPI()

# -------------------------------------------------
# ANALYZE SINGLE CANDIDATE
# -------------------------------------------------
@app.post("/analyze")
async def analyze(request: Request):
    content_type = request.headers.get("content-type", "")
    raw_body = await request.body()

    if "application/x-www-form-urlencoded" in content_type:
        parsed = parse_qs(raw_body.decode())
        data = {k: v[0] for k, v in parsed.items()}
    elif "application/json" in content_type:
        data = json.loads(raw_body.decode())
    else:
        raise HTTPException(400, "Unsupported Content-Type")

    if not data.get("resume_url") or not data.get("job_description"):
        raise HTTPException(422, "resume_url and job_description required")

    return await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_text=data["job_description"],
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
async def match_student_jds(request: Request):
    try:
        data = await request.json()

        student = data.get("student_profile")
        jds = data.get("jds")

        if not student or not jds:
            raise HTTPException(
                status_code=422,
                detail="student_profile and jds are required"
            )

        return await match_student_against_multiple_jds_async(
            student_profile=student,
            jds=jds
        )

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
        jd_text=data["job_description"]
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
@app.post("/learning-path")
async def learning_path_from_jd(request: Request):
    data = await request.json()

    if not data.get("resume_url") or not data.get("job_description"):
        raise HTTPException(
            422,
            "resume_url and job_description are required"
        )

    result = await analyze_candidate_async(
        resume_url=data["resume_url"],
        jd_text=data["job_description"],
        github_url=data.get("github_url"),
        leetcode_username=data.get("leetcode_username")
    )

    # ----------------------------
    # 1️⃣ ROLE (BEST POSSIBLE)
    # ----------------------------
    # You do NOT infer role name yet, so we do best-effort
    role_level = result.get("role_level", "unknown")
    target_role = f"Junior Backend Developer" if role_level == "junior" else "Backend Developer"

    # ----------------------------
    # 2️⃣ SKILL GAP (ACTUAL SOURCE)
    # ----------------------------
    resume_jd = result.get("resume_jd", {})

    missing_skills = resume_jd.get("missing_skills", [])

    # You currently do NOT compute weak skills
    # So we keep this empty (correct & honest)
    weak_skills = []

    return generate_learning_path(
        target_role=target_role,
        missing_skills=missing_skills,
        weak_skills=weak_skills
    )


@app.post("/failure-analytics")
def failure_analytics():
    return generate_failure_analytics()
