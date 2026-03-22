# answer_analyzer.py

from functools import lru_cache
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import asyncio

from analyzers.model_registry import get_embedding_model


# -------------------------------------------------
# GLOBAL MODEL CACHE
# -------------------------------------------------

_model = None


def get_model():
    global _model

    if _model is None:
        try:
            loop = asyncio.get_event_loop()

            if loop.is_running():
                # FastAPI loop running → fallback
                _model = asyncio.run(get_embedding_model())
            else:
                _model = asyncio.run(get_embedding_model())

        except RuntimeError:
            _model = asyncio.run(get_embedding_model())

    return _model


# -------------------------------------------------
# EMBEDDING CACHE
# -------------------------------------------------

@lru_cache(maxsize=512)
def encode_text(text: str):

    model = get_model()

    embedding = model.encode(text)

    return np.array(embedding).astype("float32")


# -------------------------------------------------
# INTERVIEW EVALUATION (SYNC)
# -------------------------------------------------

def evaluate_interview(answers):

    scores = []
    results = []

    for item in answers:

        answer = item.get("answer", "")
        expected = item.get("expected_answer", "")
        keywords = item.get("keywords", [])

        if not answer.strip():
            scores.append(0.0)
            results.append({
                "question": item.get("question", ""),
                "score": 0.0,
                "matched_keywords": []
            })
            continue

        emb1 = encode_text(answer)
        emb2 = encode_text(expected)

        similarity = cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0][0]

        keyword_hits = [
            k for k in keywords
            if k.lower() in answer.lower()
        ]

        keyword_score = len(keyword_hits) / max(len(keywords), 1)

        final_score = float((0.7 * similarity) + (0.3 * keyword_score))

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