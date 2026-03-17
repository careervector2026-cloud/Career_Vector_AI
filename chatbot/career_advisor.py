#career_advisor

from pipeline.orchestrator import (
    match_student_against_multiple_jds_async
)


async def recommend_best_roles(student_profile, jds):

    results = await match_student_against_multiple_jds_async(
        student_profile,
        jds
    )

    recommendations = []

    for r in results[:3]:

        recommendations.append({
            "role": r["jd_id"],
            "match_score": r["final_score"],
            "readiness": r["job_readiness"]["job_readiness_score"]
        })

    return recommendations
def simulate_skill_improvement(
    current_probability,
    new_skills
):

    impact = len(new_skills) * 0.05

    new_probability = min(
        1.0,
        current_probability + impact
    )

    return {
        "current_probability": current_probability,
        "new_probability": round(new_probability, 2),
        "impact": round(new_probability - current_probability, 2)
    }