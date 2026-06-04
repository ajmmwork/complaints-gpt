from langchain_openai import ChatOpenAI
from src.state.state import State
from dotenv import load_dotenv
import json
import logging
from datetime import datetime, date

load_dotenv()

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)


GENERIC_FILTER_TERMS = {
    "complaint",
    "complaints",
    "issue",
    "issues",
    "complaint issue",
    "complaint issues",
    "top issue",
    "most frequent issue",
    "frequent issue",
    "volume",
    "count",
    "counts",
    "average",
    "standard deviation",
    "standard deviations",
    "stddev",
    "std dev",
    "z score",
    "z-score",
}


def _clean_generic_filter_value(value):
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    cleaned = value.strip()

    if cleaned.lower() in GENERIC_FILTER_TERMS:
        return None

    return cleaned


def _validate_and_normalize_filters(filters: list[dict]) -> list[dict]:
    if not isinstance(filters, list):
        raise TypeError("Filters must be a list")

    normalized_filters = []

    for filter_obj in filters:
        if not isinstance(filter_obj, dict):
            raise TypeError("Each filter must be a JSON object")

        normalized = {
            "requested_company": filter_obj.get("requested_company"),
            "company": "",
            "issue": _clean_generic_filter_value(filter_obj.get("issue")),
            "product": _clean_generic_filter_value(filter_obj.get("product")),
            "state": filter_obj.get("state"),
            "date_received": None,
            "executed_fallbacks": 0,
            "company_validation": None,
        }

        date_ranges = filter_obj.get("date_received")

        if date_ranges is not None:
            if not isinstance(date_ranges, list):
                raise TypeError("date_received must be a list of objects or null")

            normalized_date_ranges = []

            for date_range in date_ranges:
                if not isinstance(date_range, dict):
                    raise TypeError("Each date_received item must be an object")

                if "start_date" not in date_range or "end_date" not in date_range:
                    raise ValueError(
                        "Each date range must include start_date and end_date"
                    )

                start = datetime.strptime(
                    date_range["start_date"],
                    "%Y-%m-%d"
                ).date()

                end = datetime.strptime(
                    date_range["end_date"],
                    "%Y-%m-%d"
                ).date()

                if start > end:
                    raise ValueError(
                        "date_received start date cannot be after end date"
                    )

                normalized_date_ranges.append(
                    {
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                    }
                )

            normalized["date_received"] = normalized_date_ranges

        normalized_filters.append(normalized)

    return normalized_filters


def FilterExtraction(state: State):
    logger.info("ENTERED Filter Extraction")

    query = state["query"]
    today = date.today().isoformat()

    response = llm.invoke(
        f"""
            You are a filter extraction system.

            Today's date is {today}.

            Extract filters from the user query.

            Return ONLY valid JSON.
            Do not include explanations.
            Do not include markdown.

            Return a JSON array of filter objects.

            Each filter object represents one logical search/request unit from the user.

            Extract ONLY these fields:
            - requested_company
            - issue
            - product
            - state
            - date_received

            Rules:
            - requested_company: extract the company name mentioned by the user.
            - issue: extract a specific complaint issue/topic ONLY if the user names an actual issue.
            - product: extract a specific financial product ONLY if the user names an actual product.
            - state: extract US state abbreviations. If full name is present convert to capitalized abbreviation.
            - date_received: extract dates, date ranges, and relative time expressions.

            If a non-date and non-company field is not present, use null.

            Important negative rules:
            - Do NOT treat generic analytical words as issue or product filters.
            - Generic words include: complaints, complaint, issue, issues, volume, count, average, standard deviation, standard deviations, most frequent issue, top issue.
            - If the user asks for the most frequent issue, issue must be null because the issue is unknown and must be discovered by SQL.
            - If the user asks for average across all issues, issue must be null.
            - If the user asks for standard deviations across all issues, issue must be null.
            - Only populate issue when the user names a specific issue, such as "Improper use of your report" or "Managing an account".
            - Only populate product when the user names a specific product, such as "Mortgage" or "Credit reporting or other personal consumer reports".

            Date rules:
            - If the user mentions any time period, date_received MUST NOT be null.
            - Always resolve relative dates using Today's date: {today}.
            - Only use null for date_received if the user gives no time reference at all.

            Relative date rules:
            - If the user says "today", use today's date as both start_date and end_date.
            - If the user says "yesterday", use yesterday as both start_date and end_date.
            - If the user says "last month", use the previous full calendar month.
            - If the user says "this month", use the first day of the current month through today's date.
            - If the user says "last week", use the previous full Monday-Sunday week.
            - If the user says "this week", use Monday of the current week through today's date.
            - If the user says "past 7 days" or "last 7 days", use the 7-day range ending today.
            - If the user says "past 30 days" or "last 30 days", use the 30-day range ending today.

            Absolute date rules:
            - If the user gives a specific date, return that day as both start_date and end_date.
            - If the user gives a month and year, return the full month range.
            - If the user gives only a year, return the full year range.

            date_received must be either:
            - null
            - or a list of date range objects:
            [
            {{
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD"
            }}
            ]

            Grouping rules:
            - If the user mentions one company with one product/date/issue/state,
            return one filter object.
            - If the user mentions multiple companies with different products,
            return one object per company/product pair.
            - If multiple companies share the same product/date/issue/state,
            return one object per company.
            - If the same date applies to multiple companies,
            repeat that date in each object.
            - If no company is mentioned, requested_company must be null.
            - Do not overmap simple words like "complaints" to issue or product.
            - If you are unsure about issue/product/state/company, use null.

            Output exactly as a JSON array in this format:

            [
            {{
                "requested_company": null,
                "issue": null,
                "product": null,
                "state": null,
                "date_received": null
            }}
            ]

            User query:
            {query}
        """
    )

    raw_text = response.content.strip()

    try:
        filters = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM JSON output")
        logger.error(raw_text)
        return {
            "filters": [],
            "status": "failed",
            "error_message": "Invalid JSON returned from filter extraction LLM."
        }

    try:
        filters = _validate_and_normalize_filters(filters)
    except Exception as exc:
        logger.exception("Filter validation failed")
        return {
            "filters": [],
            "status": "failed",
            "error_message": str(exc)
        }

    missing_company = not any(
        group.get("requested_company")
        for group in filters
    )

    missing_date = not any(
        group.get("date_received")
        for group in filters
    )

    if missing_company:
        return {
            "filters": filters,
            "status": "failed",
            "error_message": "Company context is required. Please include a company name."
        }

    if missing_date:
        return {
            "filters": filters,
            "status": "failed",
            "error_message": (
                "Date context is required. Please include a date range, "
                "month, year, or relative time period."
            )
        }

    return {
        "filters": filters,
        "status": "running",
        "error_message": None
    }