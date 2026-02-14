# train_job_readiness_model.py

import pandas as pd
import joblib
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

df = pd.read_csv("job_readiness_train.csv")

X = df[
    ["resume_jd", "skill_coverage", "experience", "github", "leetcode"]
]
y = df["label"]

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression(
        class_weight="balanced",
        max_iter=1000
    ))
])

pipeline.fit(X, y)

joblib.dump(pipeline, "job_readiness_model.pkl")

print("✅ Job Readiness ML model trained")
