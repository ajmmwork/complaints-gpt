from src.state.state import State
from src.db.DatabaseManager import DatabaseManager
import logging
import json

logger = logging.getLogger(__name__)


def DataCoverage(state: State, config: DatabaseManager):
    logger.info("ENTERED Data Coverage")
    

    candidate_jobs = state.get("ingestion_jobs", [])
    final_jobs = []

    for job in candidate_jobs:
        start_date = job["start_date"]
        end_date = job["end_date"]
        company = job["company"]

        required_jobs = config.dql.extract_required_data_coverage_jobs(
            company,
            start_date,
            end_date
        )

        if required_jobs:
            final_jobs.extend(
                [
                    {
                        "company": j[0],
                        "start_date": str(j[1]),
                        "end_date": str(j[2]),
                        "status": "pending",
                        "error_message": None,
                    }
                    for j in required_jobs
                ]
            )

    return {"ingestion_jobs": final_jobs}