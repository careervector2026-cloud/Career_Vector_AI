def generate_ats_fix_suggestions(resume_jd, ats_result):

    suggestions = []

    missing_skills = resume_jd.get("missing_skills", [])

    # -------------------------------------------------
    # Skill Suggestions
    # -------------------------------------------------

    for skill in missing_skills[:5]:

        suggestions.append({
            "type": "skill_missing",
            "skill": skill,
            "suggestion": f"Add '{skill}' to your experience or projects section if you have used it."
        })

    # -------------------------------------------------
    # Resume Completeness Suggestions
    # -------------------------------------------------

    completeness = ats_result.get("resume_completeness", 100)

    if completeness < 70:

        suggestions.append({
            "type": "resume_structure",
            "suggestion": "Add clear sections like Skills, Projects, Experience, and Education."
        })

    # -------------------------------------------------
    # Format Suggestions
    # -------------------------------------------------

    format_score = ats_result.get("format_score", 100)

    if format_score < 80:

        suggestions.append({
            "type": "format",
            "suggestion": "Avoid tables, images, or complex formatting that ATS systems cannot parse."
        })

    # -------------------------------------------------
    # Keyword Coverage Suggestions
    # -------------------------------------------------

    keyword_score = ats_result.get("keyword_coverage", 100)

    if keyword_score < 60:

        suggestions.append({
            "type": "keyword",
            "suggestion": "Include more job-specific keywords from the job description."
        })

    return suggestions