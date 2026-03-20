def build_candidate_report(result, explanation, alternatives):
    return {
        "candidate_summary": {
            "role": result.get("target_role"),
            "readiness_score": result.get("job_readiness_score"),
            "placement_probability": result.get("placement_probability"),
            "final_decision": result.get("final_decision"),
            "confidence_score": round(result.get("final_score", 0) / 100, 2)
        },

        "strengths": explanation["positive_signals"],
        "weaknesses": explanation["negative_signals"],

        "top_skill_gaps": [
            s["skill"] if isinstance(s, dict) else s
            for s in result.get("missing_skills", [])[:5]
        ],

        "improvement_priority": [
            {
                "skill": s["skill"] if isinstance(s, dict) else s,
                "priority": "High"
            }
            for s in result.get("missing_skills", [])[:3]
        ],

        "career_direction": {
            "best_fit_role": result.get("target_role"),
            "alternatives": alternatives
        },

        "explanation": explanation
    }