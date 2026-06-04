from psycopg import Connection
from typing import Any

from src.db.DDLManager import DDLManager
from src.db.DQLManager import DQLManager
from src.db.DMLManager import DMLManager
from src.db.VectorDatabase import VectorDB


class DatabaseManager:
    def __init__(
        self,
        connection: Connection,
        queries: dict[str, Any],
        verbose: bool = True,
        run_setup: bool = False
    ):
        self.conn = connection
        self.queries = queries
        self.verbose = verbose

        self.ddl = DDLManager(connection, queries, verbose)
        self.dql = DQLManager(connection, queries, verbose)
        self.dml = DMLManager(connection, queries, verbose)
        self.vector_db = VectorDB(
            dataset_path="src/vector_dbs/issues_vdb",
            chunk_size=512
        )

        if run_setup:
            self.ddl.setup_database()