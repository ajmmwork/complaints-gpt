from psycopg import Connection, sql
from typing import Any
import logging
import os
import psycopg

logger = logging.getLogger(__name__)


class DQLManager:
    def __init__(
        self,
        conn: Connection,
        queries: dict[str, Any],
        verbose=True
    ):
        self.conn = conn
        self.queries = queries
        self.verbose = verbose

    def _log(self, message: str):
        if self.verbose:
            logger.info(message)

    def get_conninfo(self):
        return (
            f"dbname={os.environ.get('dbname')} "
            f"user={os.environ.get('user')} "
            f"password={os.environ.get('password')} "
            f"host={os.environ.get('host')} "
            f"port={os.environ.get('port')}"
        )

    def get_connection(self):
        return psycopg.connect(self.get_conninfo())

    def select_all_from_table(self, field: str, table: str):
        query = sql.SQL(
            self.queries["select_all_from_column"]
        ).format(
            field=sql.Identifier(field),
            table=sql.Identifier(table)
        )

        with self.conn.cursor() as cur:
            cur.execute(query)
            result = cur.fetchall()

        return [r[0] for r in result]

    def select_all_from_column(self, field: str, table: str):
        return self.select_all_from_table(field, table)

    def extract_required_data_coverage_jobs(
        self,
        company: str,
        start_date: str,
        end_date: str
    ):
        params = {
            "company": company,
            "start_date": start_date,
            "end_date": end_date
        }

        with self.conn.cursor() as cur:
            cur.execute(
                self.queries["extract_required_data_coverage_jobs"],
                params
            )
            result = cur.fetchall()

        return result

    def check_filter_value_does_not_exist(
        self,
        table: str,
        column: str,
        value: str
    ):
        query = sql.SQL(
            self.queries["check_filter_value_does_not_exist"]
        ).format(
            table=sql.Identifier(table),
            column=sql.Identifier(column),
        )

        with self.conn.cursor() as cur:
            cur.execute(query, params={"value": value})
            result = cur.fetchone()

        return result is None

    def select_complaint_documents_by_filter_group(self, filter_group: dict):
        conditions = []
        params = {}

        for key in ["company", "issue", "product", "state"]:
            value = filter_group.get(key)

            if value is not None:
                conditions.append(
                    sql.SQL("c.{field} = %({param})s").format(
                        field=sql.Identifier(key),
                        param=sql.SQL(key)
                    )
                )
                params[key] = value

        date_ranges = filter_group.get("date_received") or []
        date_conditions = []

        for i, date_range in enumerate(date_ranges):
            start_key = f"start_date_{i}"
            end_key = f"end_date_{i}"

            date_conditions.append(
                sql.SQL(
                    "(c.date_received BETWEEN %({start})s AND %({end})s)"
                ).format(
                    start=sql.SQL(start_key),
                    end=sql.SQL(end_key)
                )
            )

            params[start_key] = date_range["start_date"]
            params[end_key] = date_range["end_date"]

        if date_conditions:
            conditions.append(
                sql.SQL("(")
                + sql.SQL(" OR ").join(date_conditions)
                + sql.SQL(")")
            )

        query = sql.SQL("""
            SELECT
                c.complaint_id,
                c.company,
                c.issue,
                c.product,
                c.state,
                c.date_received,
                n.narrative
            FROM complaints c
            JOIN complaints_narratives n
              ON c.complaint_id = n.complaint_id
        """)

        if conditions:
            query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)

        query += sql.SQL(" ORDER BY c.date_received, c.complaint_id")

        # Important: use a new connection so concurrent semantic tasks can run in parallel.
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return [
            {
                "complaint_id": row[0],
                "company": row[1],
                "issue": row[2],
                "product": row[3],
                "state": row[4],
                "date_received": row[5],
                "narrative": row[6],
            }
            for row in rows
        ]

    def execute_query(self, query: str, params: dict[str, Any]):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchall()
                desc = [col.name for col in cur.description]

        return desc, result