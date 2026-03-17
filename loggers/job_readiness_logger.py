# job_readiness_logger.py

import csv
import os

from pathlib import Path
import csv

BASE_DIR = Path(__file__).resolve().parent.parent
FILE = BASE_DIR / "logs" / "job_readiness_log.csv"
FIELDS = [
    "resume_jd",
    "skill_coverage",
    "experience",
    "github",
    "leetcode",
    "job_readiness",
    "status"
]


def log_job_readiness_sample(
    breakdown: dict,
    job_readiness: float,
    status: str
):
    exists = os.path.exists(FILE)

    with open(FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)

        if not exists:
            writer.writeheader()

        writer.writerow({
            "resume_jd": breakdown["resume_jd"],
            "skill_coverage": breakdown["skill_coverage"],
            "experience": breakdown["experience"],
            "github": breakdown["github"],
            "leetcode": breakdown["leetcode"],
            "job_readiness": job_readiness,
            "status": status
        })
