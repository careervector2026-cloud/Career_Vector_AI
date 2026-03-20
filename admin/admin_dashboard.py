# admin/admin_dashboard.py

from db.neon_db import get_pool
from collections import Counter


# -------------------------------------------------
# 1. PLACEMENT FUNNEL
# -------------------------------------------------
async def get_placement_funnel(college_name: str):

    pool = await get_pool()

    async with pool.acquire() as conn:

        rows = await conn.fetch("""
            SELECT student_id, status
            FROM candidate_analysis_cache
            WHERE college_name = $1
        """, college_name)

        # -------------------------------
        # STEP 1: GROUP STATUSES PER STUDENT
        # -------------------------------
        student_status_map = {}

        for r in rows:
            sid = r["student_id"]
            status = r["status"]

            if sid not in student_status_map:
                student_status_map[sid] = set()

            student_status_map[sid].add(status)

        # -------------------------------
        # STEP 2: APPLY PRIORITY LOGIC
        # -------------------------------
        shortlisted = set()
        review = set()
        rejected = set()

        for sid, statuses in student_status_map.items():

            if "shortlist" in statuses:
                shortlisted.add(sid)

            elif "review" in statuses:
                review.add(sid)

            else:
                rejected.add(sid)

        # -------------------------------
        # STEP 3: FINAL COUNTS
        # -------------------------------
        total_students = len(student_status_map)

        return {
            "total_students": total_students,
            "shortlisted": len(shortlisted),
            "review": len(review),
            "rejected": len(rejected),
            "conversion_rate": round(
                (len(shortlisted) / total_students) * 100, 2
            ) if total_students else 0
        }

# -------------------------------------------------
# 2. TOP STUDENTS
# -------------------------------------------------
async def get_top_students(college_name: str):

    pool = await get_pool()

    async with pool.acquire() as conn:

        rows = await conn.fetch("""
            SELECT 
                student_id,
                AVG(final_score) as avg_score,
                COUNT(*) FILTER (WHERE status = 'shortlist') as shortlist_count
            FROM candidate_analysis_cache
            WHERE college_name = $1
            GROUP BY student_id
            ORDER BY avg_score DESC
            LIMIT 10
        """, college_name)

        return [
            {
                "student_id": r["student_id"],
                "avg_score": round(r["avg_score"], 3),
                "shortlist_count": r["shortlist_count"]
            }
            for r in rows
        ]

# -------------------------------------------------
# 3. AT-RISK STUDENTS
# -------------------------------------------------
async def get_at_risk_students(college_name: str):

    pool = await get_pool()

    async with pool.acquire() as conn:

        rows = await conn.fetch("""
            SELECT 
                student_id,
                AVG(final_score) as avg_score,
                COUNT(*) FILTER (WHERE status = 'reject') * 1.0 / COUNT(*) as rejection_rate,
                COUNT(*) as attempts
            FROM candidate_analysis_cache
            WHERE college_name = $1
            GROUP BY student_id
            HAVING COUNT(*) >= 2
            ORDER BY rejection_rate DESC
        """, college_name)

        return [
            {
                "student_id": r["student_id"],
                "avg_score": round(r["avg_score"], 3),
                "rejection_rate": round(r["rejection_rate"], 2),
                "attempts": r["attempts"]
            }
            for r in rows
        ]

# -------------------------------------------------
# 4. SKILL GAP TRENDS
# -------------------------------------------------
from collections import Counter

async def get_skill_gap_trends(college_name: str):

    pool = await get_pool()

    async with pool.acquire() as conn:

        rows = await conn.fetch("""
            SELECT result
            FROM candidate_analysis_cache
            WHERE college_name = $1
        """, college_name)

        counter = Counter()

        for r in rows:
            result = r["result"]

            if not result:
                continue

            failure = result.get("failure_diagnosis")
            if not failure:
                continue

            reasons = failure.get("primary_reasons", [])

            for item in reasons:
                # 🔥 FIX: item is dict, not string
                skill = item.get("skill")

                if skill:
                    counter[skill] += 1

        return [
            {"skill": k, "count": v}
            for k, v in counter.most_common(10)
        ]

# -------------------------------------------------
# 5. STUDENT PROGRESSION
# -------------------------------------------------
async def get_student_progression(student_id: str):

    pool = await get_pool()

    async with pool.acquire() as conn:

        rows = await conn.fetch("""
            SELECT final_score, created_at
            FROM candidate_analysis_cache
            WHERE student_id = $1
            ORDER BY created_at
        """, student_id)

        scores = [round(r["final_score"], 3) for r in rows]

        trend = "stable"

        if len(scores) >= 2:
            if scores[-1] > scores[0]:
                trend = "improving"
            elif scores[-1] < scores[0]:
                trend = "declining"

        return {
            "student_id": student_id,
            "scores": scores,
            "trend": trend
        }