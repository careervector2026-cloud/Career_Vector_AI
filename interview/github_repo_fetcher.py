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