import json
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from resume_parser import parse_resume_from_url

model = SentenceTransformer("all-MiniLM-L6-v2")

with open("skills.json") as f:
    SKILLS = json.load(f)

def extract_skills(text: str):
    found = set()
    for skill, aliases in SKILLS.items():
        for a in aliases:
            if a in text:
                found.add(skill)
    return found

def compute_jd_skill_weights(jd_text, jd_skills):
    words = jd_text.split()
    freq = Counter(words)
    weights = {}

    for skill in jd_skills:
        tokens = skill.split()
        count = sum(freq.get(t, 0) for t in tokens)

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

def resume_jd_match(resume_url: str, jd_text: str):
    resume_text = parse_resume_from_url(resume_url)
    jd_text = jd_text.lower()

    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)

    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills

    weights = compute_jd_skill_weights(jd_text, jd_skills)
    total_weight = sum(weights.values())
    matched_weight = sum(weights[s] for s in matched)

    skill_score = matched_weight / max(total_weight, 1)

    embeddings = model.encode([resume_text, jd_text])
    semantic_score = float(
        cosine_similarity(
            embeddings[0].reshape(1, -1),
            embeddings[1].reshape(1, -1)
        )[0][0]
    )

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
