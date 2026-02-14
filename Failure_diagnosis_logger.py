import csv
import os
from datetime import datetime

LOG_FILE = "failure_diagnosis_log.csv"

FIELDNAMES = [
    "timestamp",
    "decision",
    "role_level",
    "role_policy",
    "final_score",
    "threshold",
    "primary_reasons",
    "secondary_reasons",
    "missing_skills",
]


def log_failure_diagnosis(*, decision_data: dict):
    """
    Stable, schema-safe logger for failure diagnosis.
    """

    file_exists = os.path.isfile(LOG_FILE)

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "decision": decision_data.get("decision"),
        "role_level": decision_data.get("role_level"),
        "role_policy": decision_data.get("role_policy"),
        "final_score": decision_data.get("final_score"),
        "threshold": decision_data.get("threshold"),
        "primary_reasons": "|".join(
            r["reason"] for r in decision_data.get("primary_reasons", [])
        ),
        "secondary_reasons": "|".join(
            r["reason"] for r in decision_data.get("secondary_reasons", [])
        ),
        "missing_skills": "|".join(
            decision_data.get("missing_skills", [])
        ),
    }

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)
