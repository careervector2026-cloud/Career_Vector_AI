def suggest_alternative_roles(result, jd_list):
    """
    jd_list = list of all available JDs (you already have this)
    """

    current_role = result.get("target_role")
    scores = result.get("multi_jd_scores", {})  # you likely already compute this

    alternatives = []

    for role, score in scores.items():
        if role == current_role:
            continue

        if score >= 70:
            reason = _generate_reason(result, role)

            alternatives.append({
                "role": role,
                "fit_score": score,
                "reason": reason
            })

    # sort by best fit
    alternatives = sorted(alternatives, key=lambda x: x["fit_score"], reverse=True)

    return alternatives[:2]


def _generate_reason(result, role):
    skills = result.get("matched_skills", [])

    if "sql" in skills or "data" in skills:
        return "Strong data-related skills"
    if "testing" in skills:
        return "Good testing and automation exposure"

    return "Better alignment with skill profile"