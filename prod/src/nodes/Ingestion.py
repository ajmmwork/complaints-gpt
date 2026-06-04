from src.db.DatabaseManager import DatabaseManager
from src.state.state import State
from cfpb.complaints import CFPBComplaintReader
from llama_index.core import Document
import traceback
import logging

logger = logging.getLogger(__name__)


def Ingestion(state: State, config: DatabaseManager):
    logger.info("ENTERED Ingestion")
    jobs = [
        dict(job)
        for job in state.get("ingestion_jobs", [])
    ]

    for job in jobs:
        job_id = None

        try:
            c = job["company"]
            s = job["start_date"]
            e = job["end_date"]

            job_id_result = config.dml.insert_job(c, s, e)

            if not job_id_result:
                job["status"] = "skipped"
                job["error_message"] = "Job already exists or was not inserted."
                continue

            job_id = job_id_result[0]
            config.dml.mark_job_running(job_id, "jobs")

            reader = CFPBComplaintReader(
                companies=[c],
                start_date_YYYY_MM_DD=s,
                end_date_YYYY_MM_DD=e
            )

            filter_index = config.vector_db.get_filter_index()
            filter_docs = []

            seen_filters = set(
                [("issue", r[0]) for r in config.dql.select_all_from_table("issue", "issues")]
                + [("product", r[0]) for r in config.dql.select_all_from_table("product", "products")]
            )

            docs = reader.load_data()

            for doc in docs:
                complaint_id = doc.metadata["complaint_id"]
                product = doc.metadata["product"]
                issue = doc.metadata["issue"]

                product_key = ("product", product)

                if product_key not in seen_filters:
                    seen_filters.add(product_key)

                    if config.dml.insert_into_filter_tables(
                        "products",
                        "product",
                        product
                    ):
                        filter_docs.append(
                            Document(
                                text=product,
                                metadata={"type": "product"},
                            )
                        )

                issue_key = ("issue", issue)

                if issue_key not in seen_filters:
                    seen_filters.add(issue_key)

                    if config.dml.insert_into_filter_tables(
                        "issues",
                        "issue",
                        issue
                    ):
                        filter_docs.append(
                            Document(
                                text=issue,
                                metadata={"type": "issue"},
                            )
                        )

                complaint_state = doc.metadata.get("state")
                company = doc.metadata["company"]
                date_received = doc.metadata["date_received"]

                if config.dml.insert_complaint(
                    complaint_id,
                    job_id,
                    company,
                    issue,
                    product,
                    complaint_state,
                    date_received,
                ):
                    parts = doc.text.split("\n\n", 1)
                    narrative = parts[1] if len(parts) > 1 else doc.text

                    config.dml.insert_narrative(
                        complaint_id,
                        narrative
                    )

            if filter_docs:
                nodes = config.vector_db.get_parser().get_nodes_from_documents(
                    filter_docs
                )
                filter_index.insert_nodes(nodes)

            config.dml.mark_job_completed(job_id, "jobs")

            job["status"] = "completed"
            job["error_message"] = None

        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(error_message)

            config.conn.rollback()

            if job_id is not None:
                config.dml.mark_job_failed(
                    job_id,
                    "jobs",
                    error_message
                )

            job["status"] = "failed"
            job["error_message"] = str(e)

    if any(job["status"] == "failed" for job in jobs):
        return {
            "ingestion_jobs": jobs,
            "status": "failed",
            "error_message": "One or more ingestion jobs failed."
        }

    return {
        "ingestion_jobs": jobs,
        "status": "completed",
        "error_message": None
    }