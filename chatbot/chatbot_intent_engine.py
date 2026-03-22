# chatbot_intent_engine.py

import numpy as np
from analyzers.model_registry import get_embedding_model

# -----------------------------------------
# INTENTS
# -----------------------------------------

INTENTS = {
    "JOB_READINESS": [
        "am i job ready",
        "how ready am i",
        "job readiness score",
        "am i ready for this role",
        "do i qualify for this job",
        "am i eligible for this job"
    ],
    "SKILL_GAP": [
        "what skills am i missing",
        "skill gap",
        "skills required for job",
        "what should i learn",
        "what skills should i improve",
        "what should i study"
    ],
    "JOB_MATCH": [
        "which jobs match me",
        "find jobs for my resume",
        "what roles fit my profile",
        "which job suits my profile",
        "what roles can i apply for"
    ],
    "FAILURE_REASON": [
        "why was i rejected",
        "why did i fail",
        "why was my application rejected",
        "why didn't i get shortlisted",
        "why didn't i get selected",
        "why was i not selected",
        "why am i rejected",
        "what went wrong in my application",
        "why am i not eligible",
        "why did i fail the screening"
    ],
    "LEARNING_PATH": [
        "learning roadmap",
        "learning path",
        "how should i prepare",
        "how can i improve my skills",
        "how to prepare for this role"
    ],
    "INTERVIEW": [
        "give interview questions",
        "start interview practice",
        "test my interview skills",
        "generate interview questions",
        "mock interview"
    ],
    "CAREER_ADVICE": [
        "what role should i target",
        "which career path is best for me",
        "which job suits my profile",
        "what career should i choose",
        "what role fits my skills"
    ]
}

intent_embeddings = {}


# -----------------------------------------
# INITIALIZE INTENTS (CALLED AT STARTUP)
# -----------------------------------------

async def initialize_intents():

    model = await get_embedding_model()

    for intent, examples in INTENTS.items():
        intent_embeddings[intent] = model.encode(
            examples,
            normalize_embeddings=True
        )


# -----------------------------------------
# DETECT INTENT
# -----------------------------------------

async def detect_intent_semantic(query: str):

    model = await get_embedding_model()

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )[0]

    best_intent = None
    best_score = -1

    for intent, embeddings in intent_embeddings.items():

        scores = np.dot(embeddings, query_embedding)
        score = float(np.max(scores))

        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent