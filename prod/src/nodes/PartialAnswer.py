from openai import OpenAI
from src.state.state import State, QueryTask
from typing import List
import json
from langchain_openai import ChatOpenAI
import logging

logger = logging.getLogger(__name__)
client = OpenAI()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)

INSTRUCTIONS = """
                    You are a statistical results interpreter.

                    You receive:
                    - The user's original query
                    - Executed statistical tasks
                    - Structured data returned from SQL execution

                    Rules:

                    1. Use only the provided task data.
                    2. Never invent calculations, trends, metrics, or findings.
                    3. If a task failed, explain the failure using the provided error_message.
                    4. Preserve the granularity of the returned data.
                    5. Do not aggregate, average, summarize, rank, or collapse results unless explicitly requested by the user.
                    6. If SQL returns grouped results, preserve those groups in the answer.
                    7. If SQL returns multiple rows, represent multiple rows in the answer.
                    8. If SQL returns a single value, represent the single value.
                    9. If additional calculations are required to answer the user's question, perform only those calculations using the provided data.
                    10. Do not discard returned columns.
                    11. Every output value must be traceable to the provided data.
                    12. Prefer structured answers over narrative summaries.
                    13. The goal is faithful representation of the statistical results, not interpretation.

                    Output Requirements:

                    - Answer the user's question directly.
                    - Preserve all meaningful dimensions returned by the data.
                    - Preserve relationships between columns.
                    - When data contains multiple records, present multiple records.
                    - When data contains grouped metrics, present grouped metrics.
                    - When data contains rankings, preserve rankings.
                    - When data contains time series, preserve the time dimension.
                """

def PartialSemanticAnswer(state: State):
    logger.info("ENTERED Partial Semantic Answer")
    semantic_tasks: List[QueryTask] = [
        task
        for task in state["query_tasks"]
        if task["status"] == "complete"
        and task["query_type"] == "semantic"
    ]

    semantic_answer = None
    if semantic_tasks:
        

        semantic_payload = [
            {
                "query": task["query"],
                "context": task["data"]
            }
            for task in semantic_tasks
        ]

        response = llm.invoke(
            f"""
                Provide a rich, detailed, assumption-free response
                to the following semantic queries using ONLY the provided context.

                Context:
                {json.dumps(semantic_payload, default=str, indent=2)}

                Make sure to include a reference section with the complaint id of every single complaint you used in your repsonse
            """
        )

        semantic_answer = response.content

    return {
        "partial_semantic_answer": semantic_answer,
        "status": "running",
        "error_message": None
    }

def PartialStatisticalAnswer(state: State):
    logger.info("ENTERED Partial Statistical Answer")
    logger.info(json.dumps(state, indent=2, default=str))

    statistical_tasks: List[QueryTask] = [
        task
        for task in state["query_tasks"]
        if task["status"] == "complete"
        and task["query_type"] == "statistical"
    ]

    statistical_answer = None

    if statistical_tasks:

        payload = {
            "original_query": state.get("query"),
            "statistical_tasks": statistical_tasks
        }

        resp = client.responses.create(
            model="gpt-4.1-mini",
            tools=[
                {
                    "type": "code_interpreter",
                    "container": {
                        "type": "auto",
                        "memory_limit": "1g"
                    }
                }
            ],
            instructions=INSTRUCTIONS,
            input=[
                {
                    "role": "user",
                    "content": json.dumps(payload, default=str)
                }
            ]
        )

        statistical_answer = resp.output_text

    return {
        "partial_statistical_answer": statistical_answer,
        "status": "running",
        "error_message": None
    }

    