from src.state.state import State, QueryTask
from typing import List
import logging

logger = logging.getLogger(__name__)


def SQLQueryValidationRouter(state: State):
    logger.info("ENTERED SQL Query Validation Router")

    if state.get("status") == "failed":
        return "SQL Generation Failed"

    query_tasks: List[QueryTask] = state.get("query_tasks", [])

    has_invalid_sql = any(
        task.get("query_type") == "statistical"
        and task.get("status") == "failed"
        for task in query_tasks
    )

    if has_invalid_sql:
        return "Invalid SQL script(s)"

    return "Validated SQL scripts"