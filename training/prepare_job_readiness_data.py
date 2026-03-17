# prepare_job_readiness_data.py

import pandas as pd

df = pd.read_csv("../logs/job_readiness_log.csv")

filtered = df[
    ((df["status"] == "shortlist") & (df["job_readiness"] >= 75)) |
    ((df["status"] == "reject") & (df["job_readiness"] <= 45))
].copy()

filtered["label"] = filtered["status"].map({
    "shortlist": 1,
    "reject": 0
})

filtered = filtered.drop(columns=["status"])

filtered.to_csv("job_readiness_train.csv", index=False)

print("✅ Training data prepared")
print("Samples:", len(filtered))
