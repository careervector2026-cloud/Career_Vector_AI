# cache.py

import hashlib

# -------------------------------------------------
# NORMALIZATION UTILITIES
# -------------------------------------------------

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.lower().strip().split())


def safe_str(value):
    return value if value is not None else ""


# -------------------------------------------------
# JD ID GENERATION (CRITICAL FIX)
# -------------------------------------------------

def generate_jd_id(jd_text: str) -> str:
    normalized = normalize_text(jd_text)
    return hashlib.sha256(normalized.encode()).hexdigest()


# -------------------------------------------------
# CACHE KEY GENERATION (PRODUCTION SAFE)
# -------------------------------------------------

def generate_cache_key(
    resume_url: str,
    jd_text: str,
    github_url: str = None,
    leetcode_username: str = None,
    student_id: str = None
) -> str:
    jd_id = generate_jd_id(jd_text)

    raw = "|".join([
        safe_str(student_id),       # primary identity
        jd_id,                      # stable job identity
        safe_str(resume_url),
        safe_str(github_url),
        safe_str(leetcode_username)
    ])

    return hashlib.sha256(raw.encode()).hexdigest()