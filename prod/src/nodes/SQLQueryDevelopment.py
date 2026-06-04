from src.state.state import State, QueryTask
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
import json
import logging

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)


def SQLQueryDevelopment(state: State):
    logger.info("ENTERED SQL Query Development")

    original_tasks: List[QueryTask] = state.get("query_tasks", [])

    sql_query_tasks: List[QueryTask] = [
        task for task in original_tasks
        if task.get("query_type") == "statistical"
        and task.get("status") in {"pending", "failed"}
    ]

    if not sql_query_tasks:
        return {
            "query_tasks": original_tasks,
            "status": "running",
            "error_message": None
        }

    response = llm.invoke(
        f"""
You are a PostgreSQL query generation engine for a financial complaints analytics system.

Generate one SQL query for each statistical query task.

Rules:
- Generate read-only analytical SQL.
- Do not invent tables or columns.
- Use only the provided schema.
- Use parameterized SQL only.
- Do not inline filter values directly into SQL.
- Use named parameters in psycopg style: %(parameter_name)s.
- Preserve the task meaning exactly.
- If a filter is null, do not add an exact filter condition for it.
- Only include GROUP BY, ORDER BY, LIMIT, aggregation, joins, or date bucketing when needed.
- Do not force a default grouping, ordering, or limit unless the task asks for it.
- Prefer simple, readable SQL.
- If previous error_message exists, correct the SQL based on that error.

Validated vs unvalidated issue/product rules:
- For validated string filters, use LOWER(column) = LOWER(%(param)s).
- A validated issue means task.filters contains a non-null issue.
- A validated product means task.filters contains a non-null product.
- If task.filters contains a non-null issue, use:
  LOWER(issue) = LOWER(%(issue)s)
- If task.filters contains a non-null product, use:
  LOWER(product) = LOWER(%(product)s)
- If task.filters issue/product is null, but the task query mentions a broad concept such as fraud, scam, fees, mortgage, credit reporting, wire transfer, dispute, unauthorized transaction, or identity theft, do NOT use equality with that raw concept.
- For unvalidated broad concepts extracted from the task query, use lowercase pattern matching:
  LOWER(issue) LIKE %(issue_pattern)s
  or LOWER(product) LIKE %(product_pattern)s
- Never generate LOWER(issue) = LOWER(%(issue)s) with params like {{"issue": "fraud"}} unless "fraud" came from task.filters.issue.
- Never generate LOWER(product) = LOWER(%(product)s) with raw user wording unless it came from task.filters.product.
- If the task asks for complaint IDs for an unvalidated broad issue concept, use LIKE pattern matching rather than exact equality.
- Example: if task.filters.issue is null and the query asks for fraud complaints, use LOWER(issue) LIKE %(issue_pattern)s with issue_pattern = "%fraud%".
- Example: if task.filters.issue is "Fraud or scam", use LOWER(issue) = LOWER(%(issue)s) with issue = "Fraud or scam".

Schema meaning:
- complaints.issue represents the complaint issue/topic/concern.
- complaints.product represents the financial product.
- complaints.company represents the legal company name.
- complaints.state represents the state.
- complaints.date_received represents when the complaint was received.
- complaints_narrative.narrative contains the complaint narrative text.

Available schema:

complaints:
- complaint_id
- job_id
- company
- issue
- product
- state
- date_received

complaints_narrative:
- complaint_id
- narrative

Trend and time-series rules:
- If the task asks for every month in a range, generate one row for every month in the range, even when complaint_count is zero.
- For monthly trends, use generate_series(start_month, end_month, interval '1 month') to create a complete month calendar.
- LEFT JOIN complaint counts onto the generated month calendar.
- Use COALESCE(count, 0) so missing months appear as zero.
- Month-over-month change must compare against the immediately previous generated month, not the previous month that happens to have complaints.
- Do not omit months just because no complaints exist for that month.
- For month ranges, prefer inclusive start and exclusive end:
  date_received >= %(start_date)s AND date_received < %(end_date)s.
- Avoid BETWEEN for month boundaries when the end date represents the next month start.

Ranked group comparison rules:
- If the task asks to identify top/bottom N products/issues in one period and track them across later periods, use a CTE to first identify the ranked group.
- Then CROSS JOIN the ranked group with the generated month calendar.
- Then LEFT JOIN monthly counts.
- Do not use dependent placeholders like top_5_products unless explicitly passed in parameters.
- Prefer one SQL query with CTEs for ranked-group trend comparisons.
- If the ranked group is based on worst performing products, rank by complaint_count DESC.
- If the ranked group is based on best/top performing products, rank by complaint_count ASC.

SQL safety rules:
- When combining AND and OR, always use explicit parentheses.
- Never rely on SQL operator precedence for mixed AND/OR logic.
- Use only SELECT queries.
- Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or MERGE.

Example for unvalidated broad issue concept:
SELECT complaint_id
FROM complaints
WHERE LOWER(company) = LOWER(%(company)s)
  AND LOWER(issue) LIKE %(issue_pattern)s
  AND date_received >= %(start_date)s
  AND date_received < %(end_date)s;

Example for validated issue filter:
SELECT complaint_id
FROM complaints
WHERE LOWER(company) = LOWER(%(company)s)
  AND LOWER(issue) = LOWER(%(issue)s)
  AND date_received >= %(start_date)s
  AND date_received < %(end_date)s;

Example for ranked monthly trend:
WITH top_products AS (
    SELECT product
    FROM complaints
    WHERE LOWER(company) = LOWER(%(company)s)
      AND date_received >= %(rank_start)s
      AND date_received < %(rank_end)s
    GROUP BY product
    ORDER BY COUNT(*) DESC
    LIMIT 5
),
months AS (
    SELECT generate_series(
        %(trend_start)s::date,
        %(trend_end)s::date,
        interval '1 month'
    )::date AS month
),
monthly_counts AS (
    SELECT
        product,
        DATE_TRUNC('month', date_received)::date AS month,
        COUNT(*) AS complaint_count
    FROM complaints
    WHERE LOWER(company) = LOWER(%(company)s)
      AND date_received >= %(trend_start)s
      AND date_received < %(trend_exclusive_end)s
      AND product IN (SELECT product FROM top_products)
    GROUP BY product, DATE_TRUNC('month', date_received)::date
),
dense_counts AS (
    SELECT
        tp.product,
        m.month,
        COALESCE(mc.complaint_count, 0) AS complaint_count
    FROM top_products tp
    CROSS JOIN months m
    LEFT JOIN monthly_counts mc
      ON mc.product = tp.product
     AND mc.month = m.month
)
SELECT
    product,
    month,
    complaint_count,
    complaint_count - LAG(complaint_count) OVER (
        PARTITION BY product
        ORDER BY month
    ) AS month_over_month_change
FROM dense_counts
ORDER BY product, month;

Tasks:
{json.dumps(sql_query_tasks, indent=2, default=str)}

Return ONLY valid JSON.

Output format:
[
  {{
    "task_id": "task_1",
    "sql": "SELECT issue, COUNT(*) AS complaint_count FROM complaints WHERE LOWER(company) = LOWER(%(company)s) AND date_received >= %(start_date)s AND date_received < %(end_date)s GROUP BY issue ORDER BY complaint_count DESC LIMIT 5;",
    "description": "Returns the top 5 complaint issues for the requested filters.",
    "parameters": {{
      "company": "BANK OF AMERICA, NATIONAL ASSOCIATION",
      "start_date": "2026-05-11",
      "end_date": "2026-05-18"
    }}
  }}
]
"""
    )

    output = response.content.strip()

    try:
        sql_scripts: List[Dict[str, Any]] = json.loads(output)
    except json.JSONDecodeError:
        return {
            "query_tasks": original_tasks,
            "status": "failed",
            "error_message": "Invalid JSON returned from SQL Query Development LLM.",
            "raw_output": output
        }

    if not isinstance(sql_scripts, list):
        return {
            "query_tasks": original_tasks,
            "status": "failed",
            "error_message": "SQL Query Development LLM must return a JSON array.",
            "raw_output": output
        }

    scripts_by_task_id = {
        script.get("task_id"): script
        for script in sql_scripts
        if isinstance(script, dict)
    }

    updated_tasks: List[QueryTask] = []

    for task in original_tasks:
        if (
            task.get("query_type") != "statistical"
            or task.get("status") not in {"pending", "failed"}
        ):
            updated_tasks.append(task)
            continue

        script = scripts_by_task_id.get(task.get("task_id"))

        if script is None:
            new_task: QueryTask = dict(task)
            new_task["status"] = "failed"
            new_task["error_message"] = (
                f"No SQL script returned for task_id {task.get('task_id')}."
            )
            updated_tasks.append(new_task)
            continue

        new_task: QueryTask = dict(task)
        new_task["sql"] = script.get("sql")
        new_task["desc"] = script.get("description")
        new_task["params"] = script.get("parameters", {})
        new_task["status"] = "running"
        new_task["error_message"] = None

        updated_tasks.append(new_task)

    return {
        "query_tasks": updated_tasks,
        "status": "running",
        "error_message": None
    }