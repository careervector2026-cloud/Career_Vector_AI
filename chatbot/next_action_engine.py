#next_action_engine.py
def recommend_next_action(profile):

    readiness = profile["job_readiness"]["job_readiness_score"]
    missing = profile["missing_skills"]
    github_score = profile["github_score"]
    leetcode_score = profile["leetcode_score"]

    # -----------------------------------------
    # Low readiness
    # -----------------------------------------

    if readiness < 40:

        if missing:
            return {
                "action": "LEARN_SKILLS",
                "message": f"You should start by learning {missing[:2]}."
            }

        return {
            "action": "FOUNDATION",
            "message": "Focus on building core programming and problem-solving skills."
        }

    # -----------------------------------------
    # Medium readiness
    # -----------------------------------------

    if readiness < 70:

        if github_score < 0.4:

            return {
                "action": "BUILD_PROJECTS",
                "message": "Improving your GitHub projects can significantly increase your chances."
            }

        if leetcode_score < 0.4:

            return {
                "action": "PRACTICE_DSA",
                "message": "Practicing algorithms and data structures will improve your placement chances."
            }

        return {
            "action": "INTERVIEW_PREP",
            "message": "You are close to being job ready. Start practicing interview questions."
        }

    # -----------------------------------------
    # High readiness
    # -----------------------------------------

    return {
        "action": "APPLY_JOBS",
        "message": "You are job ready. Start applying for relevant roles."
    }