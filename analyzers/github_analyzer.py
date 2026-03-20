#github_analyzer.py
import os
from dotenv import load_dotenv
from analyzers.http_client import get_http_client

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

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
        client = get_http_client()

        resp = await client.get(repos_url, headers=HEADERS)

        # 🔴 Handle HTTP errors properly
        if resp.status_code != 200:
            return {
                "score": 0.0,
                "evidence": [],
                "note": f"GitHub API HTTP {resp.status_code}"
            }

        repos = resp.json()

        # 🔴 Validate response structure
        if not isinstance(repos, list):
            return {
                "score": 0.0,
                "evidence": [],
                "note": "GitHub API error or rate limit"
            }

        # 🔴 Extract evidence
        for repo in repos:
            text_blob = (
                (repo.get("name") or "") +
                (repo.get("description") or "") +
                (repo.get("language") or "")
            ).lower()

            for skill in jd_skills:
                if skill in text_blob:
                    evidence.add(skill)

        # 🔴 Safe scoring
        total_skills = max(len(jd_skills), 1)
        score = min(len(evidence) / total_skills, 1.0)

        return {
            "score": round(score, 2),
            "evidence": sorted(evidence),
            "note": "GitHub async repo-level analysis"
        }

    except Exception as e:
        return {
            "score": 0.0,
            "evidence": [],
            "note": f"GitHub request failed: {str(e)}"
        }