from src.state.state import State, Filters
from typing import List, Literal
import logging

logger = logging.getLogger(__name__)


def CompanyResolutionReview(state: State):
    logger.info("ENTERED Autonomous CompanyResolutionReview: %s", state)

    filter_groups: List[Filters] = state.get("filters", [])

    unresolved_filters = [
        group for group in filter_groups
        if group.get("company_validation") == "failed"
    ]

    resolved_filters = [
        group for group in filter_groups
        if group.get("company_validation") == "complete"
    ]

    unresolved_companies = [
        group.get("requested_company")
        for group in unresolved_filters
    ]

    resolved_companies = [
        {
            "requested_company": group.get("requested_company"),
            "resolved_company": group.get("company")
        }
        for group in resolved_filters
    ]

    def update_company_review(
        review_status: Literal["complete", "failed"],
        message: str | None,
        outer_status: Literal["running", "failed"] = "running"
    ):
        return {
            "company_review": {
                "status": review_status,
                "error_message": message
            },
            "status": outer_status,
            "error_message": None if outer_status == "running" else message
        }

    # 🛑 TOTAL FAILURE CHECK
    # If absolutely nothing resolved, fail the execution so AppendAIMessage can tell the user why
    if not resolved_companies:
        logger.info("Total failure: Zero companies resolved. Failing run.")
        return update_company_review(
            review_status="failed",
            outer_status="failed",
            message="None of the requested companies could be mapped to a valid legal entity."
        )

    # ✅ AUTOMATIC APPROVAL (SUCCESS OR MIXED SELECTIONS)
    # If we have at least one successfully resolved company, we automatically proceed.
    # We log a warning if some companies were skipped, but we do not interrupt the user.
    if unresolved_companies:
        logger.warning(
            "Proceeding automatically with partial execution. "
            "Skipped unresolved companies: %s", unresolved_companies
        )
    else:
        logger.info("All companies resolved perfectly. Proceeding automatically.")

    return {
        "filters": resolved_filters,  # Automatically pass only valid companies down the pipeline
        "company_review": {
            "status": "complete",
            "error_message": None
        },
        "status": "running",
        "error_message": None
    }
