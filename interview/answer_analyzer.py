from functools import lru_cache
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np

model = None


# -------------------------------------------------
# MODEL LOADING (SAFE + LAZY)
# -------------------------------------------------

def get_model():

    global model

    if model is None:
        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    return model


# -------------------------------------------------
# EMBEDDING CACHE
# Prevent recomputing same embeddings
# -------------------------------------------------

@lru_cache(maxsize=512)
def encode_text(text: str):

    model = get_model()

    embedding = model.encode(text)

    return np.array(embedding).astype("float32")


# -------------------------------------------------
# INTERVIEW EVALUATION
# -------------------------------------------------

def evaluate_interview(answers):

    scores = []
    results = []

    for item in answers:

        answer = item["answer"]
        expected = item["expected_answer"]
        keywords = item["keywords"]

        # cached embeddings
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
            "question": item["question"],
            "score": round(float(final_score), 3),
            "matched_keywords": keyword_hits
        })

    overall_score = float(sum(scores) / len(scores)) if scores else 0.0

    return {
        "overall_interview_score": round(overall_score, 3),
        "question_scores": results
    }