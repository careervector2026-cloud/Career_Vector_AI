# ats_screening.py

from matcher import get_model
from sklearn.metrics.pairwise import cosine_similarity
from functools import lru_cache

SIMILARITY_THRESHOLD = 0.70


# -------------------------------------------------
# TECHNOLOGY FAMILY MAPPING (FINAL IMPROVEMENT)
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


def proximity_skill_recovery(missing_skills, matched_skills):

    recovered = []

    for missing in missing_skills:

        if missing in SKILL_FAMILIES:

            family = SKILL_FAMILIES[missing]

            if any(skill in matched_skills for skill in family):
                recovered.append(missing)

    return recovered


# -------------------------------------------------
# CACHE JD EMBEDDINGS (FAST RANKING)
# -------------------------------------------------

@lru_cache(maxsize=128)
def get_jd_skill_embeddings(skills_tuple):

    model = get_model()

    if model is None:
        return None

    return model.encode(list(skills_tuple))


# -------------------------------------------------
# SEMANTIC SKILL RECOVERY
# -------------------------------------------------

def semantic_skill_recovery(missing_skills, matched_skills):

    if not missing_skills or not matched_skills:
        return []

    model = get_model()

    if model is None:
        return []

    try:

        missing_emb = model.encode(missing_skills)
        matched_emb = get_jd_skill_embeddings(tuple(matched_skills))

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
        "project",
        "built",
        "developed",
        "implemented",
        "created"
    ]

    recovered = []

    if any(word in text for word in project_words):

        for skill in missing_skills:
            if skill in text:
                recovered.append(skill)

    return recovered


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
# ATS FORMAT SCORE
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
# MAIN ATS FUNCTION
# -------------------------------------------------

def compute_ats_screening(resume_jd, resume_text=""):

    matched = resume_jd.get("matched_skills", [])
    missing = resume_jd.get("missing_skills", [])
    weights = resume_jd.get("jd_skill_weights", {})

    # ----------------------------------------------
    # SKILL RECOVERY LAYERS
    # ----------------------------------------------

    proximity_recovered = proximity_skill_recovery(
        missing,
        matched
    )

    semantic_recovered = semantic_skill_recovery(
        missing,
        matched
    )

    project_recovered = detect_project_skills(
        resume_text,
        missing
    )

    recovered_skills = list(
        set(
            proximity_recovered
            + semantic_recovered
            + project_recovered
        )
    )

    matched_extended = matched + recovered_skills
    missing_filtered = [
        s for s in missing if s not in recovered_skills
    ]

    # ----------------------------------------------
    # WEIGHTED KEYWORD COVERAGE
    # ----------------------------------------------

    matched_weight = sum(
        weights.get(s, 1) for s in matched_extended
    )

    total_weight = sum(weights.values()) or 1

    keyword_coverage = (
        matched_weight / total_weight
    ) * 100

    # ----------------------------------------------
    # MANDATORY SKILL PENALTY
    # ----------------------------------------------

    mandatory_skills = [
        skill for skill, w in weights.items()
        if w >= 2.5
    ]

    missing_mandatory = [
        s for s in mandatory_skills
        if s in missing_filtered
    ]

    mandatory_penalty = len(missing_mandatory) * 10

    # ----------------------------------------------
    # RESUME COMPLETENESS
    # ----------------------------------------------

    completeness_score, detected_sections = detect_resume_sections(
        resume_text
    )

    if not resume_text:
        completeness_score = 60

    # ----------------------------------------------
    # FORMAT SCORE
    # ----------------------------------------------

    format_score = ats_format_score(resume_text)

    # ----------------------------------------------
    # FINAL ATS SCORE
    # ----------------------------------------------

    ats_score = (
        0.55 * keyword_coverage +
        0.25 * completeness_score +
        0.20 * format_score
        - mandatory_penalty
    )

    ats_score = round(max(min(ats_score, 100), 0), 2)

    # ----------------------------------------------
    # DECISION
    # ----------------------------------------------

    if ats_score >= 65:
        decision = "pass"

    elif ats_score >= 45:
        decision = "review"

    else:
        decision = "reject"

    # ----------------------------------------------
    # OUTPUT
    # ----------------------------------------------

    return {

        "ats_score": ats_score,
        "decision": decision,

        "keyword_coverage": round(keyword_coverage, 2),

        "missing_mandatory_skills": missing_mandatory,

        "proximity_recovered_skills": proximity_recovered,
        "semantic_recovered_skills": semantic_recovered,
        "project_recovered_skills": project_recovered,

        "resume_completeness": completeness_score,
        "detected_sections": detected_sections,

        "format_score": format_score
    }