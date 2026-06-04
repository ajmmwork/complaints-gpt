from psycopg import Connection, sql
from typing import Any, List
import logging

logger = logging.getLogger(__name__)
class DMLManager:
    def __init__(self, conn : Connection, queries : dict[str, Any], verbose = True):
        self.conn = conn
        self.queries = queries
        self.verbose = verbose

    def _log(self, message : str):
        if self.verbose:
            logger.info(message)

    def insert_into_filter_tables(self, table : str, column : str, value : str):
        query = sql.SQL(self.queries["insert_into_filter_tables"]).format(
            table = sql.Identifier(table),
            column = sql.Identifier(column)
        )

        with self.conn.cursor() as cur:
            cur.execute(query, params={"value" : value})
            result = cur.fetchone()

        self.conn.commit()
        return result
    
    def insert_job(self, company, start_date : str, end_date: str):
        params = {
            "company" : company,
            "start_date" : start_date,
            "end_date" : end_date,
        }

        with self.conn.cursor() as cur:
            cur.execute(self.queries["insert_job"], params=params)
            result = cur.fetchone()
        
        self.conn.commit()
        return result
    
    def insert_complaint(self, complaint_id : str, job_id : str, company : str, issue : str, product : str, state : str, date_received : str):
        params = {
            "complaint_id" : complaint_id,
            "job_id" : job_id,
            "company" : company,
            "issue" : issue,
            "product" : product,
            "state" : state,
            "date_received" : date_received
        }
        with self.conn.cursor() as cur:
            cur.execute(self.queries["insert_complaint"], params=params)
            result = cur.fetchone()
        
        self.conn.commit()

        return result
    
    def insert_narrative(self, complaint_id : str, narrative : str):
        params = {
            "complaint_id" : complaint_id,
            "narrative" : narrative,
        }

        with self.conn.cursor() as cur:
            cur.execute(self.queries["insert_narrative"], params=params)
            result = cur.fetchone()
        
        self.conn.commit()

        return result
    
    def mark_job_running(self, job_id : str, table: str):
        params = {
            "job_id" : job_id
        }

        query = sql.SQL(self.queries["mark_job_running"]).format(
            table = sql.Identifier(table))

        with self.conn.cursor() as cur:
            cur.execute(query, params=params)
        
        self.conn.commit()

    def mark_job_completed(self, job_id : str, table: str):
        query = sql.SQL(self.queries["mark_job_completed"]).format(
            table = sql.Identifier(table)
        )
        params = {
            "job_id" : job_id
        }

        with self.conn.cursor() as cur:
            cur.execute(query, params=params)
        
        self.conn.commit()

    def mark_job_failed(self, job_id : str, table: str, error_message: str):
        query = sql.SQL(self.queries["mark_job_failed"]).format(
            table = sql.Identifier(table)
        )
        params = {
            "job_id" : job_id,
            "error_message" : error_message
        }

        with self.conn.cursor() as cur:
            cur.execute(query, params=params)
        
        self.conn.commit()

    def mark_job_pending(self, job_id : str, table: str):
        query = sql.SQL(self.queries["mark_job_pending"]).format(
            table = sql.Identifier(table)
        )
        params = {
            "job_id" : job_id
        }

        with self.conn.cursor() as cur:
            cur.execute(query, params=params)
        
        self.conn.commit()

    def insert_exploratory_job(self, start: str, end: str, fallback_level: str):
        params = {
            "start_date" : start,
            "end_date" : end,
            "level" : fallback_level
        }

        with self.conn.cursor() as cur:
            cur.execute(self.queries["insert_exploratory_job"], params=params)
            result = cur.fetchone()

        self.conn.commit()
        return result
    
    def insert_companies(self, rows : List[dict]):


        with self.conn.cursor() as cur:
            cur.executemany(self.queries["insert_company"], rows)

        self.conn.commit()

    

    

    
    


