
import os
from datetime import datetime

from pathlib import Path
import csv

BASE_DIR = Path(__file__).resolve().parent.parent
FILE = BASE_DIR / "logs" / "failure_analytics_log.csv"


def log_failure_analytics(
    *,
    decision_stage: str,
    role_level: str,
    role_policy: str,
    primary_reasons: list,
    secondary_reasons: list,
    missing_skills: list
):
    file_exists = os.path.exists(FILE)

    with open(FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "decision_stage",
                "role_level",
                "role_policy",
                "primary_reasons",
                "secondary_reasons",
                "missing_skills"
            ])

        writer.writerow([
            datetime.utcnow().isoformat(),
            decision_stage,
            role_level,
            role_policy,
            "|".join([r["reason"] for r in primary_reasons]),
            "|".join([r["reason"] for r in secondary_reasons]),
            "|".join(missing_skills)
        ])
