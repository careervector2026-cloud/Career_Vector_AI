# recruiter_repo.py

from db.neon_db import get_pool
from datetime import datetime
from utils.cache import generate_jd_id


# -------------------------------------------------
# NORMALIZATION FUNCTION
# -------------------------------------------------
def normalize_decision(decision: str) -> str:

    if not decision:
        raise ValueError("Decision is required")

    d = decision.strip().lower()

    # 🔥 FIX: normalize underscores → spaces
    d = d.replace("_", " ")

    mapping = {
        "hired": "hired",
        "selected": "hired",

        "rejected": "rejected",
        "reject": "rejected",

        "shortlisted": "shortlisted",
        "shortlist": "shortlisted",

        "under review": "review",
        "review": "review"
    }

    if d not in mapping:
        raise ValueError(f"Invalid decision: {decision}")

    return mapping[d]

# -------------------------------------------------
# UPDATE USING CACHE KEY
# -------------------------------------------------
async def update_recruiter_decision(cache_key: str, decision: str):

    decision = normalize_decision(decision)

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT status, recruiter_status
            FROM candidate_analysis_cache
            WHERE cache_key = $1
            """,
            cache_key
        )

        if not row:
            raise ValueError("Candidate not found")

        # -------------------------------------------------
        # PIPELINE STATE UPDATE
        # -------------------------------------------------
        if decision in ["shortlisted", "review"]:

            await conn.execute(
                """
                UPDATE candidate_analysis_cache
                SET recruiter_status = $1
                WHERE cache_key = $2
                """,
                decision,
                cache_key
            )

            return {
                "message": f"Candidate moved to {decision}"
            }

        # -------------------------------------------------
        # FINAL DECISION (hired / rejected)
        # -------------------------------------------------
        if row["recruiter_status"] in ["hired", "rejected"]:
            raise ValueError("Final decision already made")

        await conn.execute(
            """
            UPDATE candidate_analysis_cache
            SET recruiter_status = $1,
                recruiter_decision_at = $2
            WHERE cache_key = $3
            """,
            decision,
            datetime.utcnow(),
            cache_key
        )

    return {
        "message": f"Candidate marked as {decision}"
    }


# -------------------------------------------------
# UPDATE USING JD TEXT
# -------------------------------------------------
async def update_recruiter_decision_with_jd_text(
    student_id: str,
    jd_text: str,
    decision: str
):

    decision = normalize_decision(decision)

    jd_id = generate_jd_id(jd_text)

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT status, recruiter_status
            FROM candidate_analysis_cache
            WHERE student_id = $1 AND jd_id = $2
            """,
            student_id,
            jd_id
        )

        if not row:
            raise ValueError("No matching record found for given JD")

        # -------------------------------------------------
        # PIPELINE STATE UPDATE
        # -------------------------------------------------
        if decision in ["shortlisted", "review"]:

            await conn.execute(
                """
                UPDATE candidate_analysis_cache
                SET recruiter_status = $1
                WHERE student_id = $2 AND jd_id = $3
                """,
                decision,
                student_id,
                jd_id
            )

            return {
                "message": f"Candidate moved to {decision}",
                "student_id": student_id,
                "jd_id": jd_id
            }

        # -------------------------------------------------
        # FINAL DECISION
        # -------------------------------------------------
        if row["recruiter_status"] in ["hired", "rejected"]:
            raise ValueError("Final decision already made")

        await conn.execute(
            """
            UPDATE candidate_analysis_cache
            SET recruiter_status = $1,
                recruiter_decision_at = $2
            WHERE student_id = $3 AND jd_id = $4
            """,
            decision,
            datetime.utcnow(),
            student_id,
            jd_id
        )

    return {
        "message": "Decision updated",
        "student_id": student_id,
        "jd_id": jd_id,
        "decision": decision
    }