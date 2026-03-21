from functools import lru_cache
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from analyzers.model_registry import get_model_sync

model = get_model_sync()

# -------------------------------------------------
# EMBEDDING CACHE
# -------------------------------------------------

@lru_cache(maxsize=512)
def encode_text(text: str):

    embedding = EMBEDDING_MODEL.encode(text, normalize_embeddings=True)

    return np.array(embedding).astype("float32")


# -------------------------------------------------
# INTERVIEW EVALUATION
# -------------------------------------------------

def evaluate_interview(answers):

    scores = []
    results = []

    for item in answers:

        answer = item.get("answer", "")
        expected = item.get("expected_answer", "")
        keywords = item.get("keywords", [])

        # ✅ EMPTY ANSWER
        if not answer or not answer.strip():
            results.append({
                "question": item.get("question", ""),
                "score": 0.0,
                "matched_keywords": []
            })
            scores.append(0.0)
            continue

        emb1 = encode_text(answer)
        emb2 = encode_text(expected)

        similarity = cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0][0]

        similarity = max(similarity, 0.0)

        keyword_hits = [
            k for k in keywords
            if k.lower() in answer.lower()
        ]

        keyword_score = len(keyword_hits) / max(len(keywords), 1)

        final_score = float(0.7 * similarity + 0.3 * keyword_score)
        final_score = max(0.0, min(final_score, 1.0))

        scores.append(final_score)

        results.append({
            "question": item.get("question", ""),
            "score": round(final_score, 3),
            "matched_keywords": keyword_hits
        })

    overall_score = float(sum(scores) / len(scores)) if scores else 0.0

    return {
        "overall_interview_score": round(overall_score, 3),
        "question_scores": results
    }