def generate_ats_fix_suggestions(resume_jd, ats_result):

    suggestions = []

    missing_skills = resume_jd.get("missing_skills", [])

    # -------------------------------------------------
    # SKILL FIXES
    # -------------------------------------------------

    for skill in missing_skills[:5]:

        suggestions.append({
            "type": "skill_missing",
            "skill": skill,
            "suggestion": f"Add '{skill}' to your experience or projects section if applicable."
        })

    # -------------------------------------------------
    # STRUCTURE FIX
    # -------------------------------------------------

    if ats_result.get("resume_completeness", 100) < 70:

        suggestions.append({
            "type": "resume_structure",
            "suggestion": "Include sections like Skills, Projects, Experience, Education."
        })

    # -------------------------------------------------
    # FORMAT FIX
    # -------------------------------------------------

    if ats_result.get("format_score", 100) < 80:

        suggestions.append({
            "type": "format",
            "suggestion": "Avoid tables, images, and complex formatting."
        })

    # -------------------------------------------------
    # KEYWORD FIX
    # -------------------------------------------------

    if ats_result.get("keyword_coverage", 100) < 60:

        suggestions.append({
            "type": "keyword",
            "suggestion": "Add more keywords from the job description."
        })

    return suggestions