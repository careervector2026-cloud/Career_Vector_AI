#answer_analyzer.py
from functools import lru_cache
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import asyncio

from analyzers.model_registry import get_embedding_model


_model = None

def get_model():
    global _model

    if _model is None:
        _model = asyncio.run(get_embedding_model())

    return _model


@lru_cache(maxsize=512)
def encode_text(text: str):

    model = get_model()

    embedding = model.encode(text, normalize_embeddings=True)

    return np.array(embedding).astype("float32")


def evaluate_interview(answers):

    scores = []
    results = []

    for item in answers:

        emb1 = encode_text(item["answer"])
        emb2 = encode_text(item["expected_answer"])

        similarity = cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0][0]

        keywords = item["keywords"]

        keyword_hits = [
            k for k in keywords
            if k.lower() in item["answer"].lower()
        ]

        keyword_score = len(keyword_hits) / max(len(keywords), 1)

        final_score = float(0.7 * similarity + 0.3 * keyword_score)

        scores.append(final_score)

        results.append({
            "question": item["question"],
            "score": round(final_score, 3),
            "matched_keywords": keyword_hits
        })

    overall_score = float(sum(scores) / len(scores)) if scores else 0.0

    return {
        "overall_interview_score": round(overall_score, 3),
        "question_scores": results
    }