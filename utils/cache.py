import hashlib


def normalize_jd(jd_text: str):
    return " ".join(jd_text.lower().split())


def generate_cache_key(
    resume_url,
    jd_text,
    github_url=None,
    leetcode_username=None,
    student_id=None   # 🔥 ADD
):
    jd_text = normalize_jd(jd_text)

    raw = f"{resume_url}|{jd_text}|{github_url}|{leetcode_username}|{student_id}"

    return hashlib.md5(raw.encode()).hexdigest()