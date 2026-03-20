def generate_explanation(result):
    """
    result = final orchestrator output (dict)
    """

    positive = []
    negative = []

    # -------------------------
    # SKILL MATCH
    # -------------------------
    skill_match = result.get("jd_match_score", 0)

    if skill_match >= 80:
        positive.append(f"High JD skill match ({skill_match}%)")
    elif skill_match >= 60:
        positive.append(f"Moderate JD skill match ({skill_match}%)")
    else:
        negative.append(f"Low JD skill match ({skill_match}%)")

    # -------------------------
    # GITHUB SIGNAL
    # -------------------------
    github_score = result.get("github_score", 0)

    if github_score >= 70:
        positive.append("Strong GitHub profile")
    elif github_score >= 40:
        positive.append("Average GitHub activity")
    else:
        negative.append("Weak or no GitHub presence")

    # -------------------------
    # LEETCODE / DSA
    # -------------------------
    dsa_score = result.get("leetcode_score", 0)

    if dsa_score >= 70:
        positive.append("Strong DSA problem solving")
    elif dsa_score >= 40:
        positive.append("Moderate DSA skills")
    else:
        negative.append("Low DSA proficiency")

    # -------------------------
    # SKILL GAPS
    # -------------------------
    gaps = result.get("missing_skills", [])
    if len(gaps) > 5:
        negative.append("Multiple critical skill gaps")

    # -------------------------
    # FINAL DECISION REASON
    # -------------------------
    decision = result.get("final_decision", "review")

    if decision == "shortlist":
        key_reason = "Strong overall profile with high alignment"
    elif decision == "reject":
        key_reason = "Insufficient alignment with job requirements"
    else:
        key_reason = "Moderate profile requiring further evaluation"

    return {
        "positive_signals": positive,
        "negative_signals": negative,
        "key_reason": key_reason
    }