# admin/admin_dashboard.py
from typing import List
from db.neon_db import get_pool
from utils.cache import generate_jd_id
# -------------------------------------------------
# 🔥 STATUS NORMALIZATION (CRITICAL)
# -------------------------------------------------
def normalize_status(status: str):
    if not status:
        return ""

    s = status.strip().lower().replace("_", " ")

    if s in ["shortlist", "shortlisted"]:
        return "shortlisted"

    if s in ["review", "under review"]:
        return "review"

    if s in ["reject", "rejected"]:
        return "rejected"

    return s


def normalize_recruiter_status(status: str):
    if not status:
        return ""

    s = status.strip().lower()

    if s in ["selected", "hired"]:
        return "hired"

    if s in ["reject", "rejected"]:
        return "rejected"

    return ""


# -------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------
async def get_full_funnel_with_students(college_name: str, jd_texts: List[str]):

    pool = await get_pool()

    jd_ids = list(set(generate_jd_id(jd) for jd in jd_texts if jd))

    async with pool.acquire() as conn:

        # -----------------------------------------
        # FETCH DATA
        # -----------------------------------------
        if jd_ids:
            rows = await conn.fetch("""
                SELECT student_id, jd_id, status, recruiter_status
                FROM candidate_analysis_cache
                WHERE college_name = $1
                AND jd_id = ANY($2)
            """, college_name, jd_ids)
        else:
            rows = await conn.fetch("""
                SELECT student_id, jd_id, status, recruiter_status
                FROM candidate_analysis_cache
                WHERE college_name = $1
            """, college_name)

        # -----------------------------------------
        # UTIL
        # -----------------------------------------
        def safe_div(a, b):
            return round(a / b, 2) if b > 0 else 0

        # -----------------------------------------
        # STORAGE
        # -----------------------------------------
        pair_map = {}
        student_apps = {}

        # -----------------------------------------
        # BUILD DATA (🔥 CLEANED)
        # -----------------------------------------
        for r in rows:

            sid = r["student_id"]
            jid = r["jd_id"]

            status = normalize_status(r["status"])
            recruiter_status = normalize_recruiter_status(r["recruiter_status"])

            key = (sid, jid)

            if key not in pair_map:
                pair_map[key] = {
                    "status": status,
                    "recruiter_status": recruiter_status
                }

            if sid not in student_apps:
                student_apps[sid] = []

            student_apps[sid].append(pair_map[key])

        # -----------------------------------------
        # APPLICATION LEVEL
        # -----------------------------------------
        S_app, V_app, H_app, R_app = set(), set(), set(), set()

        for key, app in pair_map.items():

            status = app["status"]
            recruiter_status = app["recruiter_status"]

            if status == "shortlisted":
                S_app.add(key)

            if status == "review":
                V_app.add(key)

            if recruiter_status == "hired":
                H_app.add(key)

            if recruiter_status == "rejected":
                R_app.add(key)

        total_applications = len(pair_map)

        # -----------------------------------------
        # STUDENT LEVEL (🔥 FINAL CORRECT LOGIC)
        # -----------------------------------------
        H_stu, R_stu, P_stu = set(), set(), set()
        S_stu, V_stu = set(), set()

        students_output = {}

        for sid, apps in student_apps.items():

            has_hired = False
            has_pending = False
            all_rejected = True

            shortlisted = 0
            review = 0
            hired = 0
            rejected = 0

            for app in apps:

                status = app["status"]
                recruiter_status = app["recruiter_status"]

                # ---------------- COUNTS ----------------
                if status == "shortlisted":
                    shortlisted += 1
                    S_stu.add(sid)

                if status == "review":
                    review += 1
                    V_stu.add(sid)

                if recruiter_status == "hired":
                    hired += 1
                    has_hired = True

                if recruiter_status == "rejected":
                    rejected += 1

                # ---------------- PENDING ----------------
                if recruiter_status == "" and status in ["shortlisted", "review"]:
                    has_pending = True

                # ---------------- FINAL REJECTION CHECK ----------------
                is_rejected = (
                    recruiter_status == "rejected"
                    or status == "rejected"
                )

                if not is_rejected:
                    all_rejected = False

            # -----------------------------------------
            # FINAL CLASSIFICATION
            # -----------------------------------------
            if has_hired:
                H_stu.add(sid)

            elif has_pending:
                P_stu.add(sid)

            elif all_rejected:
                R_stu.add(sid)

            # -----------------------------------------
            # STUDENT OUTPUT
            # -----------------------------------------
            total = len(apps)

            students_output[sid] = {
                "total_applications": total,
                "shortlisted": shortlisted,
                "review": review,
                "hired": hired,
                "rejected": rejected,

                "shortlist_to_hire_rate": safe_div(hired, shortlisted),
                "review_to_hire_rate": safe_div(hired, review),
                "overall_hire_rate": safe_div(hired, total)
            }

        total_students = len(student_apps)

        # -----------------------------------------
        # FINAL RESPONSE
        # -----------------------------------------
        return {
            "college_name": college_name,

            "application_level": {
                "total_applications": total_applications,
                "shortlisted": len(S_app),
                "review": len(V_app),
                "hired": len(H_app),
                "rejected": len(R_app),

                "shortlist_to_hire_rate": safe_div(len(S_app & H_app), len(S_app)),
                "review_to_hire_rate": safe_div(len(V_app & H_app), len(V_app)),
                "overall_hire_rate": safe_div(len(H_app), total_applications),

                "shortlist_dropoff_rate": safe_div(len(S_app - H_app), len(S_app)),
                "review_dropoff_rate": safe_div(len(V_app - H_app), len(V_app)),
            },

            "student_level": {
                "total_students": total_students,
                "shortlisted": len(S_stu),
                "review": len(V_stu),
                "hired": len(H_stu),
                "rejected": len(R_stu),
                "pending": len(P_stu),

                "overall_hire_rate": safe_div(len(H_stu), total_students),
            },

            "students": students_output
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
import json
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

            # 🔥 DOUBLE PARSE FIX
            while isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    break

            if not isinstance(result, dict):
                continue

            failure = result.get("failure_diagnosis")
            if not failure:
                continue

            reasons = failure.get("primary_reasons", [])

            for item in reasons:
                if isinstance(item, dict):
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