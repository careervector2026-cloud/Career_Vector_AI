import json
import re
import os
from collections import Counter
from functools import lru_cache

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from resume_parser import parse_resume_from_url

# -------------------------------------------------
# OPTIONAL FAISS ACCELERATION
# -------------------------------------------------

try:
    import faiss
    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False


# -------------------------------------------------
# SAFE MODEL LOADING (Lazy + Cached)
# -------------------------------------------------

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


@lru_cache(maxsize=1)
def get_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(
            MODEL_NAME,
            cache_folder="./hf_cache"
        )
    except Exception:
        return None


# -------------------------------------------------
# LOAD SKILLS
# -------------------------------------------------

with open("skills.json", encoding="utf-8") as f:
    SKILLS = json.load(f)


# -------------------------------------------------
# STACK EXPANSION LAYER
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
# SAFE SKILL EXTRACTION
# -------------------------------------------------

def extract_skills(text: str):

    text_lower = text.lower()
    found = set()

    for skill, aliases in SKILLS.items():

        for alias in aliases:

            pattern = rf"\b{re.escape(alias.lower())}\b"

            if re.search(pattern, text_lower):
                found.add(skill)
                break

    return found


# -------------------------------------------------
# JD SKILL WEIGHTING
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
# EMBEDDING CACHE LAYER
# -------------------------------------------------

@lru_cache(maxsize=512)
def get_resume_embedding(resume_text: str):

    model = get_model()

    if model is None:
        return None

    embedding = model.encode(resume_text)
    return np.array(embedding).astype("float32")


@lru_cache(maxsize=512)
def get_jd_embedding(jd_text: str):

    model = get_model()

    if model is None:
        return None

    embedding = model.encode(jd_text)
    return np.array(embedding).astype("float32")


# -------------------------------------------------
# FAISS SEMANTIC SIMILARITY
# -------------------------------------------------

def compute_semantic_similarity(resume_embedding, jd_embedding):

    if resume_embedding is None or jd_embedding is None:
        return 0.0

    try:

        if FAISS_AVAILABLE:

            dim = resume_embedding.shape[0]

            index = faiss.IndexFlatIP(dim)

            index.add(resume_embedding.reshape(1, -1))

            D, I = index.search(jd_embedding.reshape(1, -1), 1)

            return float(D[0][0])

        else:

            return float(
                cosine_similarity(
                    resume_embedding.reshape(1, -1),
                    jd_embedding.reshape(1, -1)
                )[0][0]
            )

    except Exception:
        return 0.0


# -------------------------------------------------
# MAIN RESUME–JD MATCH FUNCTION
# -------------------------------------------------

def resume_jd_match(resume_url: str, jd_text: str):

    # -------------------------------------------------
    # Parse resume
    # -------------------------------------------------

    resume_text = parse_resume_from_url(resume_url)

    resume_text = resume_text.lower()
    jd_text = jd_text.lower()

    # -------------------------------------------------
    # Extract skills
    # -------------------------------------------------

    resume_skills = extract_skills(resume_text)

    jd_skills = extract_skills(jd_text)

    jd_skills = expand_stack_mentions(jd_text, jd_skills)

    # -------------------------------------------------
    # Skill Overlap
    # -------------------------------------------------

    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills

    # -------------------------------------------------
    # Weighted Skill Score
    # -------------------------------------------------

    weights = compute_jd_skill_weights(jd_text, jd_skills)

    total_weight = sum(weights.values())
    matched_weight = sum(weights[s] for s in matched)

    skill_score = matched_weight / max(total_weight, 1)

    # -------------------------------------------------
    # Semantic Similarity (FAISS Optimized)
    # -------------------------------------------------

    semantic_score = 0.0

    resume_embedding = get_resume_embedding(resume_text)
    jd_embedding = get_jd_embedding(jd_text)

    semantic_score = compute_semantic_similarity(
        resume_embedding,
        jd_embedding
    )

    # -------------------------------------------------
    # Hybrid Score
    # -------------------------------------------------

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