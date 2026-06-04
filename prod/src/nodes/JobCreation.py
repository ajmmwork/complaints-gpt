from src.state.state import State, IngestionJob
import logging
from typing import List

logger = logging.getLogger(__name__)


def JobCreation(state: State):
    logger.info("ENTERED Job Creation")

    groups = state.get("filters", [])

    jobs: List[IngestionJob]= []

    for group in groups:
        if group.get("company_validation") != "passed":
            continue

        date_ranges = group.get("date_received") or []

        for date_range in date_ranges:
            jobs.append(
                {
                    "company": group.get("company"),
                    "start_date": date_range["start_date"],
                    "end_date": date_range["end_date"],
                    "status": "pending",
                    "error_message": None,
                }
            )

    return {"ingestion_jobs": jobs}