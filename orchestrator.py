import asyncio
from typing import List, Dict
from collections import Counter

from matcher import resume_jd_match, extract_skills
from github_analyzer import analyze_github_async
from leetcode_analyzer import analyze_leetcode_async
from role_inference import infer_role_policy
from job_readiness import compute_job_readiness_score
from failure_diagnosis import generate_failure_diagnosis
from failure_analytics_logger import log_failure_analytics


# -------------------------------------------------
# ROLE LEVEL INFERENCE
# -------------------------------------------------
def infer_role_level(jd_text: str) -> str:
    jd = jd_text.lower()

    if any(k in jd for k in [
        "intern", "fresher", "junior", "entry level", "graduate"
    ]):
        return "junior"

    if any(k in jd for k in [
        "senior", "lead", "staff", "principal", "architect"
    ]):
        return "senior"

    return "mid"


# -------------------------------------------------
# ROLE-LEVEL THRESHOLDS
# -------------------------------------------------
ROLE_LEVEL_THRESHOLDS = {
    "junior": {
        "resume_only": 0.25,
        "resume_github": 0.35,
        "resume_leetcode": 0.35,
        "resume_github_leetcode": 0.40
    },
    "mid": {
        "resume_only": 0.30,
        "resume_github": 0.40,
        "resume_leetcode": 0.45,
        "resume_github_leetcode": 0.50
    },
    "senior": {
        "resume_only": 0.40,
        "resume_github": 0.50,
        "resume_leetcode": 0.55,
        "resume_github_leetcode": 0.60
    }
}

REVIEW_MARGIN = 0.05

# -------------------------------------------------
# CORE SINGLE-CANDIDATE ANALYSIS (ASYNC)
# -------------------------------------------------
async def analyze_candidate_async(
    resume_url: str,
    jd_text: str,
    github_url: str = None,
    leetcode_username: str = None
):
    role_policy = infer_role_policy(jd_text)
    role_level = infer_role_level(jd_text)

    resume_jd = await asyncio.to_thread(
        resume_jd_match, resume_url, jd_text
    )

    resume_score = resume_jd["final_match_score"]

    jd_skills = set(
        s.lower().strip()
        for s in (resume_jd["matched_skills"] + resume_jd["missing_skills"])
        if isinstance(s, str) and s.strip()
    )

    signals_used = ["resume_jd"]

    github_task = (
        analyze_github_async(github_url, jd_skills)
        if "github" in role_policy
        else asyncio.sleep(0, result={"score": 0.0, "evidence": []})
    )

    leetcode_task = (
        analyze_leetcode_async(leetcode_username)
        if "leetcode" in role_policy
        else asyncio.sleep(0, result={"score": 0.0})
    )

    github_result, leetcode_result = await asyncio.gather(
        github_task, leetcode_task
    )

    if role_policy == "resume_only":
        final_score = resume_score

    elif role_policy == "resume_github":
        final_score = 0.6 * resume_score + 0.4 * github_result["score"]
        signals_used.append("github")

    elif role_policy == "resume_leetcode":
        final_score = 0.6 * resume_score + 0.4 * leetcode_result["score"]
        signals_used.append("leetcode")

    else:
        final_score = (
            0.5 * resume_score +
            0.3 * github_result["score"] +
            0.2 * leetcode_result["score"]
        )
        signals_used.extend(["github", "leetcode"])

    final_score = round(final_score, 2)
    threshold = ROLE_LEVEL_THRESHOLDS[role_level][role_policy]

    if final_score >= threshold:
        status = "shortlist"
        reason = "Meets role-level threshold"
    elif final_score >= threshold - REVIEW_MARGIN:
        status = "review"
        reason = "Borderline candidate – manual review recommended"
    else:
        status = "reject"
        reason = "Below role-level threshold"

    job_readiness = compute_job_readiness_score({
        "resume_jd": resume_jd,
        "github": github_result,
        "leetcode": leetcode_result,
        "role_level": role_level
    })

    response = {
        "final_score": final_score,
        "status": status,
        "reason": reason,
        "threshold": threshold,
        "role_policy": role_policy,
        "role_level": role_level,
        "signals_used": signals_used,
        "resume_jd": resume_jd,
        "github": github_result,
        "leetcode": leetcode_result,
        "job_readiness": job_readiness
    }

    print("\n--- DEBUG FAILURE DIAGNOSIS INPUTS ---")
    print("resume_jd:", resume_jd)
    print("role_policy:", role_policy)
    print("github:", github_result)
    print("leetcode:", leetcode_result)
    print("-------------------------------------\n")

    # 🆕 attach failure diagnosis
    if status in {"reject", "review"}:
        diagnosis = generate_failure_diagnosis(
            final_score=final_score,
            threshold=threshold,
            resume_jd=resume_jd,
            github=github_result,
            leetcode=leetcode_result,
            role_policy=role_policy,
            role_level=role_level
        )

        response["failure_diagnosis"] = diagnosis

        log_failure_analytics(
            decision_stage=status,
            role_level=role_level,
            role_policy=role_policy,
            primary_reasons=diagnosis.get("primary_reasons", []),
            secondary_reasons=diagnosis.get("secondary_reasons", []),
            missing_skills=resume_jd.get("missing_skills", [])
        )

    return response
# -------------------------------------------------
# RECRUITER FLOW: MANY CANDIDATES → ONE JD
# -------------------------------------------------
async def rank_candidates_against_jd_async(
    jd_text: str,
    candidates: List[Dict]
):
    tasks = [
        analyze_candidate_async(
            resume_url=c.get("resume_url"),
            jd_text=jd_text,
            github_url=c.get("github_url"),
            leetcode_username=c.get("leetcode_username")
        )
        for c in candidates
    ]

    results = await asyncio.gather(*tasks)

    ranked = []
    for c, r in zip(candidates, results):
        ranked.append({
            "candidate_id": c.get("candidate_id"),
            "final_score": r["final_score"],
            "status": r["status"],
            "reason": r["reason"],
            "threshold": r["threshold"],
            "role_policy": r["role_policy"],
            "role_level": r["role_level"],
            "signals_used": r["signals_used"],
            "resume_jd_score": r["resume_jd"]["final_match_score"],
            "job_readiness": r["job_readiness"],
            "rank_explainability": r
        })

    ranked.sort(key=lambda x: x["final_score"], reverse=True)

    for idx, r in enumerate(ranked, start=1):
        r["rank"] = idx

    return ranked


# -------------------------------------------------
# STUDENT FLOW: ONE STUDENT → MANY JDs
# -------------------------------------------------
async def match_student_against_multiple_jds_async(
    student_profile: Dict,
    jds: List[Dict]
):
    tasks = [
        analyze_candidate_async(
            resume_url=student_profile.get("resume_url"),
            jd_text=jd.get("job_description"),
            github_url=student_profile.get("github_url"),
            leetcode_username=student_profile.get("leetcode_username")
        )
        for jd in jds
    ]

    results = await asyncio.gather(*tasks)

    ranked_jds = []
    for jd, r in zip(jds, results):
        ranked_jds.append({
            "jd_id": jd.get("jd_id"),
            "final_score": r["final_score"],
            "status": r["status"],
            "reason": r["reason"],
            "threshold": r["threshold"],
            "role_policy": r["role_policy"],
            "role_level": r["role_level"],
            "signals_used": r["signals_used"],
            "resume_jd_score": r["resume_jd"]["final_match_score"],
            "job_readiness": r["job_readiness"],
            "jd_explainability": r
        })

    ranked_jds.sort(key=lambda x: x["final_score"], reverse=True)

    for idx, jd in enumerate(ranked_jds, start=1):
        jd["rank"] = idx

    return ranked_jds


# -------------------------------------------------
# SKILL GAP REPORT
# -------------------------------------------------
async def generate_skill_gap_report(
    resume_url: str,
    jd_text: str
):
    resume_jd = await asyncio.to_thread(
        resume_jd_match, resume_url, jd_text
    )

    gaps = []

    for skill in resume_jd["missing_skills"]:
        weight = resume_jd["jd_skill_weights"].get(skill, 1.0)

        if weight >= 2.0:
            priority = "high"
        elif weight >= 1.5:
            priority = "medium"
        else:
            priority = "low"

        gaps.append({
            "skill": skill,
            "priority": priority,
            "weight": weight
        })

    gaps.sort(key=lambda x: x["weight"], reverse=True)

    return {
        "matched_skills": resume_jd["matched_skills"],
        "missing_skills": gaps,
        "overall_match_score": resume_jd["final_match_score"]
    }


# -------------------------------------------------
# CAREER PATH RECOMMENDATION
# -------------------------------------------------
CAREER_PATHS = {
    "backend developer": [
        "senior backend developer",
        "full stack developer",
        "software architect"
    ],
    "junior backend developer": [
        "backend developer",
        "full stack developer"
    ],
    "data analyst": [
        "data scientist",
        "machine learning engineer"
    ]
}

async def recommend_career_paths(
    resume_url: str,
    jd_text: str
):
    resume_jd = await asyncio.to_thread(
        resume_jd_match, resume_url, jd_text
    )

    role_level = infer_role_level(jd_text)
    base_role = f"{role_level} backend developer"

    return {
        "current_profile_fit": resume_jd["final_match_score"],
        "current_role": base_role,
        "recommended_next_roles": CAREER_PATHS.get(base_role, []),
        "skills_to_focus": resume_jd["missing_skills"][:3]
    }


# -------------------------------------------------
# MARKET DEMAND HEATMAP
# -------------------------------------------------
async def generate_market_demand_heatmap(jds: List[str]):
    skill_counter = Counter()

    for jd in jds:
        skills = extract_skills(jd.lower())
        skill_counter.update(skills)

    total = sum(skill_counter.values()) or 1

    heatmap = [
        {
            "skill": skill,
            "demand_score": round(count / total, 2)
        }
        for skill, count in skill_counter.items()
    ]

    heatmap.sort(key=lambda x: x["demand_score"], reverse=True)
    return heatmap
