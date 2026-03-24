#orchestrator.py
import asyncio
from typing import List, Dict
from collections import Counter

from analyzers.matcher import extract_skills, resume_jd_match_async
from analyzers.github_analyzer import analyze_github_async
from analyzers.leetcode_analyzer import analyze_leetcode_async
from intelligence.action_plan import generate_action_plan
from intelligence.candidate_report import build_candidate_report
from intelligence.explainability import generate_explanation

from intelligence.role_inference import infer_role_policy
from intelligence.job_readiness import compute_job_readiness_score
from intelligence.failure_diagnosis import generate_failure_diagnosis
from intelligence.placement_probability import compute_placement_probability

from db.cache_repo import get_cached_analysis, store_analysis
from intelligence.role_redirection import suggest_alternative_roles
from intelligence.what_if_engine import generate_what_if_analysis
from utils.cache import generate_cache_key
from utils.memory_cache import analysis_cache_memory

# -------------------------------------------------
# GLOBAL CONCURRENCY
# -------------------------------------------------
MAX_CONCURRENT_ANALYSIS = 30
analysis_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSIS)

REVIEW_MARGIN = 0.05

# -------------------------------------------------
# JD CONTEXT
# -------------------------------------------------
async def build_jd_context(jd_text: str):
    return {
        "jd_text": jd_text,
        "jd_skills": extract_skills(jd_text.lower())
    }

# -------------------------------------------------
# ROLE LEVEL
# -------------------------------------------------
def infer_role_level(jd_text: str) -> str:
    jd = jd_text.lower()

    if any(k in jd for k in ["intern", "fresher", "junior", "entry level"]):
        return "junior"

    if any(k in jd for k in ["senior", "lead", "architect"]):
        return "senior"

    return "mid"


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

# -------------------------------------------------
# MAIN ANALYSIS
# -------------------------------------------------
async def analyze_candidate_async(
    resume_url: str,
    jd_context: dict,
    github_url: str = None,
    leetcode_username: str = None,
    college_name: str = None,
    student_id: str = None
):

    jd_text = jd_context["jd_text"]
    jd_skills = jd_context["jd_skills"]

    cache_key = generate_cache_key(
        resume_url,
        jd_text,
        github_url,
        leetcode_username,
        student_id
    )

    # -----------------------------
    # CACHE CHECK
    # -----------------------------
    cached_mem = analysis_cache_memory.get(cache_key)
    if cached_mem:
        return cached_mem

    cached = await get_cached_analysis(cache_key)
    if cached:
        analysis_cache_memory.set(cache_key, cached)
        return cached

    # -----------------------------
    # CORE PIPELINE
    # -----------------------------
    role_policy = infer_role_policy(jd_text)
    role_level = infer_role_level(jd_text)

    resume_jd = await resume_jd_match_async(resume_url, jd_text)

    resume_score = resume_jd["final_match_score"]
    threshold = ROLE_LEVEL_THRESHOLDS[role_level][role_policy]

    signals_used = ["resume_jd"]

    # -------------------------------------------------
    # EARLY REJECTION
    # -------------------------------------------------
    if resume_score < (threshold * 0.5):

        response = {
            "final_score": round(resume_score, 2),
            "status": "reject",
            "reason": "Below role-level threshold",
            "threshold": threshold,
            "role_policy": role_policy,
            "role_level": role_level,
            "signals_used": signals_used,
            "resume_jd": resume_jd,
            "github": {"score": 0.0, "evidence": []},
            "leetcode": {"score": 0.0}
        }

        # -----------------------------
        # INTELLIGENCE LAYERS
        # -----------------------------
        response["job_readiness"] = compute_job_readiness_score({
            "resume_jd": resume_jd,
            "github": response["github"],
            "leetcode": response["leetcode"],
            "role_level": role_level
        })

        response["placement_probability"] = compute_placement_probability({
            "resume_jd": resume_jd,
            "github": response["github"],
            "leetcode": response["leetcode"],
            "job_readiness": response["job_readiness"],
            "final_score": response["final_score"],
            "threshold": threshold,
            "role_policy": role_policy,
            "role_name": role_policy.replace("_", " "),
            "status": "reject"
        })

        response["failure_diagnosis"] = generate_failure_diagnosis(
            final_score=response["final_score"],
            threshold=threshold,
            resume_jd=resume_jd,
            github=response["github"],
            leetcode=response["leetcode"],
            role_policy=role_policy,
            role_level=role_level
        )

        # -----------------------------
        # 🔥 NEW FEATURES
        # -----------------------------
        explanation = generate_explanation(response)
        alternatives = suggest_alternative_roles(response, {})
        report = build_candidate_report(response, explanation, alternatives)

        response["explanation"] = explanation
        response["alternative_roles"] = alternatives
        response["candidate_report"] = report

        # -----------------------------
        # CACHE STORE
        # -----------------------------
        await store_analysis(cache_key, {
            "resume_url": resume_url,
            "jd_text": jd_text,
            "github_url": github_url,
            "leetcode_username": leetcode_username,
            "college_name": college_name,
            "student_id": student_id,
            "result": response
        })

        analysis_cache_memory.set(cache_key, response)
        return response

    # -------------------------------------------------
    # EXTERNAL SIGNALS
    # -------------------------------------------------
    github_result, leetcode_result = await asyncio.gather(
        analyze_github_async(github_url, jd_skills)
        if "github" in role_policy else asyncio.sleep(0, result={"score": 0.0, "evidence": []}),
        analyze_leetcode_async(leetcode_username)
        if "leetcode" in role_policy else asyncio.sleep(0, result={"score": 0.0})
    )

    # -------------------------------------------------
    # FINAL SCORE
    # -------------------------------------------------
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

    # -------------------------------------------------
    # DECISION
    # -------------------------------------------------
    if final_score >= threshold:
        status = "shortlist"
        reason = "Meets role-level threshold"
    elif final_score >= threshold - REVIEW_MARGIN:
        status = "review"
        reason = "Borderline candidate"
    else:
        status = "reject"
        reason = "Below role-level threshold"

    # -------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------
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
        "leetcode": leetcode_result
    }

    # -----------------------------
    # INTELLIGENCE LAYERS
    # -----------------------------
    response["job_readiness"] = compute_job_readiness_score({
        "resume_jd": resume_jd,
        "github": github_result,
        "leetcode": leetcode_result,
        "role_level": role_level
    })

    response["placement_probability"] = compute_placement_probability({
        "resume_jd": resume_jd,
        "github": github_result,
        "leetcode": leetcode_result,
        "job_readiness": response["job_readiness"],
        "final_score": final_score,
        "threshold": threshold,
        "role_policy": role_policy,
        "role_name": role_policy.replace("_", " "),
        "status": status
    })

    if status in {"reject", "review"}:
        response["failure_diagnosis"] = generate_failure_diagnosis(
            final_score=final_score,
            threshold=threshold,
            resume_jd=resume_jd,
            github=github_result,
            leetcode=leetcode_result,
            role_policy=role_policy,
            role_level=role_level
        )

    # -----------------------------
    # 🔥 NEW FEATURES
    # -----------------------------
    explanation = generate_explanation(response)
    alternatives = suggest_alternative_roles(response, {})
    report = build_candidate_report(response, explanation, alternatives)

    response["explanation"] = explanation
    response["alternative_roles"] = alternatives
    response["candidate_report"] = report

    # -----------------------------
    # CACHE STORE
    # -----------------------------
    await store_analysis(cache_key, {
        "resume_url": resume_url,
        "jd_text": jd_text,
        "github_url": github_url,
        "leetcode_username": leetcode_username,
        "college_name": college_name,
        "student_id": student_id,
        "result": response
    })

    analysis_cache_memory.set(cache_key, response)

    return response

# -------------------------------------------------
# RECRUITER FLOW
# -------------------------------------------------
async def analyze_candidate_limited(
    resume_url,
    jd_context,
    github_url=None,
    leetcode_username=None,
    college_name=None,
    student_id=None   # 🔥 ADD
):
    async with analysis_semaphore:
        return await analyze_candidate_async(
            resume_url,
            jd_context,
            github_url,
            leetcode_username,
            college_name,
            student_id   # 🔥 PASS
        )
async def rank_candidates_against_jd_async(jd_text: str, candidates: List[Dict]):
    jd_context = await build_jd_context(jd_text)

    results = await asyncio.gather(*[
        analyze_candidate_limited(
            c.get("resume_url"),
            jd_context,
            c.get("github_url"),
            c.get("leetcode_username"),
            c.get("college_name"),
            c.get("student_id")
        ) for c in candidates
    ])

    # attach student_id
    ranked = [
        {**r, "student_id": c.get("student_id")}
        for c, r in zip(candidates, results)
    ]

    # -------------------------------------------------
    # 🔥 BUCKETING LOGIC
    # -------------------------------------------------
    shortlist_bucket = []
    review_bucket = []
    reject_bucket = []

    for r in ranked:
        if r["status"] == "shortlist":
            shortlist_bucket.append(r)
        elif r["status"] == "review":
            review_bucket.append(r)
        else:
            reject_bucket.append(r)

    # -------------------------------------------------
    # SORT EACH BUCKET (DESCENDING SCORE)
    # -------------------------------------------------
    shortlist_bucket.sort(key=lambda x: x["final_score"], reverse=True)
    review_bucket.sort(key=lambda x: x["final_score"], reverse=True)
    reject_bucket.sort(key=lambda x: x["final_score"], reverse=True)

    # -------------------------------------------------
    # MERGE IN ORDER
    # -------------------------------------------------
    final_ranked = shortlist_bucket + review_bucket + reject_bucket

    # -------------------------------------------------
    # ASSIGN GLOBAL RANK
    # -------------------------------------------------
    for i, r in enumerate(final_ranked, 1):
        r["rank"] = i

    return final_ranked

# -------------------------------------------------
# STUDENT FLOW
# -------------------------------------------------
async def match_student_against_multiple_jds_async(
    student_profile: Dict,
    jds: List[Dict]
):
    results = await asyncio.gather(*[
        analyze_candidate_async(
            student_profile.get("resume_url"),
            await build_jd_context(jd.get("job_description")),
            student_profile.get("github_url"),
            student_profile.get("leetcode_username"),
            student_profile.get("college_name"),
            student_profile.get("student_id")

        )
        for jd in jds
    ])

    ranked = [
        {**r, "jd_id": jd.get("jd_id")}
        for jd, r in zip(jds, results)
    ]

    # -------------------------------------------------
    # 🔥 BUCKETING
    # -------------------------------------------------
    shortlist_bucket = []
    review_bucket = []
    reject_bucket = []

    for r in ranked:
        if r["status"] == "shortlist":
            shortlist_bucket.append(r)
        elif r["status"] == "review":
            review_bucket.append(r)
        else:
            reject_bucket.append(r)

    # -------------------------------------------------
    # SORT EACH BUCKET
    # -------------------------------------------------
    shortlist_bucket.sort(key=lambda x: x["final_score"], reverse=True)
    review_bucket.sort(key=lambda x: x["final_score"], reverse=True)
    reject_bucket.sort(key=lambda x: x["final_score"], reverse=True)

    # -------------------------------------------------
    # MERGE
    # -------------------------------------------------
    final_ranked = shortlist_bucket + review_bucket + reject_bucket

    # -------------------------------------------------
    # GLOBAL + BUCKET RANK
    # -------------------------------------------------
    rank = 1

    for bucket in [shortlist_bucket, review_bucket, reject_bucket]:
        for i, r in enumerate(bucket, 1):
            r["bucket_rank"] = i   # rank inside that status
            r["rank"] = rank       # global rank
            rank += 1

    return final_ranked
# -------------------------------------------------
# MARKET DEMAND
# -------------------------------------------------
from collections import Counter
from typing import List
import math


async def generate_market_demand_heatmap(jds: List[str]):

    counter = Counter()

    for jd in jds:
        counter.update(extract_skills(jd.lower()))

    total = sum(counter.values()) or 1

    # Step 1: exact scores
    items = []
    for k, v in counter.items():
        exact = v / total
        floor_val = math.floor(exact * 100) / 100  # truncate to 2 decimals
        remainder = exact - floor_val

        items.append({
            "skill": k,
            "exact": exact,
            "floor": floor_val,
            "remainder": remainder
        })

    # Step 2: compute remaining points
    floor_sum = sum(x["floor"] for x in items)
    remaining = round(1 - floor_sum, 2)

    # number of 0.01 units to distribute
    units = int(round(remaining * 100))

    # Step 3: distribute based on largest remainder
    items.sort(key=lambda x: x["remainder"], reverse=True)

    for i in range(units):
        items[i]["floor"] += 0.01

    # Step 4: format output
    result = [
        {
            "skill": x["skill"],
            "demand_score": round(x["floor"], 2)
        }
        for x in items
    ]

    # final sort
    result.sort(key=lambda x: x["demand_score"], reverse=True)

    return result
# -------------------------------------------------
# SKILL GAP REPORT (REQUIRED FOR APP.PY)
# -------------------------------------------------
async def generate_skill_gap_report(
    resume_url: str,
    jd_text: str,
    github_url: str = None,
    leetcode_username: str = None
):
    resume_jd = await resume_jd_match_async(resume_url, jd_text)

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
# CAREER PATH (REQUIRED)
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
    ]
}


async def recommend_career_paths(resume_url: str, jd_text: str):

    resume_jd = await resume_jd_match_async(resume_url, jd_text)

    role_level = infer_role_level(jd_text)
    base_role = f"{role_level} backend developer"

    return {
        "current_profile_fit": resume_jd["final_match_score"],
        "current_role": base_role,
        "recommended_next_roles": CAREER_PATHS.get(base_role, []),
        "skills_to_focus": resume_jd["missing_skills"][:3]
    }