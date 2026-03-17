# placement_probability_logger.py


import os
from datetime import datetime

from pathlib import Path
import csv

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "logs" / "placement_probability_log.csv"
def log_placement_probability_sample(breakdown: dict, probability: float, status: str):

    file_exists = os.path.isfile(LOG_FILE)

    # ensure consistent ordering
    keys = list(breakdown.keys())

    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(
                ["timestamp"] + keys + ["probability", "status"]
            )

        writer.writerow(
            [datetime.utcnow().isoformat()]
            + [breakdown.get(k, 0) for k in keys]
            + [probability, status]
        )