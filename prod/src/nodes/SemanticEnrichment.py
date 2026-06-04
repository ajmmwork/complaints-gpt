from src.state.state import State
from langchain_openai import ChatOpenAI
import json
import logging

logger = logging.getLogger(__name__)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _strip_json_fences(content: str) -> str:
    content = content.strip()

    if content.startswith("```json"):
        content = content[len("```json"):].strip()
    elif content.startswith("```"):
        content = content[len("```"):].strip()

    if content.endswith("```"):
        content = content[:-len("```")].strip()

    return content


def SemanticEnrichment(state: State):
    logger.info("ENTERED Semantic Enrichment")

    statistical_partial_answer = state.get("partial_statistical_answer")
    initial_query = state.get("query")
    query_tasks = state.get("query_tasks", [])

    semantic_tasks = [
        task for task in query_tasks
        if task.get("query_type") == "semantic"
        and task.get("status") == "pending"
    ]

    if not semantic_tasks:
        return {
            "query_tasks": query_tasks,
            "status": "running",
            "error_message": None
        }

    if not statistical_partial_answer:
        return {
            "query_tasks": query_tasks,
            "status": "running",
            "error_message": None
        }

    response = llm.invoke(
        f"""
You are a semantic enrichment node.

Your task is to improve semantic retrieval task queries using the SQL/statistical partial answer.

Rules:
- Do NOT create new tasks.
- Do NOT modify statistical tasks.
- Preserve task_id exactly.
- You may ONLY rewrite the semantic task query text.
- You must NOT create, edit, remove, infer, or override filters.
- Validated filters are immutable.
- Do NOT return filters.
- Do NOT return issue, product, company, state, date_received, or any filter-like fields.
- If SQL/statistical findings identify useful issue/product context, mention it in the rewritten query text only.
- If the original semantic query already has enough retrieval context, keep it mostly unchanged.
- Return ONLY valid JSON.

Original user query:
{initial_query}

SQL/statistical partial answer:
{statistical_partial_answer}

Pending semantic tasks:
{json.dumps(semantic_tasks, indent=2, default=str)}

Return ONLY this JSON structure:

{{
  "semantic_tasks": [
    {{
      "task_id": "...",
      "query": "..."
    }}
  ]
}}
"""
    )

    try:
        clean_content = _strip_json_fences(response.content)
        enriched_response = json.loads(clean_content)
        enriched_tasks = enriched_response.get("semantic_tasks", [])

        if not isinstance(enriched_tasks, list):
            raise ValueError("semantic_tasks must be a list.")

    except Exception as exc:
        logger.error("Failed to parse semantic enrichment JSON: %s", exc)

        return {
            "query_tasks": query_tasks,
            "status": "running",
            "error_message": str(exc)
        }

    enriched_by_id = {
        task.get("task_id"): task
        for task in enriched_tasks
        if isinstance(task, dict) and task.get("task_id")
    }

    updated_tasks = []

    for task in query_tasks:
        if task.get("query_type") != "semantic":
            updated_tasks.append(task)
            continue

        task_id = task.get("task_id")

        if task_id not in enriched_by_id:
            updated_tasks.append(task)
            continue

        enriched = enriched_by_id[task_id]

        updated_task = dict(task)
        updated_task["query"] = enriched.get("query", task.get("query"))

        # Critical: never allow SemanticEnrichment to mutate validated filters.
        updated_task["filters"] = task.get("filters", [])

        updated_tasks.append(updated_task)

    return {
        "query_tasks": updated_tasks,
        "status": "running",
        "error_message": None
    }