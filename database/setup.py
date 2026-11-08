"""
Creates or upgrades the database automatically (used when the app starts online).

    python -m database.setup

Safe to run on every start:
- a new, empty database gets all tables and the default job roles;
- an existing database only gets the upgrade files it has not had yet;
- a database that was set up by hand before is detected and left as it is.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector

from config import Config
from database.run_sql import ALREADY_DONE_ERRORS, split_statements

HERE = os.path.dirname(os.path.abspath(__file__))

FILES = ["schema.sql", "upgrade_v3.sql", "upgrade_v4.sql", "upgrade_v5.sql", "upgrade_v6.sql"]

DEFAULT_NAME = "ats_resume_analyzer_v2"


def run(connect=None, log=print):

    name = Config.MYSQL_DATABASE

    connection = (connect or mysql.connector.connect)(
        host=Config.MYSQL_HOST, port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD
    )

    cursor = connection.cursor()

    try:

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{name}`")
        cursor.execute(f"USE `{name}`")

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS schema_files ("
            " name VARCHAR(100) PRIMARY KEY,"
            " applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )

        cursor.execute("SELECT name FROM schema_files")
        done = {row[0] for row in cursor.fetchall()}

        cursor.execute("SHOW TABLES LIKE 'users'")
        has_users = cursor.fetchone() is not None

        if not done and has_users:

            # Set up by hand earlier (run_sql.py): only check the newest upgrade
            # below, and never re-run the files that insert the job roles

            done = {"schema.sql", "upgrade_v3.sql"}
            cursor.executemany("INSERT IGNORE INTO schema_files (name) VALUES (%s)", [(f,) for f in done])

        for file_name in FILES:

            if file_name in done:
                continue

            with open(os.path.join(HERE, file_name), encoding="utf-8") as file:
                sql = file.read().replace(DEFAULT_NAME, name)

            for statement in split_statements(sql):

                if statement.upper().startswith(("CREATE DATABASE", "USE ")):
                    continue

                try:
                    cursor.execute(statement)
                except mysql.connector.Error as e:
                    if e.errno not in ALREADY_DONE_ERRORS:
                        raise

            cursor.execute("INSERT INTO schema_files (name) VALUES (%s)", (file_name,))
            connection.commit()

            log(f"Database: applied {file_name}")

        connection.commit()
        log(f"Database '{name}' is ready.")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    run()
