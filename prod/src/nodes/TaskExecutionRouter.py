from src.state.state import State, QueryTask
from typing import List
import logging
import json

logger = logging.getLogger()
def TaskExecutionRouter(state: State):
    logger.info("ENTERED Task Execution Router")
    logger.info(json.dumps(state, indent=2, default=str))
    query_tasks: List[QueryTask] = state["query_tasks"]

    statistical_pending = any(task.get("query_type") == "statistical" and task.get("status") == "pending" for task in query_tasks)

    if statistical_pending:
        return "Statistical Subtasks Pending Execution"

    semantic_pending = any(task.get("query_type") == "semantic" and task.get("status") == "pending" for task in query_tasks)

    if semantic_pending:
        return "Semantic Subtasks Pending Execution"
    
    return "No Subtasks Pending Execution"