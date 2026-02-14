import httpx

async def analyze_leetcode_async(username: str):
    if not username:
        return {
            "score": 0.0,
            "note": "No LeetCode username"
        }

    url = f"https://leetcode-stats-api.herokuapp.com/{username}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            data = (await client.get(url)).json()

        easy = data.get("easySolved", 0)
        medium = data.get("mediumSolved", 0)
        hard = data.get("hardSolved", 0)

        score = min(
            (easy * 0.2 + medium * 0.5 + hard * 0.8) / 100,
            1.0
        )

        return {
            "score": round(score, 2),
            "easy": easy,
            "medium": medium,
            "hard": hard,
            "note": "LeetCode async analysis"
        }

    except Exception:
        return {
            "score": 0.0,
            "note": "LeetCode request failed"
        }
