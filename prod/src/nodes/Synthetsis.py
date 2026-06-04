from src.state.state import State
from langchain_openai import ChatOpenAI
import logging
import json

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


def _extract_reference_ids_from_tasks(state: State) -> list[str]:
    reference_ids = []

    for task in state.get("query_tasks", []):
        data = task.get("data")

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("complaint_id"):
                    reference_ids.append(str(item["complaint_id"]))

        if isinstance(data, dict):
            ids = data.get("complaint_id")
            if isinstance(ids, list):
                reference_ids.extend(str(x) for x in ids if x is not None)

    seen = set()
    unique_ids = []

    for complaint_id in reference_ids:
        if complaint_id not in seen:
            seen.add(complaint_id)
            unique_ids.append(complaint_id)

    return unique_ids


def Synthesis(state: State):
    logger.info("ENTERED Synthesis")

    partial_semantic_answer = state.get("partial_semantic_answer")
    partial_statistical_answer = state.get("partial_statistical_answer")

    query = state.get("query", "")
    filters = state.get("filters", [])
    company_review = state.get("company_review", {})
    query_tasks = state.get("query_tasks", [])

    executable_companies = [
        group.get("company")
        for group in filters
        if group.get("company")
    ]

    reference_ids = _extract_reference_ids_from_tasks(state)

    context_sections = f"""
Original User Query:
{query}

Executable Companies:
{json.dumps(executable_companies, indent=2)}

Validated Executable Filters:
{json.dumps(filters, indent=2, default=str)}

Company Review:
{json.dumps(company_review, indent=2, default=str)}

Executed Query Tasks:
{json.dumps(query_tasks, indent=2, default=str)}

Reference Complaint IDs Extracted From Executed Tasks:
{json.dumps(reference_ids, indent=2)}
"""

    if partial_statistical_answer is not None:
        context_sections += f"""

Statistical Findings:
{partial_statistical_answer}
"""

    if partial_semantic_answer is not None:
        context_sections += f"""

Semantic Findings:
{partial_semantic_answer}
"""

    prompt = f"""
You are an analytical financial complaints intelligence assistant.

Your task is to answer the user's question using only the provided context.

Rules:
- Answer the user's question ONLY for the validated executable scope.
- Use ONLY the provided context.
- Do not invent statistics, trends, complaints, customer frustrations, complaint IDs, or missing data.
- Do not answer for companies absent from the validated executable filters.
- Do not imply unresolved companies were queried.
- Do not report findings for excluded or unresolved companies.
- Only discuss companies present in the validated executable filters.
- Do not mention semantic findings unless Semantic Findings are provided.
- Do not mention statistical findings unless Statistical Findings are provided.
- Preserve complaint IDs and references when they are present.
- If Reference Complaint IDs are provided, include a section titled "Reference Complaint IDs".
- If the user asks for references, complaint IDs, citations, or evidence, prioritize returning the complaint IDs clearly.
- If semantic findings cite complaint IDs, do not remove them in the final answer.
- If no complaint IDs are available in the provided context, say that no reference complaint IDs were available in the executed results.
- Prioritize concrete findings over generic observations.
- Keep the answer concise but information-dense.
- Use structured formatting with short sections and bullet points when appropriate.
- The original user query is analytical intent only.
- The validated executable filters define the actual execution scope.

Context:
{context_sections}

Generate the final answer.
"""

    resp = llm.invoke(prompt)

    return {
        "answer": resp.content.strip()
    }