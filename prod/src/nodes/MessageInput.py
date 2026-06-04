from src.state.state import State
from langchain_openai import ChatOpenAI
import logging
import json

logger = logging.getLogger(__name__)
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)


def message_content(message):
    if isinstance(message, dict):
        return message.get("content", "")

    if hasattr(message, "content"):
        return message.content

    return str(message)


def message_type(message):
    if isinstance(message, dict):
        return message.get("type") or message.get("role") or "unknown"

    return getattr(message, "type", "unknown")


def MessageInput(state: State):
    logger.info("ENTERED MessageInput")

    messages = state.get("messages", [])

    if not messages:
        return {
            "status": "failed",
            "error_message": "No user message was provided."
        }

    current_query = message_content(messages[-1])

    if not current_query:
        return {
            "status": "failed",
            "error_message": "Could not extract latest user message."
        }

    recent_messages = [
        {
            "type": message_type(message),
            "content": message_content(message)
        }
        for message in messages[-10:]
    ]

    if len(recent_messages) <= 1:
        return {
            "query": current_query,
            "status": "pending",
            "error_message": None
        }

    response = llm.invoke(
        f"""
You are a query rewriting node for a financial complaints analytics system.

Your task:
Return the best standalone version of the latest user query.

Rules:
- If the latest user query is already standalone, return it unchanged.
- If the latest user query depends on prior messages, rewrite it into a complete standalone analytics query.
- Use prior messages only to fill missing context such as company, date range, metric, product, issue, state, comparison period, or analysis type.
- Preserve the latest user's requested change.
- Do not answer the query.
- Do not invent facts.
- Do not add filters that are not supported by the conversation.
- Do not include explanations.
- Return ONLY valid JSON.

Examples:

Conversation:
User: Top complaint issue for BofA jan 2020
Assistant: Managing an account, 56 complaints
User: what about wells fargo

Output:
{{
  "query": "Top complaint issue for Wells Fargo in January 2020"
}}

Conversation:
User: Top 5 complaint products for BofA in May 2024
Assistant: Checking or savings account was highest
User: what about June

Output:
{{
  "query": "Top 5 complaint products for BofA in June 2024"
}}

Conversation:
User: Top 5 complaint products for Citi in March 2024

Output:
{{
  "query": "Top 5 complaint products for Citi in March 2024"
}}

Recent conversation messages:
{json.dumps(recent_messages, indent=2)}

Latest user query:
{current_query}

Return ONLY:
{{
  "query": "standalone query here"
}}
"""
    )

    try:
        parsed = json.loads(response.content)
        resolved_query = parsed.get("query", current_query)
    except Exception as exc:
        logger.warning("Query rewrite failed: %s", exc)
        resolved_query = current_query

    return {
        "query": resolved_query,
        "status": "pending",
        "error_message": None
    }