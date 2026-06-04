from src.state.state import State
import logging

logger = logging.getLogger(__name__)
def CompanyValidationFallbackRouter(state: State):
    logger.info("ENTERED CompanyValidationFallback")
    filters = state.get('filters', [])

    for filter in filters:
        company_validation = filter["company_validation"]
        fallback_count = filter["executed_fallbacks"]
        if company_validation == "failed":
            if fallback_count < 1:
                return "Company Validation Failed"
    
    return "Ready for Review"