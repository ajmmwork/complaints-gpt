from src.state.state import State
import logging

logger = logging.getLogger(__name__)

def ExecutionRequirementRouter(state: State):
    logger.info("ENTERED Execution Requirement Router")
    jobs = state.get("ingestion_jobs", [])

    if jobs:
        return "Needs Ingestion"

    return "Does Not Need Ingestion"