#orchestrator.py
import asyncio
from typing import List, Dict
from collections import Counter

from analyzers.matcher import (resume_jd_match, extract_skills)
from analyzers.github_analyzer import analyze_github_async
from analyzers.leetcode_analyzer import analyze_leetcode_async
from intelligence.role_inference import infer_role_policy
from intelligence.job_readiness import compute_job_readiness_score
from intelligence.failure_diagnosis import generate_failure_diagnosis
from loggers.failure_analytics_logger import log_failure_analytics
from intelligence.placement_probability import compute_placement_probability

# -------------------------------------------------
# GLOBAL CONCURRENCY LIMIT
# -------------------------------------------------
MAX_CONCURRENT_ANALYSIS = 30
analysis_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSIS)

async def build_jd_context(jd_text: str):

    from analyzers.matcher import extract_skills, get_jd_embedding

    jd_text_lower = jd_text.lower()

    jd_skills = extract_skills(jd_text_lower)

    jd_embedding = get_jd_embedding(jd_text_lower)

    return {
        "jd_text": jd_text,
        "jd_text_lower": jd_text_lower,
        "jd_skills": jd_skills,
        "jd_embedding": jd_embedding
    }# -------------------------------------------------
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
    jd_context: dict,
    github_url: str = None,
    leetcode_username: str = None
):

    jd_text = jd_context["jd_text"]
    jd_skills = jd_context["jd_skills"]

    role_policy = infer_role_policy(jd_text)
    role_level = infer_role_level(jd_text)

    # -------------------------------------------------
    # Resume-JD Matching
    # -------------------------------------------------

    resume_jd = await asyncio.to_thread(
        resume_jd_match,
        resume_url,
        jd_text
    )

    # -------------------------------------------------
    # Market-aware skill weight adjustment
    # -------------------------------------------------

    try:

        heatmap = await generate_market_demand_heatmap([jd_text])

        demand_map = {
            item["skill"]: item["demand_score"]
            for item in heatmap
        }

        adjusted = {}

        for skill, weight in resume_jd["jd_skill_weights"].items():

            demand = demand_map.get(skill, 0.5)

            adjusted[skill] = round(weight * (1 + demand), 3)

        resume_jd["jd_skill_weights"] = adjusted

    except Exception:
        pass

    resume_score = resume_jd["final_match_score"]

    signals_used = ["resume_jd"]

    threshold = ROLE_LEVEL_THRESHOLDS[role_level][role_policy]

    # -------------------------------------------------
    # EARLY RESUME FILTER (performance optimization)
    # -------------------------------------------------

    if resume_score < (threshold * 0.5):

        final_score = round(resume_score, 2)

        status = "reject"
        reason = "Below role-level threshold"

        github_result = {"score": 0.0, "evidence": []}
        leetcode_result = {"score": 0.0}

        job_readiness = compute_job_readiness_score({
            "resume_jd": resume_jd,
            "github": github_result,
            "leetcode": leetcode_result,
            "role_level": role_level
        })

        placement_probability = compute_placement_probability({
            "resume_jd": resume_jd,
            "github": github_result,
            "leetcode": leetcode_result,
            "job_readiness": job_readiness,
            "final_score": final_score,
            "threshold": threshold,
            "role_policy": role_policy,
            "role_name": role_policy.replace("_", " "),
            "status": status
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
            "job_readiness": job_readiness,
            "placement_probability": placement_probability
        }

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
    # External Signals
    # -------------------------------------------------

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
        github_task,
        leetcode_task
    )

    # -------------------------------------------------
    # GitHub Skill Recovery
    # -------------------------------------------------

    matched_skills = set(resume_jd["matched_skills"])
    missing_skills = set(resume_jd["missing_skills"])

    github_evidence = set(
        s.lower() for s in github_result.get("evidence", [])
    )

    recovered_skills = []

    for skill in list(missing_skills):

        if skill.lower() in github_evidence:

            recovered_skills.append(skill)
            missing_skills.remove(skill)
            matched_skills.add(skill)

    resume_jd["matched_skills"] = list(matched_skills)
    resume_jd["missing_skills"] = list(missing_skills)

    # -------------------------------------------------
    # AI Final Score
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
            0.5 * resume_score
            + 0.3 * github_result["score"]
            + 0.2 * leetcode_result["score"]
        )

        signals_used.extend(["github", "leetcode"])

    final_score = round(final_score, 2)

    # -------------------------------------------------
    # Final Decision
    # -------------------------------------------------

    if final_score >= threshold:

        status = "shortlist"
        reason = "Meets role-level threshold"

    elif final_score >= threshold - REVIEW_MARGIN:

        status = "review"
        reason = "Borderline candidate – manual review recommended"

    else:

        status = "reject"
        reason = "Below role-level threshold"

    # -------------------------------------------------
    # Job Readiness
    # -------------------------------------------------

    job_readiness = compute_job_readiness_score({
        "resume_jd": resume_jd,
        "github": github_result,
        "leetcode": leetcode_result,
        "role_level": role_level
    })

    # -------------------------------------------------
    # Placement Probability
    # -------------------------------------------------

    placement_probability = compute_placement_probability({
        "resume_jd": resume_jd,
        "github": github_result,
        "leetcode": leetcode_result,
        "job_readiness": job_readiness,
        "final_score": final_score,
        "threshold": threshold,
        "role_policy": role_policy,
        "role_name": role_policy.replace("_", " "),
        "status": status
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
        "job_readiness": job_readiness,
        "placement_probability": placement_probability
    }

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
async def analyze_candidate_limited(
    resume_url: str,
    jd_context: dict,
    github_url: str = None,
    leetcode_username: str = None
):

    async with analysis_semaphore:
        return await analyze_candidate_async(
            resume_url=resume_url,
            jd_context=jd_context,
            github_url=github_url,
            leetcode_username=leetcode_username
        )
def chunk_candidates(candidates, size=200):

    for i in range(0, len(candidates), size):
        yield candidates[i:i + size]

async def rank_candidates_against_jd_async(
    jd_text: str,
    candidates: List[Dict]
):

    jd_context = await build_jd_context(jd_text)

    ranked = []

    for batch in chunk_candidates(candidates, 200):

        tasks = [
            analyze_candidate_limited(
                resume_url=c.get("resume_url"),
                jd_context=jd_context,
                github_url=c.get("github_url"),
                leetcode_username=c.get("leetcode_username")
            )
            for c in batch
        ]

        results = await asyncio.gather(*tasks)

        for candidate, result in zip(batch, results):

            ranked.append({
                "candidate_id": candidate.get("candidate_id"),
                "final_score": result["final_score"],
                "status": result["status"],
                "reason": result["reason"],
                "threshold": result["threshold"],
                "role_policy": result["role_policy"],
                "role_level": result["role_level"],
                "signals_used": result["signals_used"],
                "resume_jd_score": result["resume_jd"]["final_match_score"],
                "job_readiness": result["job_readiness"],
                "rank_explainability": result
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

    tasks = []

    jd_contexts = []

    for jd in jds:
        jd_context = await build_jd_context(jd.get("job_description"))
        jd_contexts.append(jd_context)

    for jd_context in jd_contexts:

        tasks.append(
            analyze_candidate_limited(
                resume_url=student_profile.get("resume_url"),
                jd_context=jd_context,
                github_url=student_profile.get("github_url"),
                leetcode_username=student_profile.get("leetcode_username")
            )
        )

    results = await asyncio.gather(*tasks)

    ranked_jds = []

    for jd, result in zip(jds, results):

        ranked_jds.append({
            "jd_id": jd.get("jd_id"),
            "final_score": result["final_score"],
            "status": result["status"],
            "reason": result["reason"],
            "threshold": result["threshold"],
            "role_policy": result["role_policy"],
            "role_level": result["role_level"],
            "signals_used": result["signals_used"],
            "resume_jd_score": result["resume_jd"]["final_match_score"],
            "job_readiness": result["job_readiness"],
            "jd_explainability": result
        })

    ranked_jds.sort(key=lambda x: x["final_score"], reverse=True)

    for idx, jd in enumerate(ranked_jds, start=1):
        jd["rank"] = idx

    return ranked_jds
# -------------------------------------------------
# SKILL GAP REPORT
# -------------------------------------------------
# -------------------------------------------------
# SKILL GAP REPORT (Enhanced with GitHub + LeetCode)
# -------------------------------------------------
async def generate_skill_gap_report(
    resume_url: str,
    jd_text: str,
    github_url: str = None,
    leetcode_username: str = None
):
    # --- Resume vs JD Matching ---
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

    # -------------------------------------------------
    # EXTERNAL ANALYSIS (Optional)
    # -------------------------------------------------
    github_evidence = []
    leetcode_score = 0.0

    if github_url:
        try:
            github_result = await analyze_github_async(
                github_url,
                set(resume_jd["jd_skill_weights"].keys())
            )
            github_evidence = github_result.get("evidence", [])
        except Exception:
            github_evidence = []

    if leetcode_username:
        try:
            leetcode_result = await analyze_leetcode_async(
                leetcode_username
            )
            leetcode_score = leetcode_result.get("score", 0.0)
        except Exception:
            leetcode_score = 0.0

    # -------------------------------------------------
    # EXTERNAL VALIDATION LAYER (Non-mutating)
    # -------------------------------------------------
    external_validation = {
        "github_confirmed": [],
        "leetcode_indicators": [],
        "confidence_notes": []
    }

    # --- GitHub confirms missing skills ---
    github_lower = [g.lower() for g in github_evidence]

    for gap in gaps:
        if gap["skill"].lower() in github_lower:
            external_validation["github_confirmed"].append(gap["skill"])

    if external_validation["github_confirmed"]:
        external_validation["confidence_notes"].append(
            "Some missing skills validated via GitHub repositories"
        )

    # --- LeetCode supports DSA-related skills ---
    dsa_keywords = [
        "algorithms",
        "data structures",
        "problem solving",
        "competitive programming"
    ]

    if leetcode_score >= 0.5:
        for skill in resume_jd["jd_skill_weights"].keys():
            if skill.lower() in dsa_keywords:
                external_validation["leetcode_indicators"].append(skill)

        if external_validation["leetcode_indicators"]:
            external_validation["confidence_notes"].append(
                "DSA-related skills supported by LeetCode performance"
            )

    # -------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------
    return {
        "matched_skills": resume_jd["matched_skills"],
        "missing_skills": gaps,
        "overall_match_score": resume_jd["final_match_score"],
        "external_validation": external_validation
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
