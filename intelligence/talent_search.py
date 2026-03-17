import numpy as np
from functools import lru_cache

from analyzers.matcher import get_model
from analyzers.resume_parser import parse_resume_from_url

try:
    import faiss
    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False


# -------------------------------------------------
# RESUME EMBEDDING CACHE
# -------------------------------------------------

@lru_cache(maxsize=2048)
def get_resume_embedding_cached(resume_url):

    model = get_model()

    resume_text = parse_resume_from_url(resume_url)

    emb = model.encode(resume_text)

    return np.array(emb).astype("float32")


# -------------------------------------------------
# TALENT SEARCH
# -------------------------------------------------

async def search_talent_pool(query, candidates, top_k=10):

    model = get_model()

    query_embedding = model.encode(query)
    query_embedding = np.array(query_embedding).astype("float32")

    candidate_embeddings = []
    candidate_ids = []

    for c in candidates:

        cid = c.get("candidate_id")
        resume_url = c.get("resume_url")

        emb = get_resume_embedding_cached(resume_url)

        candidate_embeddings.append(emb)
        candidate_ids.append(cid)

    candidate_embeddings = np.array(candidate_embeddings).astype("float32")

    # -------------------------------------------------
    # FAISS SEARCH
    # -------------------------------------------------

    if FAISS_AVAILABLE:

        dim = candidate_embeddings.shape[1]

        index = faiss.IndexFlatIP(dim)

        index.add(candidate_embeddings)

        scores, indices = index.search(
            query_embedding.reshape(1, -1),
            min(top_k, len(candidate_embeddings))
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):

            results.append({
                "candidate_id": candidate_ids[idx],
                "similarity_score": float(score)
            })

        return results

    # -------------------------------------------------
    # COSINE FALLBACK
    # -------------------------------------------------

    from sklearn.metrics.pairwise import cosine_similarity

    sims = cosine_similarity(
        query_embedding.reshape(1, -1),
        candidate_embeddings
    )[0]

    ranked = sorted(
        zip(candidate_ids, sims),
        key=lambda x: x[1],
        reverse=True
    )

    return [
        {"candidate_id": cid, "similarity_score": float(score)}
        for cid, score in ranked[:top_k]
    ]