# model_registry.py

import asyncio

_model = None
_lock = asyncio.Lock()

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


async def get_embedding_model():
    global _model

    if _model is None:
        async with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(
                    MODEL_NAME,
                    cache_folder="./hf_cache"
                )

    return _model


# ✅ ADD THIS (IMPORTANT)
def get_model_sync():
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)

    return _model