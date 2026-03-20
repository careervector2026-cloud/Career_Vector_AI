#chatbot_intent_engine.py
from sentence_transformers import SentenceTransformer
import numpy as np
from functools import lru_cache

# -----------------------------------------
# MODEL LOADER (PREVENTS REPEATED LOAD)
# -----------------------------------------

@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


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

    # -------------------------------------------------
    # FAILURE DIAGNOSIS INTENT
    # -------------------------------------------------

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


# -----------------------------------------
# PRECOMPUTE INTENT EMBEDDINGS
# -----------------------------------------

intent_embeddings = {}

def initialize_intents():

    model = get_model()

    for intent, examples in INTENTS.items():

        emb = model.encode(examples)

        intent_embeddings[intent] = emb


initialize_intents()


# -----------------------------------------
# DETECT INTENT
# -----------------------------------------

def detect_intent_semantic(query):

    model = get_model()

    query_embedding = model.encode([query])[0]

    best_intent = None
    best_score = -1

    for intent, embeddings in intent_embeddings.items():

        scores = np.dot(embeddings, query_embedding)

        score = max(scores)

        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent