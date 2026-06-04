from src.state.state import State
import logging

logger = logging.getLogger(__name__)


def CompanyResolutionRouter(state: State):
    logger.info("ENTERED CompanyResolutionRouter")

    status = state.get("status")
    company_review = state.get("company_review", {})
    review_status = company_review.get("status")

    # 1. Pipeline automatically processed the mappings -> Proceed downstream to JobCreation
    if status == "running" and review_status == "complete":
        return "Approved"

    # 2. Total validation failure occurred -> Route to AppendAIMessage and explain why
    if status == "failed" or review_status == "failed":
        return "Failed"

    raise ValueError(
        f"Unknown routing state. "
        f"status={status}, review_status={review_status}"
    )
