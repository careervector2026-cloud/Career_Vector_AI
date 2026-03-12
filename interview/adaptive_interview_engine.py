import random

from interview.difficulty_engine import determine_difficulty, adjust_difficulty
from interview.interview_engine import QUESTION_BANK
from interview.github_question_generator import generate_github_questions
from interview.github_repo_fetcher import fetch_github_repositories

from resume_parser import parse_resume_from_url
from app import extract_skills, resume_jd_match
from github_analyzer import analyze_github_async
from interview.answer_analyzer import evaluate_interview


class AdaptiveInterview:

    def __init__(self, jd_text, resume_url, github_url, n_questions):

        self.jd_text = jd_text
        self.resume_url = resume_url
        self.github_url = github_url
        self.n_questions = n_questions

        self.asked = []
        self.current_question = None
        self.current_index = 0

        self.question_pool = []

    # -------------------------------------------------
    # ROLE INFERENCE
    # -------------------------------------------------

    def infer_role(self, jd_text: str):

        jd = jd_text.lower()

        if any(x in jd for x in ["react", "frontend", "javascript", "html", "css"]):
            return "frontend"

        if any(x in jd for x in ["full stack", "fullstack"]):
            return "fullstack"

        if any(x in jd for x in ["machine learning", "ml", "deep learning"]):
            return "machine_learning"

        if any(x in jd for x in ["data scientist", "data science", "pandas", "statistics"]):
            return "data_science"

        return "backend"

    # -------------------------------------------------
    # INITIAL PIPELINE
    # -------------------------------------------------

    async def initialize_pipeline(self):

        resume_text = parse_resume_from_url(self.resume_url)

        jd_skills = extract_skills(self.jd_text)

        match_result = resume_jd_match(self.resume_url, self.jd_text)

        self.matched_skills = match_result["matched_skills"]
        self.missing_skills = match_result["missing_skills"]

        # GitHub skill scoring
        github_result = await analyze_github_async(
            self.github_url,
            set(jd_skills)
        )

        self.github_score = github_result["score"]

        # Fetch repositories separately for question generation
        if self.github_url:
            try:
                self.github_data = await fetch_github_repositories(self.github_url)
            except Exception:
                self.github_data = {}
        else:
            self.github_data = {}

        # placeholder scores
        leetcode_score = 0.5
        readiness_score = 0.6

        self.difficulty = determine_difficulty(
            self.github_score,
            leetcode_score,
            readiness_score
        )

        self.question_pool = self._build_question_pool()

    # -------------------------------------------------
    # QUESTION POOL BUILDER
    # -------------------------------------------------

    def _build_question_pool(self):

        role = self.infer_role(self.jd_text)

        role_bank = QUESTION_BANK.get(role, QUESTION_BANK.get("concept", {}))

        concept_questions = []
        coding_questions = QUESTION_BANK.get("coding", [])
        system_questions = QUESTION_BANK.get("system_design", [])

        for skill in self.missing_skills + self.matched_skills:

            if skill in role_bank:
                concept_questions.extend(role_bank[skill])

        github_questions = generate_github_questions(self.github_data, max_questions=4)

        question_pool = (
                concept_questions
                + coding_questions
                + system_questions
                + github_questions
        )

        random.shuffle(question_pool)

        return question_pool

    # -------------------------------------------------
    # NEXT QUESTION
    # -------------------------------------------------

    def next_question(self):

        # stop if required questions completed
        if self.current_index >= self.n_questions:
            return None

        # remaining questions
        remaining = [
            q for q in self.question_pool
            if q not in self.asked
        ]

        if not remaining:
            return None

        # difficulty filtered candidates
        candidates = [
            q for q in remaining
            if q.get("difficulty", "medium") == self.difficulty
        ]

        # fallback to any remaining question
        if not candidates:
            candidates = remaining

        if not candidates:
            return None

        question = random.choice(candidates)

        self.asked.append(question)
        self.current_question = question
        self.current_index += 1

        return question

    # -------------------------------------------------
    # ANSWER SUBMISSION
    # -------------------------------------------------

    def submit_answer(self, answer):

        result = evaluate_interview([
            {
                "question": self.current_question["question"],
                "answer": answer,
                "expected_answer": self.current_question["expected_answer"],
                "keywords": self.current_question["keywords"]
            }
        ])

        score = float(result["question_scores"][0]["score"])

        self.difficulty = adjust_difficulty(
            self.difficulty,
            score
        )

        return score