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