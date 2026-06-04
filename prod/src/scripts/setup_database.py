import os
import yaml
import psycopg

from src.db.DatabaseManager import DatabaseManager


def main():
    with open("src/db/queries.yaml", "r") as file:
        queries = yaml.safe_load(file)

    conn = psycopg.connect(
        dbname=os.environ.get("dbname"),
        user=os.environ.get("admin_user"),
        password=os.environ.get("admin_password"),
        host=os.environ.get("host"),
        port=os.environ.get("port"),
    )

    try:
        DatabaseManager(
            connection=conn,
            queries=queries,
            verbose=True,
            run_setup=True,
        )

        print("Database setup complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()