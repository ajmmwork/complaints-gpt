from src.state.state import State
from datetime import datetime, timedelta

import logging

logger = logging.getLogger(__name__)
def parse_date(value):
    if hasattr(value, "isoformat"):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_date(value):
    return value.isoformat()


def merge_ranges(jobs):
    if not jobs:
        return []

    sorted_jobs = sorted(
        jobs,
        key=lambda job: (job["company"], parse_date(job["start_date"]))
    )

    merged = []

    for job in sorted_jobs:
        company = job["company"]
        start = parse_date(job["start_date"])
        end = parse_date(job["end_date"])

        if not merged:
            merged.append({
                **job,
                "start_date": start,
                "end_date": end,
            })
            continue

        last = merged[-1]

        if (
            company == last["company"]
            and start <= last["end_date"] + timedelta(days=1)
        ):
            last["end_date"] = max(last["end_date"], end)
        else:
            merged.append({
                **job,
                "start_date": start,
                "end_date": end,
            })

    return merged


def JobConsolidation(state: State):
    logger.info("ENTERED Job Consolidation")
    jobs = state.get("ingestion_jobs", [])


    consolidated_jobs = merge_ranges(jobs)

    for job in consolidated_jobs:
        job["start_date"] = format_date(job["start_date"])
        job["end_date"] = format_date(job["end_date"])

    return {"ingestion_jobs": consolidated_jobs}