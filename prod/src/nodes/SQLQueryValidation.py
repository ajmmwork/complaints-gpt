from sqlglot import parse, exp
from src.state.state import State, QueryTask
from typing import List
import logging
import json

logger = logging.getLogger(__name__)


def SQLQueryValidation(state: State):
    logger.info("ENTERED SQL Query Validation")
    logger.info(json.dumps(state, indent=2, default=str))

    all_tasks: List[QueryTask] = state.get("query_tasks", [])
    validated_tasks: List[QueryTask] = []

    unauthorized_types = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.TruncateTable,
        exp.Create,
        exp.Alter,
        exp.Command,
    )

    for task in all_tasks:
        copy_task: QueryTask = dict(task)

        if copy_task.get("query_type") != "statistical":
            validated_tasks.append(copy_task)
            continue

        if copy_task.get("status") not in {"running", "failed"}:
            validated_tasks.append(copy_task)
            continue

        sql = copy_task.get("sql")

        if not sql:
            copy_task["error_message"] = "No SQL code was generated for this task."
            copy_task["status"] = "failed"
            validated_tasks.append(copy_task)
            continue

        try:
            parsed_statements = parse(sql, dialect="postgres")
        except Exception as exc:
            copy_task["error_message"] = f"SQL parsing failed: {exc}"
            copy_task["status"] = "failed"
            validated_tasks.append(copy_task)
            continue

        if len(parsed_statements) != 1:
            copy_task["error_message"] = "Only one SQL statement is allowed per task."
            copy_task["status"] = "failed"
            validated_tasks.append(copy_task)
            continue

        statement = parsed_statements[0]

        logger.info("SQL ROOT TYPE: %s", type(statement).__name__)

        if statement.find(unauthorized_types) is not None:
            copy_task["error_message"] = "Unauthorized DML, DDL, or command statement found."
            copy_task["status"] = "failed"
            validated_tasks.append(copy_task)
            continue

        copy_task["status"] = "pending"
        copy_task["error_message"] = None
        validated_tasks.append(copy_task)

    return {
        "query_tasks": validated_tasks,
        "status": state.get("status", "running"),
        "error_message": state.get("error_message")
    }