# ats_screening.py

from analyzers.model_registry import get_embedding_model
from sklearn.metrics.pairwise import cosine_similarity
from functools import lru_cache

SIMILARITY_THRESHOLD = 0.70


# -------------------------------------------------
# TECHNOLOGY FAMILY MAPPING
# -------------------------------------------------

SKILL_FAMILIES = {
    "spring boot": ["spring", "spring mvc"],
    "mysql": ["mariadb"],
    "postgresql": ["postgres"],
    "docker": ["container", "containers"],
    "microservices": ["distributed systems"],
    "ci/cd": ["jenkins", "github actions", "gitlab ci"],
    "aws": ["amazon web services"],
}


# -------------------------------------------------
# PROXIMITY SKILL RECOVERY (RULE-BASED)
# -------------------------------------------------

def proximity_skill_recovery(missing_skills, matched_skills):

    recovered = []

    for missing in missing_skills:
        if missing in SKILL_FAMILIES:
            family = SKILL_FAMILIES[missing]

            if any(skill in matched_skills for skill in family):
                recovered.append(missing)

    return recovered


# -------------------------------------------------
# SEMANTIC SKILL RECOVERY (MODEL-BASED)
# -------------------------------------------------

async def semantic_skill_recovery(missing_skills, matched_skills):

    if not missing_skills or not matched_skills:
        return []

    model = await get_embedding_model()

    try:
        missing_emb = model.encode(
            missing_skills,
            normalize_embeddings=True
        )

        matched_emb = model.encode(
            matched_skills,
            normalize_embeddings=True
        )

        recovered = []

        for i, skill in enumerate(missing_skills):

            sims = cosine_similarity(
                missing_emb[i].reshape(1, -1),
                matched_emb
            )[0]

            if sims.max() >= SIMILARITY_THRESHOLD:
                recovered.append(skill)

        return recovered

    except Exception:
        return []


# -------------------------------------------------
# PROJECT SKILL DETECTION
# -------------------------------------------------

def detect_project_skills(resume_text, missing_skills):

    if not resume_text:
        return []

    text = resume_text.lower()

    project_words = [
        "project", "built", "developed",
        "implemented", "created"
    ]

    if any(w in text for w in project_words):
        return [s for s in missing_skills if s in text]

    return []


# -------------------------------------------------
# RESUME SECTION DETECTION
# -------------------------------------------------

def detect_resume_sections(resume_text):

    if not resume_text:
        return 60, []

    text = resume_text.lower()

    sections = {
        "education": ["education", "university", "college"],
        "projects": ["project", "projects"],
        "skills": ["skills", "technical skills"],
        "experience": ["experience", "work experience", "internship"]
    }

    detected = []
    score = 0

    for section, keywords in sections.items():

        if any(k in text for k in keywords):
            detected.append(section)
            score += 25

    return score, detected


# -------------------------------------------------
# FORMAT SCORE
# -------------------------------------------------

def ats_format_score(resume_text):

    if not resume_text:
        return 70

    score = 100
    text = resume_text.lower()

    if "|" in text:
        score -= 10

    if "table" in text:
        score -= 10

    if "image" in text:
        score -= 10

    if len(text.split()) < 200:
        score -= 10

    return max(score, 50)


# -------------------------------------------------
# MAIN ATS FUNCTION (ASYNC SAFE)
# -------------------------------------------------

async def compute_ats_screening(resume_jd, resume_text=""):

    matched = resume_jd.get("matched_skills", [])
    missing = resume_jd.get("missing_skills", [])
    weights = resume_jd.get("jd_skill_weights", {})

    # -------------------------------
    # SKILL RECOVERY
    # -------------------------------

    proximity = proximity_skill_recovery(missing, matched)
    semantic = await semantic_skill_recovery(missing, matched)
    project = detect_project_skills(resume_text, missing)

    recovered = list(set(proximity + semantic + project))

    matched_extended = matched + recovered
    missing_filtered = [s for s in missing if s not in recovered]

    # -------------------------------
    # WEIGHTED COVERAGE
    # -------------------------------

    matched_weight = sum(weights.get(s, 1) for s in matched_extended)
    total_weight = sum(weights.values()) or 1

    keyword_coverage = (matched_weight / total_weight) * 100

    # -------------------------------
    # MANDATORY PENALTY
    # -------------------------------

    mandatory = [s for s, w in weights.items() if w >= 2.5]
    missing_mandatory = [s for s in mandatory if s in missing_filtered]

    penalty = len(missing_mandatory) * 10

    # -------------------------------
    # STRUCTURE + FORMAT
    # -------------------------------

    completeness, sections = detect_resume_sections(resume_text)
    format_score = ats_format_score(resume_text)

    # -------------------------------
    # FINAL SCORE
    # -------------------------------

    ats_score = (
        0.55 * keyword_coverage +
        0.25 * completeness +
        0.20 * format_score -
        penalty
    )

    ats_score = round(max(min(ats_score, 100), 0), 2)

    # -------------------------------
    # DECISION
    # -------------------------------

    if ats_score >= 65:
        decision = "pass"
    elif ats_score >= 45:
        decision = "review"
    else:
        decision = "reject"

    return {
        "ats_score": ats_score,
        "decision": decision,
        "keyword_coverage": round(keyword_coverage, 2),
        "missing_mandatory_skills": missing_mandatory,
        "proximity_recovered_skills": proximity,
        "semantic_recovered_skills": semantic,
        "project_recovered_skills": project,
        "resume_completeness": completeness,
        "detected_sections": sections,
        "format_score": format_score
    }