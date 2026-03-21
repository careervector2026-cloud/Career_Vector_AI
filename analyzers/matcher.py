#matcher.py
import asyncio
import json
import re
from collections import Counter

import numpy as np

from analyzers.model_registry import get_embedding_model
from analyzers.resume_parser import parse_resume_from_url
from analyzers.jd_cache import get_jd_embedding_cached
# -------------------------------------------------
# LOAD SKILLS
# -------------------------------------------------
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
skills_file = BASE_DIR / "data" / "skills.json"

with open(skills_file, encoding="utf-8") as f:
    SKILLS = json.load(f)

# -------------------------------------------------
# MEMORY CACHE (LEVEL 1 CACHE)
# -------------------------------------------------
_resume_memory_cache = {}

# -------------------------------------------------
# STACK EXPANSION
# -------------------------------------------------
STACKS = {
    "mern": ["mongodb", "express", "react", "node.js"],
    "mean": ["mongodb", "express", "angular", "node.js"],
    "pern": ["postgresql", "express", "react", "node.js"],
    "lamp": ["mysql"]
}


def expand_stack_mentions(text: str, skills_found: set):
    text_lower = text.lower()

    for stack, atomic_skills in STACKS.items():
        if re.search(rf"\b{re.escape(stack)}\b", text_lower):
            for skill in atomic_skills:
                if skill in SKILLS:
                    skills_found.add(skill)

    return skills_found


# -------------------------------------------------
# SKILL EXTRACTION
# -------------------------------------------------
def extract_skills(text: str):
    text_lower = text.lower()
    found = set()

    for skill, aliases in SKILLS.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias.lower())}\b", text_lower):
                found.add(skill)
                break

    return found


# -------------------------------------------------
# JD SKILL WEIGHTS
# -------------------------------------------------
def compute_jd_skill_weights(jd_text, jd_skills):
    words = re.findall(r"\w+", jd_text.lower())
    freq = Counter(words)

    weights = {}

    for skill in jd_skills:
        tokens = skill.split()
        count = sum(freq.get(t.lower(), 0) for t in tokens)

        if count >= 5:
            weight = 3.0
        elif count >= 3:
            weight = 2.5
        elif count >= 2:
            weight = 2.0
        elif count == 1:
            weight = 1.5
        else:
            weight = 1.0

        weights[skill] = weight

    return weights


# -------------------------------------------------
# SEMANTIC SIMILARITY
# -------------------------------------------------
def compute_semantic_similarity(resume_embedding, jd_embedding):

    if resume_embedding is None or jd_embedding is None:
        return 0.0

    try:
        return float(np.dot(resume_embedding, jd_embedding))
    except Exception:
        return 0.0


# -------------------------------------------------
# 🔥 RESUME CACHE (LEVEL 1 + LEVEL 2)
# -------------------------------------------------
async def get_or_compute_resume_data(resume_url: str):

    # -------------------------------
    # LEVEL 1: MEMORY CACHE
    # -------------------------------
    if resume_url in _resume_memory_cache:
        return _resume_memory_cache[resume_url]

    # -------------------------------
    # LEVEL 2: DB CACHE
    # -------------------------------
    from db.resume_cache_repo import get_cached_resume, store_resume_cache

    cached = await get_cached_resume(resume_url)

    if cached:
        result = (
            cached["resume_text"],
            cached["embedding"]
        )
        _resume_memory_cache[resume_url] = result
        return result

    # -------------------------------
    # COMPUTE
    # -------------------------------
    resume_text = parse_resume_from_url(resume_url)

    model = await get_embedding_model()

    embedding = model.encode(
        resume_text,
        normalize_embeddings=True
    )

    embedding = np.array(embedding).astype("float32")

    # -------------------------------
    # STORE DB
    # -------------------------------
    await store_resume_cache(
        resume_url,
        resume_text,
        embedding
    )

    result = (resume_text, embedding)

    # -------------------------------
    # STORE MEMORY
    # -------------------------------
    _resume_memory_cache[resume_url] = result

    return result


# -------------------------------------------------
# 🔥 MAIN MATCH FUNCTION (ASYNC)
# -------------------------------------------------
async def resume_jd_match_async(resume_url: str, jd_text: str):

    # -------------------------------
    # RESUME CACHE
    # -------------------------------
    resume_text, resume_embedding = await get_or_compute_resume_data(resume_url)

    resume_text = resume_text.lower()
    jd_text = jd_text.lower()

    # -------------------------------
    # SKILLS
    # -------------------------------
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)
    jd_skills = expand_stack_mentions(jd_text, jd_skills)

    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills

    # -------------------------------
    # WEIGHTS
    # -------------------------------
    weights = compute_jd_skill_weights(jd_text, jd_skills)

    total_weight = sum(weights.values())
    matched_weight = sum(weights[s] for s in matched)

    skill_score = matched_weight / max(total_weight, 1)

    # -------------------------------
    # JD EMBEDDING CACHE
    # -------------------------------
    jd_embedding = await get_jd_embedding_cached(jd_text)

    # -------------------------------
    # SEMANTIC SCORE
    # -------------------------------
    semantic_score = compute_semantic_similarity(
        resume_embedding,
        jd_embedding
    )

    # -------------------------------
    # FINAL SCORE
    # -------------------------------
    final_score = round(
        float(0.7 * skill_score + 0.3 * semantic_score),
        2
    )

    return {
        "final_match_score": final_score,
        "matched_skills": list(matched),
        "missing_skills": list(missing),
        "jd_skill_weights": weights
    }


# -------------------------------------------------
# 🔥 BACKWARD COMPATIBILITY
# -------------------------------------------------

def resume_jd_match(resume_url: str, jd_text: str):
    """
    SAFE sync wrapper (no event loop crash)
    """
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(
            lambda: asyncio.run(resume_jd_match_async(resume_url, jd_text))
        )
        return future.result()