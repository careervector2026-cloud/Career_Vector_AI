import csv
import os
from collections import Counter

FILE = "failure_analytics_log.csv"


def generate_failure_analytics(decision_filter: str = "ALL"):
    """
    decision_filter: ALL | REJECT | REVIEW
    """

    if not os.path.exists(FILE):
        return {"message": "No analytics data available"}

    primary_counter = Counter()
    secondary_counter = Counter()
    skill_counter = Counter()
    role_counter = Counter()
    policy_counter = Counter()

    with open(FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if decision_filter != "ALL" and row["decision_stage"].upper() != decision_filter:
                continue

            role_counter[row["role_level"]] += 1
            policy_counter[row["role_policy"]] += 1

            for r in row["primary_reasons"].split("|"):
                if r:
                    primary_counter[r] += 1

            for r in row["secondary_reasons"].split("|"):
                if r:
                    secondary_counter[r] += 1

            for s in row["missing_skills"].split("|"):
                if s:
                    skill_counter[s] += 1

    return {
        "decision_scope": decision_filter,
        "total_records": sum(role_counter.values()),
        "top_primary_issues": primary_counter.most_common(5),
        "top_secondary_issues": secondary_counter.most_common(5),
        "most_common_missing_skills": skill_counter.most_common(5),
        "by_role_level": dict(role_counter),
        "by_evaluation_policy": dict(policy_counter)
    }
