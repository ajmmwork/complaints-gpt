from langchain_core.messages import AIMessage
from src.state.state import State
import logging

logger = logging.getLogger(__name__)


def AppendAIMessage(state: State):
    logger.info("ENTERED AppendAIMessage")

    answer = state.get("answer")
    status = state.get("status")
    
    # 🌟 NEW RESILIENT ERROR LOOKUP:
    # Check top-level error_message first; fall back to nested company_review errors if empty
    error_message = state.get("error_message")
    if not error_message:
        company_review = state.get("company_review", {})
        error_message = company_review.get("error_message")

    if answer:
        content = answer
        final_status = "complete"
        final_error = None

    elif error_message:
        content = f"I couldn't complete the request.\n\nReason: {error_message}"
        final_status = "failed"
        final_error = error_message

    elif status == "failed":
        content = "I couldn't complete the request, but no specific error message was provided."
        final_status = "failed"
        final_error = "No error message provided."

    else:
        content = "The workflow completed but did not produce an answer."
        final_status = "failed"
        final_error = "No answer produced."

    return {
        "messages": [AIMessage(content=content)],
        "status": final_status,
        "error_message": final_error,

        # Clear execution artifacts after responding.
        # Chat history is preserved by the messages reducer in State.
        "answer": None,
        "filters": [],
        "company_review": {},
        "company_resolution": {},
        "ingestion_jobs": [],
        "query_tasks": [],
        "partial_semantic_answer": None,
        "partial_statistical_answer": None,
    }
