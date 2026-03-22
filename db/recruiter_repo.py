# recruiter_repo.py

from db.neon_db import get_pool
from datetime import datetime
from utils.cache import generate_jd_id   # 🔥 your function

# -------------------------------------------------
# UPDATE RECRUITER DECISION
# -------------------------------------------------
async def update_recruiter_decision(cache_key: str, decision: str):
    """
    decision: 'hired' | 'rejected'
    """

    if decision not in ["hired", "rejected"]:
        raise ValueError("Invalid decision. Must be 'hired' or 'rejected'")

    pool = await get_pool()

    async with pool.acquire() as conn:

        # -------------------------------------------------
        # VALIDATION: candidate must exist
        # -------------------------------------------------
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
        # VALIDATION: only shortlisted candidates allowed
        # -------------------------------------------------
        if row["status"] != "shortlisted":
            raise ValueError("Recruiter decision allowed only for shortlisted candidates")

        # -------------------------------------------------
        # OPTIONAL: prevent overwrite (strong design)
        # -------------------------------------------------
        if row["recruiter_status"] in ["hired", "rejected"]:
            raise ValueError("Decision already made for this candidate")

        # -------------------------------------------------
        # UPDATE
        # -------------------------------------------------
        await conn.execute(
            """
            UPDATE candidate_analysis_cache
            SET recruiter_status = $1,
                recruiter_decision_at = NOW()
            WHERE cache_key = $2
            """,
            decision,
            cache_key
        )

    return {
        "message": f"Candidate marked as {decision}"
    }

# -------------------------------------------------
# UPDATE USING JD_TEXT
# -------------------------------------------------
async def update_recruiter_decision_with_jd_text(
    student_id: str,
    jd_text: str,
    decision: str
):

    decision = decision.lower()

    if decision not in ["hired", "rejected"]:
        raise ValueError("Invalid decision")

    jd_id = generate_jd_id(jd_text)   # 🔥 CRITICAL

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT status
            FROM candidate_analysis_cache
            WHERE student_id = $1 AND jd_id = $2
            """,
            student_id,
            jd_id
        )

        if not row:
            raise ValueError("No matching record found for given JD")

        current_status = row["status"]

        if current_status == "reject":
            raise ValueError("Cannot update rejected candidate")

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
        "message": "Updated using jd_text",
        "student_id": student_id,
        "jd_id": jd_id,
        "decision": decision
    }
