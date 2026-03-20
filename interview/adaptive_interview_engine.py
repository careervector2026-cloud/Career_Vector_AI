#adaptive_interview_engine.py
import random

from interview.difficulty_engine import determine_difficulty, adjust_difficulty
from interview.interview_engine import QUESTION_BANK
from interview.github_question_generator import generate_github_questions
from interview.github_repo_fetcher import fetch_github_repositories

from analyzers.resume_parser import parse_resume_from_url
from analyzers.matcher import extract_skills, resume_jd_match
from analyzers.github_analyzer import analyze_github_async
from interview.answer_analyzer import evaluate_interview


# -------------------------------------------------
# SKILL GRAPH (PROGRESSION PATHS)
# -------------------------------------------------

SKILL_GRAPH = {

    "java": ["spring boot", "microservices", "system design"],
    "spring boot": ["microservices", "docker"],
    "python": ["fastapi", "django", "system design"],
    "react": ["redux", "next.js"],
    "node.js": ["express", "microservices"],
    "docker": ["kubernetes", "ci/cd"],
    "aws": ["microservices", "system design"],
    "data structures": ["algorithms", "system design"]
}


# -------------------------------------------------
# ADAPTIVE INTERVIEW CLASS
# -------------------------------------------------

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
        self.skill_progression = []

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

        if any(x in jd for x in ["data scientist", "data science"]):
            return "data_science"

        return "concept"

    # -------------------------------------------------
    # BUILD SKILL PROGRESSION
    # -------------------------------------------------

    def build_skill_progression(self, skills):

        progression = []

        for skill in skills:

            progression.append(skill)

            if skill in SKILL_GRAPH:
                progression.extend(SKILL_GRAPH[skill])

        # remove duplicates but keep order
        seen = set()
        ordered = []

        for s in progression:
            if s not in seen:
                ordered.append(s)
                seen.add(s)

        return ordered

    # -------------------------------------------------
    # INITIAL PIPELINE
    # -------------------------------------------------

    async def initialize_pipeline(self):

        resume_text = parse_resume_from_url(self.resume_url)

        jd_skills = extract_skills(self.jd_text)

        match_result = resume_jd_match(self.resume_url, self.jd_text)

        self.matched_skills = match_result["matched_skills"]
        self.missing_skills = match_result["missing_skills"]

        github_result = await analyze_github_async(
            self.github_url,
            set(jd_skills)
        )

        self.github_score = github_result["score"]

        if self.github_url:
            try:
                self.github_data = await fetch_github_repositories(self.github_url)
            except Exception:
                self.github_data = {}
        else:
            self.github_data = {}

        # placeholder signals
        leetcode_score = 0.5
        readiness_score = 0.6

        self.difficulty = determine_difficulty(
            self.github_score,
            leetcode_score,
            readiness_score
        )

        # build skill progression graph
        base_skills = list(set(self.matched_skills + self.missing_skills))
        self.skill_progression = self.build_skill_progression(base_skills)

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

        # skill progression based questions
        for skill in self.skill_progression:

            if skill in role_bank:
                concept_questions.extend(role_bank[skill])

        # github project questions
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
    # FOLLOW-UP QUESTION GENERATOR
    # -------------------------------------------------

    def detect_followup(self, answer):

        answer = answer.lower()

        concept_bank = QUESTION_BANK.get("concept", {})

        followups = []

        for skill, questions in concept_bank.items():

            if skill in answer:

                for q in questions:

                    if q not in self.asked:
                        followups.append(q)

        return followups

    # -------------------------------------------------
    # NEXT QUESTION
    # -------------------------------------------------

    def next_question(self):

        if self.current_index >= self.n_questions:
            return None

        remaining = [
            q for q in self.question_pool
            if q not in self.asked
        ]

        if not remaining:
            return None

        # difficulty filter
        candidates = [
            q for q in remaining
            if q.get("difficulty", "medium") == self.difficulty
        ]

        if not candidates:
            candidates = remaining

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

        # adjust difficulty dynamically
        self.difficulty = adjust_difficulty(
            self.difficulty,
            score
        )

        # generate follow-up questions
        followups = self.detect_followup(answer)

        for q in followups:

            if q not in self.question_pool:
                self.question_pool.insert(0, q)

        return score

#answer_analyzer.py
from functools import lru_cache
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np

model = None


# -------------------------------------------------
# MODEL LOADING (SAFE + LAZY)
# -------------------------------------------------

def get_model():

    global model

    if model is None:
        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    return model


# -------------------------------------------------
# EMBEDDING CACHE
# Prevent recomputing same embeddings
# -------------------------------------------------

@lru_cache(maxsize=512)
def encode_text(text: str):

    model = get_model()

    embedding = model.encode(text)

    return np.array(embedding).astype("float32")


# -------------------------------------------------
# INTERVIEW EVALUATION
# -------------------------------------------------

def evaluate_interview(answers):

    scores = []
    results = []

    for item in answers:

        answer = item["answer"]
        expected = item["expected_answer"]
        keywords = item["keywords"]

        # cached embeddings
        emb1 = encode_text(answer)
        emb2 = encode_text(expected)

        similarity = cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0][0]

        keyword_hits = [
            k for k in keywords
            if k.lower() in answer.lower()
        ]

        keyword_score = len(keyword_hits) / max(len(keywords), 1)

        final_score = float((0.7 * similarity) + (0.3 * keyword_score))

        scores.append(final_score)

        results.append({
            "question": item["question"],
            "score": round(float(final_score), 3),
            "matched_keywords": keyword_hits
        })

    overall_score = float(sum(scores) / len(scores)) if scores else 0.0

    return {
        "overall_interview_score": round(overall_score, 3),
        "question_scores": results
    }

#difficulty_engine.py
def determine_difficulty(github_score, leetcode_score, readiness_score):

    combined = (github_score + leetcode_score + readiness_score) / 3

    if combined > 0.75:
        return "hard"

    if combined > 0.45:
        return "medium"

    return "easy"

def adjust_difficulty(current_difficulty, score):

    levels = ["easy", "medium", "hard"]

    idx = levels.index(current_difficulty)

    if score > 0.75 and idx < 2:
        idx += 1

    elif score < 0.45 and idx > 0:
        idx -= 1

    return levels[idx]

#github_code_analyzer.py
import httpx
import base64


async def fetch_repo_structure(owner, repo, headers):

    url = f"https://api.github.com/repos/{owner}/{repo}/contents"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            return []

        files = resp.json()

        return [f["name"] for f in files]


async def fetch_readme(owner, repo, headers):

    url = f"https://api.github.com/repos/{owner}/{repo}/readme"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            return ""

        data = resp.json()

        content = base64.b64decode(data["content"]).decode("utf-8")

        return content[:1000]

#github_question_generator.py
import random


def generate_github_questions(github_data, max_questions=4):

    questions = []

    repos = github_data.get("repositories", [])

    for repo in repos:

        repo_name = repo.get("name", "")
        description = repo.get("description", "")
        language = repo.get("language", "")
        files = repo.get("files", [])
        folders = repo.get("folders", [])
        readme = repo.get("readme", "")

        # -------------------------
        # Architecture Question
        # -------------------------

        questions.append({
            "difficulty": "medium",
            "question": f"Explain the overall architecture of your project '{repo_name}'.",
            "expected_answer": "Explain modules, backend services, database and APIs.",
            "keywords": ["architecture", "modules", "api", "database"]
        })

        # -------------------------
        # Folder Structure Question
        # -------------------------

        if folders:
            questions.append({
                "difficulty": "medium",
                "question": f"Why did you organize folders {folders[:3]} in project '{repo_name}'?",
                "expected_answer": "Explain separation of concerns and modular architecture.",
                "keywords": ["structure", "modules", "design"]
            })

        # -------------------------
        # Language Choice
        # -------------------------

        if language:
            questions.append({
                "difficulty": "easy",
                "question": f"Why did you choose {language} for implementing '{repo_name}'?",
                "expected_answer": "Explain language advantages and ecosystem.",
                "keywords": ["language", "performance", "libraries"]
            })

        # -------------------------
        # README Understanding
        # -------------------------

        if readme:
            questions.append({
                "difficulty": "medium",
                "question": f"According to the README of '{repo_name}', what problem does this project solve?",
                "expected_answer": "Explain project goal and functionality.",
                "keywords": ["problem", "solution", "project"]
            })

        # -------------------------
        # Code Organization
        # -------------------------

        if files:
            questions.append({
                "difficulty": "hard",
                "question": f"In '{repo_name}', how did you organize major source files like {files[:2]}?",
                "expected_answer": "Explain modularization and separation of responsibilities.",
                "keywords": ["modules", "files", "architecture"]
            })

    random.shuffle(questions)

    return questions[:max_questions]

#github_repo_fetcher.py
import httpx


async def fetch_github_repositories(github_url):

    username = github_url.rstrip("/").split("/")[-1]

    repos_url = f"https://api.github.com/users/{username}/repos"

    repositories = []

    async with httpx.AsyncClient() as client:

        resp = await client.get(repos_url)

        repos = resp.json()

        for repo in repos[:5]:

            repo_name = repo["name"]

            contents_url = f"https://api.github.com/repos/{username}/{repo_name}/contents"

            content_resp = await client.get(contents_url)

            contents = content_resp.json()

            files = []
            folders = []

            for item in contents:

                if item["type"] == "file":
                    files.append(item["name"])

                if item["type"] == "dir":
                    folders.append(item["name"])

            # README fetch

            readme_url = f"https://api.github.com/repos/{username}/{repo_name}/readme"

            readme_text = ""

            try:
                readme_resp = await client.get(readme_url)

                if readme_resp.status_code == 200:
                    readme_text = "README available"
            except Exception:
                pass

            repositories.append({

                "name": repo_name,
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "files": files,
                "folders": folders,
                "readme": readme_text

            })

    return {"repositories": repositories}

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