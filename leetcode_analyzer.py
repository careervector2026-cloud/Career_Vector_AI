import httpx

LEETCODE_API_URL = "https://leetcode.com/graphql"


async def analyze_leetcode_async(username: str):
    if not username:
        return {
            "score": 0.0,
            "easy": 0,
            "medium": 0,
            "hard": 0,
            "note": "No LeetCode username"
        }

    query = """
    query getUserProfile($username: String!) {
      matchedUser(username: $username) {
        submitStats: submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
      }
    }
    """

    variables = {"username": username}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                LEETCODE_API_URL,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"}
            )

        if response.status_code != 200:
            return {
                "score": 0.0,
                "easy": 0,
                "medium": 0,
                "hard": 0,
                "note": f"LeetCode API HTTP {response.status_code}"
            }

        data = response.json()

        user_data = data.get("data", {}).get("matchedUser")

        if not user_data:
            return {
                "score": 0.0,
                "easy": 0,
                "medium": 0,
                "hard": 0,
                "note": "Invalid LeetCode username"
            }

        submissions = user_data["submitStats"]["acSubmissionNum"]

        easy = medium = hard = 0

        for item in submissions:
            if item["difficulty"] == "Easy":
                easy = item["count"]
            elif item["difficulty"] == "Medium":
                medium = item["count"]
            elif item["difficulty"] == "Hard":
                hard = item["count"]

        # Weighted DSA scoring
        raw_score = (easy * 0.2 + medium * 0.5 + hard * 0.8) / 100
        score = min(raw_score, 1.0)

        return {
            "score": round(score, 2),
            "easy": easy,
            "medium": medium,
            "hard": hard,
            "note": "LeetCode GraphQL analysis"
        }

    except Exception as e:
        return {
            "score": 0.0,
            "easy": 0,
            "medium": 0,
            "hard": 0,
            "note": f"LeetCode request failed: {str(e)}"
        }