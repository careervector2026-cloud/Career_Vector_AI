import csv
import os
from collections import Counter

FILE = "../logs/failure_analytics_log.csv"


def generate_failure_analytics(decision_filter: str = "ALL"):
    """
    decision_filter: ALL | REJECT | REVIEW
    Aggregates historical rejection/review patterns safely.
    """

    if not os.path.exists(FILE):
        return {"message": "No analytics data available"}

    primary_counter = Counter()
    secondary_counter = Counter()
    skill_counter = Counter()
    role_counter = Counter()
    policy_counter = Counter()

    total_records = 0

    with open(FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Skip malformed rows completely
            if not row:
                continue

            decision_stage = (row.get("decision_stage") or "").upper()

            # Apply filter
            if decision_filter != "ALL" and decision_stage != decision_filter:
                continue

            total_records += 1

            # Safe field extraction
            role_level = row.get("role_level") or "unknown"
            role_policy = row.get("role_policy") or "unknown"
            primary = row.get("primary_reasons") or ""
            secondary = row.get("secondary_reasons") or ""
            missing = row.get("missing_skills") or ""

            # Count role distributions
            role_counter[role_level] += 1
            policy_counter[role_policy] += 1

            # Count primary reasons
            for r in primary.split("|"):
                r = r.strip()
                if r:
                    primary_counter[r] += 1

            # Count secondary reasons
            for r in secondary.split("|"):
                r = r.strip()
                if r:
                    secondary_counter[r] += 1

            # Count missing skills
            for s in missing.split("|"):
                s = s.strip()
                if s:
                    skill_counter[s] += 1

    return {
        "decision_scope": decision_filter,
        "total_records": total_records,
        "top_primary_issues": primary_counter.most_common(5),
        "top_secondary_issues": secondary_counter.most_common(5),
        "most_common_missing_skills": skill_counter.most_common(5),
        "by_role_level": dict(role_counter),
        "by_evaluation_policy": dict(policy_counter)
    }