from src.state.state import State, QueryTask
from src.db.DatabaseManager import DatabaseManager
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from llama_index.core import Document
from langchain_openai import ChatOpenAI
import logging
import json

logger = logging.getLogger(__name__)

judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _strip_json_fences(content: str) -> str:
    content = content.strip()

    if content.startswith("```json"):
        content = content[len("```json"):].strip()
    elif content.startswith("```"):
        content = content[len("```"):].strip()

    if content.endswith("```"):
        content = content[:-len("```")].strip()

    return content


def _judge_relevance(task_query: str, candidates: list[dict]) -> set[str]:
    if not candidates:
        return set()

    response = judge_llm.invoke(
        f"""
You are a relevance judge for a financial complaint retrieval system.

Your task is to decide which retrieved complaint narratives are relevant to the semantic task query.

Rules:
- Use ONLY the task query, complaint text, and complaint metadata.
- Keep a complaint only if it directly helps answer the task query.
- Drop complaints that are weakly related, generic, or off-topic.
- Do not keep a complaint just because it mentions the company.
- Do not keep a complaint just because it is from the correct date.
- Be strict but not overly narrow.
- If the task asks about a product or issue, use both the narrative text and metadata to judge relevance.
- If the metadata clearly contradicts the task topic and the narrative does not directly support the topic, mark it not relevant.
- If unsure, mark it not relevant.

Task query:
{task_query}

Retrieved candidates:
{json.dumps(candidates, indent=2, default=str)}

Return ONLY valid JSON in this format:
{{
  "relevant_complaint_ids": ["123", "456"]
}}
"""
    )

    try:
        parsed = json.loads(_strip_json_fences(response.content))
        ids = parsed.get("relevant_complaint_ids", [])

        if not isinstance(ids, list):
            return set()

        return {str(x) for x in ids}

    except Exception as exc:
        logger.error("Failed to parse relevance judge output: %s", exc)
        return set()


def RAGExecution(task: QueryTask, config: DatabaseManager):
    logger.info("ENTERED RAG Execution")

    copy_task: QueryTask = dict(task)

    try:
        docs: List[Document] = []
        seen_complaints = set()

        for filter_group in copy_task["filters"]:
            rows = config.dql.select_complaint_documents_by_filter_group(filter_group)

            for row in rows:
                complaint_id = str(row["complaint_id"])

                if complaint_id in seen_complaints:
                    continue

                metadata = {
                    key: value
                    for key, value in row.items()
                    if key not in {"narrative", "complaint_id"}
                }

                docs.append(
                    Document(
                        text=row["narrative"],
                        metadata=metadata,
                        doc_id=complaint_id
                    )
                )

                seen_complaints.add(complaint_id)

        if not docs:
            copy_task["data"] = []
            copy_task["status"] = "complete"
            copy_task["error_message"] = None
            return copy_task

        index = config.vector_db.build_ephemeral_complaint_index(docs)

        retriever = index.as_retriever(
            similarity_top_k=12,
            vector_store_query_mode="mmr",
            lambda_mult=0.7
        )

        nodes = retriever.retrieve(copy_task["query"])

        candidates = []

        for rank, node_with_score in enumerate(nodes, start=1):
            node = node_with_score.node
            metadata = node.metadata or {}

            candidates.append({
                "complaint_id": str(node.ref_doc_id),
                "rank": rank,
                "score": node_with_score.score,
                "text": node.get_content(),
                "metadata": metadata,
            })

        relevant_ids = _judge_relevance(
            task_query=copy_task["query"],
            candidates=[
                {
                    "complaint_id": candidate["complaint_id"],
                    "text": candidate["text"],
                    "metadata": candidate["metadata"],
                    "score": candidate["score"],
                }
                for candidate in candidates
            ]
        )

        filtered_context = []
        output_rank = 1

        for candidate in candidates:
            if candidate["complaint_id"] not in relevant_ids:
                continue

            filtered_context.append({
                "complaint_id": candidate["complaint_id"],
                "rank": output_rank,
                "score": candidate["score"],
                "text": candidate["text"],
                "metadata": candidate["metadata"],
            })

            output_rank += 1

        copy_task["error_message"] = None
        copy_task["status"] = "complete"
        copy_task["data"] = filtered_context

    except Exception as exc:
        logger.exception("RAGExecution failed")

        copy_task["error_message"] = str(exc)
        copy_task["status"] = "failed"
        copy_task["data"] = []

    return copy_task


def RAGSubTaskExecution(state: State, config: DatabaseManager):
    original_tasks: List[QueryTask] = state["query_tasks"]

    semantic_tasks: List[QueryTask] = [
        task
        for task in original_tasks
        if task.get("query_type") == "semantic"
        and task.get("status") == "pending"
    ]

    finished_tasks = []

    if semantic_tasks:
        max_workers = min(len(semantic_tasks), 8)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(RAGExecution, task, config)
                for task in semantic_tasks
            ]

            for future in as_completed(futures):
                finished_tasks.append(future.result())

    finished_by_id = {
        task["task_id"]: task
        for task in finished_tasks
    }

    updated_tasks = []

    for task in original_tasks:
        if task.get("query_type") == "statistical":
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