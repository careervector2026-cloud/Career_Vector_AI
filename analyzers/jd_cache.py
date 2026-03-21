#jd_cache.py
import numpy as np
from analyzers.model_registry import get_embedding_model

_jd_memory_cache = {}


async def get_jd_embedding_cached(jd_text: str):

    if jd_text in _jd_memory_cache:
        return _jd_memory_cache[jd_text]

    model = await get_embedding_model()

    embedding = model.encode(
        jd_text,
        normalize_embeddings=True
    )

    embedding = np.array(embedding).astype("float32")

    _jd_memory_cache[jd_text] = embedding

    return embedding