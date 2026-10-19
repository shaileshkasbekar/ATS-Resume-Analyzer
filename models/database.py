import mysql.connector
from config import Config


def get_db_connection():
    connection = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE
    )

    return connection


def table_columns(cursor, table):
    """
    Column names of a table, or an empty set if the table
    does not exist yet (database upgrade not run).
    """

    try:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    except mysql.connector.Error:
        return set()

    return {row[0] if isinstance(row, tuple) else row["Field"] for row in cursor.fetchall()}
