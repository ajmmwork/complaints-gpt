from src.state.state import State, QueryTask
from src.db.DatabaseManager import DatabaseManager
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger()

def SQLExecution(task: QueryTask, config: DatabaseManager):
    logger.info("ENTERD SQL Execution")
    copy_task: QueryTask = dict(task)

    try:
        column_names, data = config.dql.execute_query(
            copy_task["sql"],
            params=copy_task["params"]
        )

        result = {
            column_name: list(column_values)
            for column_name, column_values in zip(column_names, zip(*data))
        } if data else {column_name: [] for column_name in column_names}

        copy_task["data"] = result
        copy_task["status"] = "complete"
        copy_task["error_message"] = None

    except Exception as exc:
        copy_task["status"] = "failed"
        copy_task["error_message"] = str(exc)

    return copy_task


def SQLSubTaskExecution(state: State, config: DatabaseManager):
    original_tasks: List[QueryTask] = state["query_tasks"]

    statistical_tasks: List[QueryTask] = [
        task for task in original_tasks
        if task.get("query_type") == "statistical"
        and task.get("status") == "pending"
    ]

    finished_tasks = []

    if statistical_tasks:
        max_workers = min(len(statistical_tasks), 8)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(SQLExecution, task, config)
                for task in statistical_tasks
            ]

            for future in as_completed(futures):
                finished_tasks.append(future.result())

    finished_by_id = {
        task["task_id"]: task
        for task in finished_tasks
    }

    updated_tasks = []

    for task in original_tasks:
        if task.get("query_type") == "semantic":
            updated_tasks.append(task)
        elif task["task_id"] in finished_by_id:
            updated_tasks.append(finished_by_id[task["task_id"]])
        else:
            updated_tasks.append(task)

    return {
        "query_tasks": updated_tasks,
        "status": "running",
        "error_message": None
    }