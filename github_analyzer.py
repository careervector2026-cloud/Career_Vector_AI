import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github+json"
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


async def analyze_github_async(github_url: str, jd_skills: set):
    if not github_url or not jd_skills:
        return {
            "score": 0.0,
            "evidence": [],
            "note": "GitHub skipped"
        }

    username = github_url.rstrip("/").split("/")[-1]
    repos_url = f"https://api.github.com/users/{username}/repos"

    evidence = set()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(repos_url, headers=HEADERS)
            repos = resp.json()

            if not isinstance(repos, list):
                return {
                    "score": 0.0,
                    "evidence": [],
                    "note": "GitHub API error or rate limit"
                }

            for repo in repos:
                text_blob = (
                    (repo.get("name") or "") +
                    (repo.get("description") or "") +
                    (repo.get("language") or "")
                ).lower()

                for skill in jd_skills:
                    if skill in text_blob:
                        evidence.add(skill)

        score = min(len(evidence) / len(jd_skills), 1.0)

        return {
            "score": round(score, 2),
            "evidence": sorted(evidence),
            "note": "GitHub async repo-level analysis"
        }

    except Exception:
        return {
            "score": 0.0,
            "evidence": [],
            "note": "GitHub request failed"
        }
