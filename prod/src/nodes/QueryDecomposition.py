from src.state.state import State
from langchain_openai import ChatOpenAI
import json
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)


def _strip_json_fences(content: str) -> str:
    content = content.strip()

    if content.startswith("```json"):
        content = content[len("```json"):].strip()
    elif content.startswith("```"):
        content = content[len("```"):].strip()

    if content.endswith("```"):
        content = content[:-len("```")].strip()

    return content


def QueryDecomposition(state: State):
    logger.info("ENTERED QueryDecomposition")

    filters = [
        group for group in state.get("filters", [])
        if group.get("company_validation") == "complete"
        and group.get("company")
    ]

    if not filters:
        return {
            "query_tasks": [],
            "status": "failed",
            "error_message": (
                "No validated company filters are available for query decomposition."
            )
        }

    # Critical: freeze validated filters so the LLM cannot mutate them per task.
    validated_filters = deepcopy(filters)

    executable_companies = [
        group.get("company")
        for group in validated_filters
        if group.get("company")
    ]

    query = state.get("query")

    if not query:
        return {
            "query_tasks": [],
            "status": "failed",
            "error_message": "No query found for query decomposition."
        }

    response = llm.invoke(
        f"""
You are a query decomposition engine for a financial complaints analytics system.

Your job is to decompose a user query into independently executable query tasks.

Each task must:
- answer one focused executable unit of work
- be classified as either "statistical" or "semantic"
- NEVER be mixed
- be executable from the validated filters alone
- NOT depend on the output of another task through placeholder filter values

Definitions:

statistical:
- counting
- aggregation
- grouping
- filtering
- trend analysis
- comparisons
- averages
- percentages
- rankings such as top N / bottom N
- SQL-friendly operations over structured fields

semantic:
- reasoning over complaint narratives
- sentiment analysis
- summarization of narrative text
- explanation of why customers are upset
- intent analysis
- semantic retrieval from vector DB
- language understanding tasks that require reading narrative text

Scope rules:
- The original user query is analytical intent only.
- The validated filters are the executable scope.
- Only create tasks for companies present in the validated filters.
- Do not mention unresolved or excluded companies.
- Do not infer or re-add companies not present in validated filters.

Filter integrity rules:
- You must NOT create, edit, remove, infer, or override filters.
- Do NOT place filters in the JSON output.
- The system will attach validated filters after decomposition.
- If the validated scope contains issue = "Fraud or scam", every task will inherit that exact issue.
- If the validated scope contains product = null, every task will inherit product = null.
- Do not infer product from issue language.
- Fraud/scam is an issue concept, not a product.
- If a task needs semantic keyword search, keep the keyword in task.query, but do not alter filters.
- Do not create task-level filters.
- Do not include fields named filters, issue, product, company, state, or date_received in task output.

No dependent task placeholders:
- Do NOT create tasks that depend on another task's output using placeholder filter values.
- Do NOT use placeholders like:
  - top_5_products_from_task_1
  - products_from_previous_task
  - results_from_task_1
  - task_1_results
- Every task must be directly executable using only validated filters and original analytical intent.
- If ranking and trend comparison must be computed together, create ONE statistical task.

Complaint ranking interpretation:
- Complaints are negative events.
- "Most complaints", "highest complaint volume", "top complaints", "top complaint products",
  "top complaint issues", "most complained about", "worst performing", and
  "largest complaint categories" mean highest complaint_count.
- "Best performing", "top performing", "least problematic", "fewest complaints",
  "lowest complaint volume", and "lowest complaint rate" mean lowest complaint_count.
- Never assume higher complaint count means better performance.
- If the user says "top performing" in complaint data, interpret it as lowest complaint_count
  unless they explicitly define performance differently.
- If the user says "worst performing", interpret it as highest complaint_count.

Time comparison rules:
- If the user asks how something changed between periods, create one task covering all periods.
- Ask for counts for each period and absolute change.
- Ask for percent change only if the user asks for rate, percent, growth, decline, or percentage change.
- If the user asks for every month in a range, the task must request every month in the range.
- If the user asks for January and "the following month", the statistical task must cover January and February.
- The semantic narrative task should usually cover only the narrative period requested unless the user explicitly asks to summarize narratives for both periods.

Multi-requirement rules:
- Preserve all requested analytical requirements.
- If the user asks for metrics and narrative interpretation, create both statistical and semantic tasks.
- If the user only asks for top/bottom products, issues, or topics using structured fields, create statistical tasks only.
- Use semantic only when narrative/free-text interpretation is required.

Classification rules:
- "topics", "concerns", "issues", "areas of concern", and "complaint drivers" usually map to complaints.issue.
- Do NOT classify as semantic just because the user says "topic" or "concern".
- Use semantic for "why", "what are customers saying", "frustrations", "narratives",
  "sentiment", "feedback themes", or "summarize concerns".

Original query:
{query}

Validated executable filters that will be attached by the system:
{json.dumps(validated_filters, indent=2, default=str)}

Executable companies:
{json.dumps(executable_companies, indent=2)}

Return only valid JSON array.

Each object must contain only:
- task_id
- query
- query_type
- desc

Do not include filters or any filter-like fields.

Output format:
[
  {{
    "task_id": "task_1",
    "query": "Detailed execution unit query string text",
    "query_type": "statistical",
    "desc": "Short unit tracking label text"
  }}
]
"""
    )

    try:
        clean_content = _strip_json_fences(response.content)
        parsed_tasks = json.loads(clean_content)

        if not isinstance(parsed_tasks, list):
            raise ValueError("Query decomposition output was not a JSON array.")

        hydrated_tasks = []

        for task in parsed_tasks:
            if not isinstance(task, dict):
                raise ValueError("Each query task must be a JSON object.")

            clean_task = {
                "task_id": task.get("task_id"),
                "query": task.get("query"),
                "query_type": task.get("query_type"),
                "desc": task.get("desc"),
                "filters": deepcopy(validated_filters),
                "status": "pending",
                "data": {},
                "error_message": None,
                "sql": None,
                "params": {},
            }

            if clean_task["query_type"] not in {"statistical", "semantic"}:
                raise ValueError(
                    f"Invalid query_type for task {clean_task['task_id']}: "
                    f"{clean_task['query_type']}"
                )

            if not clean_task["task_id"] or not clean_task["query"]:
                raise ValueError("Each task must include task_id and query.")

            hydrated_tasks.append(clean_task)

        logger.info(
            "Successfully decomposed execution run into %s tasks.",
            len(hydrated_tasks)
        )

        return {
            "query_tasks": hydrated_tasks,
            "status": "running",
            "error_message": None
        }

    except Exception as exc:
        logger.error("Failed to parse decomposition JSON block: %s", exc)

        return {
            "query_tasks": [],
            "status": "failed",
            "error_message": (
                f"Query decomposition output formatting parsing error: {exc}"
            )
        }