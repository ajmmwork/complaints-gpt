from src.state.state import State
import logging

logger = logging.getLogger(__name__)

def FilterExtractionRouter(state: State):
    logger.info("ENTERED Filter Extraction Router")
    if state.get("status") == "running":
        return "Valid Query"

    return "Failed Query"