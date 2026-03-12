from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

model = None


def get_model():

    global model

    if model is None:
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    return model


def evaluate_interview(answers):

    model = get_model()

    scores = []
    results = []

    for item in answers:

        answer = item["answer"]
        expected = item["expected_answer"]
        keywords = item["keywords"]

        emb1 = model.encode(answer)
        emb2 = model.encode(expected)

        similarity = cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0][0]

        keyword_hits = [
            k for k in keywords if k.lower() in answer.lower()
        ]

        keyword_score = len(keyword_hits) / max(len(keywords), 1)

        final_score = (0.7 * similarity) + (0.3 * keyword_score)

        scores.append(final_score)

        results.append({
            "question": item["question"],
            "score": round(final_score, 3),
            "matched_keywords": keyword_hits
        })

    overall_score = sum(scores) / len(scores) if scores else 0

    return {
        "overall_interview_score": round(overall_score, 3),
        "question_scores": results
    }