def infer_role_policy(jd_text: str) -> str:
    jd = jd_text.lower()

    # 1️⃣ Full Stack (highest priority)
    if any(k in jd for k in [
        "full stack", "mern", "mean", "frontend and backend"
    ]):
        return "resume_github_leetcode"

    # 2️⃣ DSA / Competitive Programming
    if any(k in jd for k in [
        "data structures", "algorithms", "dsa",
        "competitive programming", "problem solving"
    ]):
        return "resume_leetcode"

    # 3️⃣ Project-driven roles (GitHub)
    if any(k in jd for k in [
        # Backend
        "spring boot", "django", "backend developer",
        "microservices", "rest api",

        # ML / Data
        "machine learning", "data scientist",
        "deep learning", "nlp",

        # Frontend
        "frontend", "react", "javascript",

        # DevOps / Cloud
        "devops", "ci/cd", "kubernetes", "docker", "cloud"
    ]):
        return "resume_github"

    # 4️⃣ Fallback
    return "resume_only"
