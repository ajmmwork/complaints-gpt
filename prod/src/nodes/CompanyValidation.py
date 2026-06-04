from src.state.state import State
from src.db.DatabaseManager import DatabaseManager
from langchain_openai import ChatOpenAI
import logging
import json
from src.state.state import Filters
from typing import List

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)


MIN_COMPANY_MATCH_CONFIDENCE = 0.85


def CompanyValidation(state: State, config: DatabaseManager):
    logger.info("ENTERED Company Validation")

    filter_groups = state.get("filters", [])
    new_filter_groups: List[Filters] = []

    available_companies = config.dql.select_all_from_table(
        "company",
        "companies"
    )

    available_company_set = set(available_companies)
    company_list_text = "\n".join(str(company) for company in available_companies)

    for group in filter_groups:
        copy_group: Filters = dict(group)
        user_company = copy_group.get("requested_company")

        if not user_company:
            copy_group["company"] = ""
            copy_group["company_validation"] = "failed"
            new_filter_groups.append(copy_group)
            continue

        response = llm.invoke(
            f"""
            You are validating a user-entered company against the local CFPB company registry.

            User-entered company:
            {user_company}

            Available companies:
            {company_list_text}

            Return ONLY valid JSON.
            Do not include markdown.
            Do not include explanations outside JSON.

            Return exactly this shape:

            {{
                "decision": "match" or "no_match",
                "matched_company": string or null,
                "confidence": number,
                "reason": string
            }}

            Rules:
            - Use the full available company list.
            - Choose "match" only if the user-entered company clearly refers to one legal entity in the available list.
            - Do not force a weak match.
            - Do not match random strings, unknown acronyms, typos with no clear target, or unrelated names.
            - If the input is a common abbreviation, ticker, or brand name, match only if it is widely recognizable.
            - If unsure, return "no_match".
            - If decision is "match", matched_company must be exactly one company from the available list.
            - If decision is "no_match", matched_company must be null.
            - confidence must be between 0 and 1.
            - Use high confidence only for clear matches.

            Examples:
            BofA -> {{"decision": "match", "matched_company": "BANK OF AMERICA, NATIONAL ASSOCIATION", "confidence": 0.98, "reason": "BofA is a common abbreviation for Bank of America."}}
            Bank of America -> {{"decision": "match", "matched_company": "BANK OF AMERICA, NATIONAL ASSOCIATION", "confidence": 0.99, "reason": "The user-entered name directly refers to Bank of America."}}
            xkv -> {{"decision": "no_match", "matched_company": null, "confidence": 0.0, "reason": "The input appears to be a random string and does not clearly refer to a known company."}}
            """
        )

        raw_text = response.content.strip()

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse company validation JSON")
            logger.error(raw_text)

            copy_group["company"] = user_company
            copy_group["company_validation"] = "failed"
            new_filter_groups.append(copy_group)
            continue

        decision = result.get("decision")
        matched_company = result.get("matched_company")

        try:
            confidence = float(result.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0

        if (
            decision == "match"
            and confidence >= MIN_COMPANY_MATCH_CONFIDENCE
            and matched_company in available_company_set
        ):
            copy_group["company"] = matched_company
            copy_group["company_validation"] = "complete"
        else:
            copy_group["company"] = user_company
            copy_group["company_validation"] = "failed"

        new_filter_groups.append(copy_group)

    has_failed_company = any(
        group["company_validation"] == "failed"
        for group in new_filter_groups
    )

    return {
        "filters": new_filter_groups,
        "company_resolution": {
            "status": "failed" if has_failed_company else "complete",
            "error_message": (
                "One or more companies could not be resolved."
                if has_failed_company
                else None
            )
        }
    }