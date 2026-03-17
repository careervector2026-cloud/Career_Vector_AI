# job_readiness_ml.py

import os
import joblib
import numpy as np

MODEL_PATH = "job_readiness_model.pkl"
_model = None


def _load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"ML model not found at {MODEL_PATH}"
            )
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_job_readiness_ml(breakdown: dict) -> float:
    model = _load_model()

    X = np.array([[
        breakdown["resume_jd"],
        breakdown["skill_coverage"],
        breakdown["experience"],
        breakdown["github"],
        breakdown["leetcode"]
    ]])

    prob = model.predict_proba(X)[0][1]
    return round(float(prob * 100), 2)
