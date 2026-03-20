#interview_engine.py
import json
import random
from pathlib import Path

from interview.github_question_generator import generate_github_questions
from interview.difficulty_engine import determine_difficulty

QUESTION_BANK_PATH = Path(__file__).parent / "question_bank.json"

with open(QUESTION_BANK_PATH, "r", encoding="utf-8") as f:
    QUESTION_BANK = json.load(f)


def generate_questions(
        missing_skills,
        matched_skills,
        github_data,
        github_score,
        leetcode_score,
        readiness_score,
        n_questions=10
):

    difficulty = determine_difficulty(
        github_score,
        leetcode_score,
        readiness_score
    )

    questions = []

    # Questions from missing skills
    for skill in missing_skills:

        skill = skill.lower()

        if skill in QUESTION_BANK:

            for q in QUESTION_BANK[skill]:

                if q["difficulty"] == difficulty:

                    questions.append(q)

    # Questions from matched skills
    for skill in matched_skills:

        skill = skill.lower()

        if skill in QUESTION_BANK:

            questions.extend(QUESTION_BANK[skill])

    # Coding questions
    questions.extend(QUESTION_BANK.get("coding", []))

    # System design questions
    questions.extend(QUESTION_BANK.get("system_design", []))

    # GitHub questions
    github_questions = generate_github_questions(github_data)

    questions.extend(github_questions)

    random.shuffle(questions)

    return questions[:n_questions]