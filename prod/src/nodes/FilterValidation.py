# src/nodes/FilterValidation.py

from difflib import SequenceMatcher
from typing import Optional
import logging

from src.state.state import State
from src.db.DatabaseManager import DatabaseManager

logger = logging.getLogger(__name__)


FILTER_CONFIG = {
    "issue": {
        "table": "issues",
        "column": "issue",
        "threshold": 0.75,
    },
    "product": {
        "table": "products",
        "column": "product",
        "threshold": 0.65,
    },
}


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _get_valid_values(
    mgr: DatabaseManager,
    table: str,
    column: str,
) -> list[str]:
    values = mgr.dql.select_all_from_column(column, table)
    return [v for v in values if v is not None]


def _find_exact_match(
    valid_values: list[str],
    value: str,
) -> Optional[str]:
    target = _normalize(value)

    for valid_value in valid_values:
        if _normalize(valid_value) == target:
            return valid_value

    return None


def _find_contains_match(
    valid_values: list[str],
    value: str,
) -> tuple[Optional[str], float]:
    target = _normalize(value)
    candidates = []

    for valid_value in valid_values:
        normalized_valid = _normalize(valid_value)

        if target in normalized_valid or normalized_valid in target:
            score = _similarity(value, valid_value)
            candidates.append((valid_value, score))

    if not candidates:
        return None, 0.0

    return max(candidates, key=lambda item: item[1])


def _extract_best_rag_match(
    requested_value: str,
    valid_values: list[str],
    retrieved_text: str,
) -> tuple[Optional[str], float]:
    retrieved_lower = retrieved_text.lower()
    candidates = []

    for valid_value in valid_values:
        if valid_value.lower() in retrieved_lower:
            score = _similarity(requested_value, valid_value)
            candidates.append((valid_value, score))

    if not candidates:
        return None, 0.0

    return max(candidates, key=lambda item: item[1])


def _find_closest_match_with_rag(
    mgr: DatabaseManager,
    column: str,
    value: str,
    valid_values: list[str],
) -> tuple[Optional[str], float]:
    index = mgr.vector_db.get_filter_index()
    retriever = index.as_retriever(similarity_top_k=5)

    query = (
        f"Find the closest valid CFPB {column} filter value "
        f"for this user-provided value: {value}"
    )

    retrieved_nodes = retriever.retrieve(query)

    retrieved_text = "\n".join(
        node.get_content() for node in retrieved_nodes
    )

    return _extract_best_rag_match(
        requested_value=value,
        valid_values=valid_values,
        retrieved_text=retrieved_text,
    )


def _validate_filter_value(
    mgr: DatabaseManager,
    field: str,
    value: Optional[str],
) -> Optional[str]:
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    config = FILTER_CONFIG[field]
    table = config["table"]
    column = config["column"]
    threshold = config["threshold"]

    valid_values = _get_valid_values(
        mgr=mgr,
        table=table,
        column=column,
    )

    exact_match = _find_exact_match(
        valid_values=valid_values,
        value=value,
    )

    if exact_match:
        logger.info(
            "Validated %s by exact match: %s -> %s",
            field,
            value,
            exact_match,
        )
        return exact_match

    contains_match, contains_score = _find_contains_match(
        valid_values=valid_values,
        value=value,
    )

    if contains_match and contains_score >= threshold:
        logger.info(
            "Validated %s by contains match: %s -> %s score=%s",
            field,
            value,
            contains_match,
            contains_score,
        )
        return contains_match

    rag_match, rag_score = _find_closest_match_with_rag(
        mgr=mgr,
        column=column,
        value=value,
        valid_values=valid_values,
    )

    if rag_match and rag_score >= threshold:
        logger.info(
            "Validated %s by RAG match: %s -> %s score=%s",
            field,
            value,
            rag_match,
            rag_score,
        )
        return rag_match

    logger.info(
        "Dropped unresolved %s filter: requested=%s closest=%s score=%s threshold=%s",
        field,
        value,
        rag_match,
        rag_score,
        threshold,
    )

    return None


def FilterValidation(state: State, mgr: DatabaseManager):
    logger.info("ENTERED FilterValidation")

    filters = state.get("filters", [])
    updated_filters = []

    for filter_group in filters:
        updated_filter = dict(filter_group)

        for field in ["issue", "product"]:
            resolved_value = _validate_filter_value(
                mgr=mgr,
                field=field,
                value=updated_filter.get(field),
            )

            updated_filter[field] = resolved_value

        updated_filters.append(updated_filter)

    return {
        "filters": updated_filters,
        "status": "complete",
        "error_message": None,
    }