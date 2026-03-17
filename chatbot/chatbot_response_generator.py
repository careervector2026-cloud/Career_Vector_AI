def generate_response(intent, data):

    # -----------------------------------------
    # JOB READINESS
    # -----------------------------------------

    if intent == "JOB_READINESS":

        score = data["job_readiness"]["job_readiness_score"]
        level = data["job_readiness"]["readiness_level"]

        message = f"Your job readiness score is {score}. This indicates you are currently at a {level} readiness level."

        next_action = data.get("next_action")

        if next_action:
            message += " " + next_action["message"]

        return message

    # -----------------------------------------
    # SKILL GAP
    # -----------------------------------------

    if intent == "SKILL_GAP":

        missing = data["skill_gap"]["missing_skills"]

        if not missing:
            return "Great news! You already match most of the required skills."

        skills = []

        for s in missing[:3]:
            if isinstance(s, dict):
                skills.append(s["skill"])
            else:
                skills.append(s)

        return (
            "To improve your chances, you should focus on learning: "
            + ", ".join(skills)
            + "."
        )

    # -----------------------------------------
    # JOB MATCH
    # -----------------------------------------

    if intent == "JOB_MATCH":

        matches = data["matches"]

        if not matches:
            return "I couldn't find strong job matches for your profile yet."

        top = matches[0]

        return (
            f"The best matching role right now has a score of {top['final_score']}. "
            "You may want to explore that opportunity."
        )

    # -----------------------------------------
    # FAILURE DIAGNOSIS
    # -----------------------------------------

    if intent == "FAILURE_REASON":

        diagnosis = data.get("failure_diagnosis")

        if not diagnosis:
            return (
                "Your application was not shortlisted mainly due to "
                "missing skills or insufficient signals."
            )

        primary = diagnosis.get("primary_reasons", [])
        secondary = diagnosis.get("secondary_reasons", [])

        message = "Your application was not shortlisted due to the following reasons: "

        if primary:
            message += "Primary issues include " + ", ".join(primary[:2]) + ". "

        if secondary:
            message += "Additional factors include " + ", ".join(secondary[:2]) + ". "

        return message.strip()

    # -----------------------------------------
    # LEARNING PATH
    # -----------------------------------------

    if intent == "LEARNING_PATH":

        steps = data["learning_path"].get("learning_path", [])

        if not steps:
            return "I could not generate a learning path right now."

        first = steps[0]["skill"]

        return (
            f"I recommend starting with {first}. "
            "This skill will significantly improve your readiness."
        )

    # -----------------------------------------
    # CAREER ADVICE
    # -----------------------------------------

    if intent == "CAREER_ADVICE":

        roles = data["career_recommendations"]

        if not roles:
            return "I couldn't determine the best role yet."

        top = roles[0]["role"]

        return (
            f"Based on your current profile, the best role to target is {top}."
        )

    # -----------------------------------------
    # DEFAULT
    # -----------------------------------------

    return "I'm here to help with your career questions."