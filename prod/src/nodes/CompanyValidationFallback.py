from src.state.state import State
from src.db.DatabaseManager import DatabaseManager
from src.state.state import Filters
from typing import List
from cfpb.complaints import CFPBComplaintReader
from datetime import datetime
import traceback
import logging

logger = logging.getLogger(__name__)


def CompanyValidationFallback(state: State, config: DatabaseManager):
    logger.info("ENTERED CompnayValidationFallback")
    filters: List[Filters] = [
        dict(group)
        for group in state.get("filters", [])
    ]

    failed_groups = [
        group for group in filters
        if group.get("company_validation") == "failed"
    ]

    for group in failed_groups:
        job_id = None

        try:
            date_ranges = group.get("date_received") or []

            if not date_ranges:
                group["executed_fallbacks"] = group.get("executed_fallbacks", 0) + 1
                continue

            min_start_date = date_ranges[0]["start_date"]
            max_end_date = date_ranges[0]["end_date"]
            fallback = group.get("executed_fallbacks", 0)

            for date_range in date_ranges:
                min_start_date = min(min_start_date, date_range["start_date"])
                max_end_date = max(max_end_date, date_range["end_date"])

            start_dt = datetime.strptime(min_start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(max_end_date, "%Y-%m-%d")
            middle_dt = start_dt + (end_dt - start_dt) / 2

            day_options = [
                {"start": start_dt, "end": start_dt},
                {"start": middle_dt, "end": middle_dt},
                {"start": end_dt, "end": end_dt},
            ]

            if fallback == 0:
                for option in day_options:
                    start_str = option["start"].strftime("%Y-%m-%d")
                    end_str = option["end"].strftime("%Y-%m-%d")

                    result = config.dml.insert_exploratory_job(
                        start_str,
                        end_str,
                        "days"
                    )

                    if not result:
                        continue

                    job_id = result[0]

                    config.dml.mark_job_running(
                        job_id,
                        "exploratory_jobs"
                    )

                    reader = CFPBComplaintReader([], start_str, end_str)
                    docs = reader.load_data()

                    companies = {
                        doc.metadata["company"]
                        for doc in docs
                        if doc.metadata.get("company")
                    }

                    rows = [
                        {"job_id": job_id, "company": company}
                        for company in companies
                    ]

                    if rows:
                        config.dml.insert_companies(rows)

                    config.dml.mark_job_completed(
                        job_id,
                        "exploratory_jobs"
                    )

                    job_id = None

            group["executed_fallbacks"] = group.get("executed_fallbacks", 0) + 1

        except Exception:
            error_message = traceback.format_exc()
            logger.error(error_message)

            config.conn.rollback()

            if job_id is not None:
                config.dml.mark_job_failed(
                    job_id,
                    "exploratory_jobs",
                    error_message
                )

            group["executed_fallbacks"] = group.get("executed_fallbacks", 0) + 1

    return {
        "filters": filters
    }