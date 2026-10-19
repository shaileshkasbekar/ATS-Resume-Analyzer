"""
Runs a .sql file against the app's database (settings from .env).

Usage:
    venv\\Scripts\\python.exe database\\run_sql.py database\\fix_roles.sql

Add --dry-run to test it and undo everything afterwards.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_db_connection


def split_statements(sql):

    # Remove comment lines, then split on ";"

    lines = [
        line for line in sql.splitlines()
        if not line.strip().startswith("--")
    ]

    return [
        statement.strip()
        for statement in "\n".join(lines).split(";")
        if statement.strip()
    ]


def main():

    if len(sys.argv) < 2:
        print(__doc__)
        return

    path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    with open(path, encoding="utf-8") as file:
        statements = split_statements(file.read())

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        for statement in statements:

            cursor.execute(statement)

            first_line = statement.splitlines()[0][:70]
            print(f"OK ({cursor.rowcount} rows)  {first_line}")

        if dry_run:
            connection.rollback()
            print("\nDry run: all statements worked, changes were undone.")
        else:
            connection.commit()
            print("\nDone: changes saved.")

    except Exception as e:

        connection.rollback()
        print("\nERROR:", e)
        print("Nothing was changed.")

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
