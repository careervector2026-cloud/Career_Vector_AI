# admin/admin_dashboard.py
from db.neon_db import get_pool


# -------------------------------------------------
# COLLEGE-WISE PLACEMENT FUNNEL WITH PERCENTAGES
# -------------------------------------------------
async def get_placement_funnel(college_name: str):

    pool = await get_pool()

    async with pool.acquire() as conn:

        rows = await conn.fetch("""
            SELECT student_id, status, recruiter_status
            FROM candidate_analysis_cache
            WHERE college_name = $1
        """, college_name)

        # -------------------------------------------------
        # STEP 1: GROUP PER STUDENT (DEDUP)
        # -------------------------------------------------
        student_map = {}

        for r in rows:
            sid = r["student_id"]

            if sid not in student_map:
                student_map[sid] = {
                    "statuses": set(),
                    "recruiter_statuses": set()
                }

            if r["status"]:
                student_map[sid]["statuses"].add(r["status"])

            if r["recruiter_status"]:
                student_map[sid]["recruiter_statuses"].add(r["recruiter_status"])

        # -------------------------------------------------
        # STEP 2: FINAL CLASSIFICATION (MUTUALLY EXCLUSIVE)
        # -------------------------------------------------
        hired = set()
        rejected = set()
        shortlisted_pending = set()
        review_pending = set()

        for sid, data in student_map.items():

            statuses = data["statuses"]
            recruiter_statuses = data["recruiter_statuses"]

            # 1. FINAL HIRED (highest priority)
            status_normalized = {s.lower() for s in statuses}

            if "hired" in recruiter_statuses:
                hired.add(sid)
            elif "shortlisted" in status_normalized or "shortlist" in status_normalized:
                shortlisted_pending.add(sid)

            elif "review" in status_normalized:
                review_pending.add(sid)
            elif "rejected" in recruiter_statuses or "reject" in recruiter_statuses:
                rejected.add(sid)
            else:
                rejected.add(sid)

        # -------------------------------------------------
        # STEP 3: COUNTS
        # -------------------------------------------------
        total_students = len(student_map)

        hired_count = len(hired)
        rejected_count = len(rejected)
        shortlisted_count = len(shortlisted_pending)
        review_count = len(review_pending)

        # -------------------------------------------------
        # STEP 4: PERCENTAGES
        # -------------------------------------------------
        def calc_percent(value):
            return round((value / total_students) * 100, 2) if total_students > 0 else 0

        result = {
            "college_name": college_name,

            # counts
            "total_students": total_students,
            "hired": hired_count,
            "rejected": rejected_count,
            "shortlisted_pending": shortlisted_count,
            "review_pending": review_count,

            # percentages
            "hired_percentage": calc_percent(hired_count),
            "rejected_percentage": calc_percent(rejected_count),
            "shortlisted_percentage": calc_percent(shortlisted_count),
            "review_percentage": calc_percent(review_count),
        }

        # -------------------------------------------------
        # STEP 5: SANITY CHECK (OPTIONAL DEBUG)
        # -------------------------------------------------
        result["total_percentage_check"] = round(
            result["hired_percentage"]
            + result["rejected_percentage"]
            + result["shortlisted_percentage"]
            + result["review_percentage"],
            2
        )

        return result
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