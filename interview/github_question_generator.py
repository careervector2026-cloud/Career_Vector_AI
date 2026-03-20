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