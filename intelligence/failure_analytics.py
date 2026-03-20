from collections import Counter, defaultdict
from db.neon_db import get_pool
import json


async def generate_failure_analytics(
    decision_filter: str = "ALL",
    college_name: str = None
):
    """
    Optimized DB-based analytics:
    - Uses structured columns (status, final_score)
    - Falls back to JSON if needed
    - Supports DB-level filtering
    """

    pool = await get_pool()

    async with pool.acquire() as conn:

        # -----------------------------
        # BUILD QUERY (NOW OPTIMIZED)
        # -----------------------------
        query = """
            SELECT 
                college_name,
                status,
                final_score,
                result
            FROM candidate_analysis_cache
            WHERE 1=1
        """

        params = []
        idx = 1

        # ✅ FILTER: decision (DB LEVEL)
        if decision_filter != "ALL":
            query += f" AND LOWER(status) = LOWER(${idx})"
            params.append(decision_filter)
            idx += 1

        # ✅ FILTER: college (DB LEVEL)
        if college_name:
            query += f" AND LOWER(college_name) = LOWER(${idx})"
            params.append(college_name)
            idx += 1

        rows = await conn.fetch(query, *params)

    if not rows:
        return {"message": "No data found"}

    # -----------------------------
    # ANALYTICS STRUCTURES
    # -----------------------------
    primary_counter = Counter()
    secondary_counter = Counter()
    skill_counter = Counter()

    college_counter = Counter()
    college_failures = Counter()
    college_scores = defaultdict(list)

    total_records = 0

    # -----------------------------
    # PROCESS DATA
    # -----------------------------
    for row in rows:

        raw_result = row["result"] or {}

        # ✅ SAFE JSON HANDLING (old corrupted rows)
        if isinstance(raw_result, str):
            try:
                result = json.loads(raw_result)
            except:
                result = {}
        else:
            result = raw_result

        # ✅ USE DB COLUMN FIRST (FAST)
        status = (row["status"] or result.get("status") or "").lower()
        score = float(row["final_score"] or result.get("final_score") or 0)

        college = row["college_name"] or "unknown"

        total_records += 1

        # -------------------------
        # COLLEGE METRICS
        # -------------------------
        college_counter[college] += 1
        college_scores[college].append(score)

        if status in {"reject", "review"}:
            college_failures[college] += 1

        # -------------------------
        # FAILURE DATA
        # -------------------------
        failure = result.get("failure_diagnosis", {})

        primary = failure.get("primary_reasons", [])
        secondary = failure.get("secondary_reasons", [])
        missing = result.get("resume_jd", {}).get("missing_skills", [])

        for r in primary:
            reason = r.get("reason", "").strip()
            if reason:
                primary_counter[reason] += 1

        for r in secondary:
            reason = r.get("reason", "").strip()
            if reason:
                secondary_counter[reason] += 1

        for s in missing:
            if isinstance(s, dict):
                s = s.get("skill", "")
            if s:
                skill_counter[s] += 1

    # -----------------------------
    # COLLEGE INSIGHTS
    # -----------------------------
    college_insights = []

    for c in college_counter:
        total = college_counter[c]
        failures = college_failures[c]
        avg_score = sum(college_scores[c]) / max(len(college_scores[c]), 1)

        college_insights.append({
            "college": c,
            "total_candidates": total,
            "failure_rate": round(failures / total, 2),
            "avg_score": round(avg_score, 2)
        })

    college_insights.sort(key=lambda x: x["failure_rate"], reverse=True)

    # -----------------------------
    # FINAL RESPONSE
    # -----------------------------
    response = {
        "total_records": total_records,
        "top_primary_issues": primary_counter.most_common(5),
        "top_secondary_issues": secondary_counter.most_common(5),
        "most_common_missing_skills": skill_counter.most_common(5),
        "college_insights": college_insights[:10]
    }

    # ✅ GLOBAL ONLY
    if not college_name:
        response["top_failing_colleges"] = sorted(
            college_failures.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

    return response