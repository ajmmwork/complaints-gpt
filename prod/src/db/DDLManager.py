from psycopg import Connection, sql
from typing import Any
import logging

logger = logging.getLogger(__name__)


class DDLManager:
    def __init__(
        self,
        conn: Connection,
        queries: dict[str, Any],
        verbose=False
    ):
        self.conn = conn
        self.queries = queries
        self.verbose = verbose

    def _log(self, message: str):
        if self.verbose:
            logger.info(message)

    def setup_database(self):
        self.create_jobs_table()
        self.create_complaints_table()
        self.create_complaints_narrative_table()
        self.create_filter_table(filter_name="issue")
        self.create_filter_table(filter_name="product")
        self.create_exploratory_jobs_table()
        self.create_companies_table()

    def create_jobs_table(self):
        self._log("Creating jobs table if it does not exist")

        with self.conn.cursor() as cur:
            cur.execute(self.queries["create_jobs_table"])
            cur.execute(self.queries["create_jobs_index"])

        self.conn.commit()

        self._log("Jobs table and index are ready")

    def create_complaints_table(self):
        self._log("Creating complaints table if it does not exist")

        with self.conn.cursor() as cur:
            cur.execute(self.queries["create_complaints_table"])

        self.conn.commit()

        self._log("Complaints table is ready")

    def create_complaints_narrative_table(self):
        self._log("Creating complaints narrative table if it does not exist")

        with self.conn.cursor() as cur:
            cur.execute(self.queries["create_complaints_narrative_table"])

        self.conn.commit()

        self._log("Complaints narrative table is ready")

    def create_filter_table(self, filter_name: str):
        self._log(f"Creating {filter_name} table if it does not exist")

        query = sql.SQL(self.queries["create_filter_table"]).format(
            table=sql.Identifier(f"{filter_name}s"),
            column=sql.Identifier(filter_name)
        )

        with self.conn.cursor() as cur:
            cur.execute(query)

        self.conn.commit()

        self._log(f"{filter_name} table is ready")

    def create_exploratory_jobs_table(self):
        self._log("Creating exploratory_jobs table if it does not exist")

        with self.conn.cursor() as cur:
            cur.execute(self.queries["create_exploratory_jobs_table"])

        self.conn.commit()

        self._log("exploratory_jobs table is ready")

    def create_companies_table(self):
        self._log("Creating companies table if it does not exist")

        with self.conn.cursor() as cur:
            cur.execute(self.queries["create_companies_table"])

        self.conn.commit()

        self._log("companies table is ready")