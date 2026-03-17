def infer_role_policy(jd_text: str) -> str:
    jd = jd_text.lower()

    # 1️⃣ Full Stack (highest priority)
    if any(k in jd for k in [
        "full stack", "mern", "mean", "frontend and backend"
    ]):
        return "resume_github_leetcode"

    # 2️⃣ Frontend (must come BEFORE DSA check)
    if any(k in jd for k in [
        "frontend", "react", "angular", "vue"
    ]):
        return "resume_github"

    # 3️⃣ Backend / Project-driven
    if any(k in jd for k in [
        "spring boot", "django", "backend",
        "microservices", "rest api"
    ]):
        return "resume_github"

    # 4️⃣ ML / Data
    if any(k in jd for k in [
        "machine learning", "data scientist",
        "deep learning", "nlp"
    ]):
        return "resume_github"

    # 5️⃣ Pure DSA role (only if nothing else matched)
    if any(k in jd for k in [
        "competitive programming",
        "coding interview focus"
    ]):
        return "resume_leetcode"

    return "resume_only"