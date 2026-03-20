from db.neon_db import get_pool
import json


# -------------------------------------------------
# GET CACHE
# -------------------------------------------------
async def get_cached_analysis(cache_key: str):

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT result
            FROM candidate_analysis_cache
            WHERE cache_key = $1
            """,
            cache_key
        )

        if not row:
            return None

        result = row["result"]

        # 🔥 handle both str and dict safely
        if isinstance(result, str):
            return json.loads(result)

        return result


# -------------------------------------------------
# STORE / UPDATE CACHE
# -------------------------------------------------
async def store_analysis(cache_key: str, data: dict):

    pool = await get_pool()

    async with pool.acquire() as conn:

        result = data.get("result", {})

        await conn.execute(
            """
            INSERT INTO candidate_analysis_cache (
                cache_key,
                resume_url,
                github_url,
                leetcode_username,
                college_name,
                student_id,
                result,
                status,
                final_score
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)

            ON CONFLICT (cache_key) DO UPDATE SET
                result = EXCLUDED.result,
                status = EXCLUDED.status,
                final_score = EXCLUDED.final_score,
                college_name = EXCLUDED.college_name,
                student_id = EXCLUDED.student_id
            """,
            cache_key,
            data.get("resume_url"),
            data.get("github_url"),
            data.get("leetcode_username"),
            data.get("college_name"),
            data.get("student_id"),  # 🔥 NEW
            json.dumps(result),
            result.get("status") or result.get("decision"),
            float(result.get("final_score", 0))
        )