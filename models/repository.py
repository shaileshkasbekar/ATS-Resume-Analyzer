"""
Database access shared by the newer features.

Every function takes the user_id and only returns that user's
records, so one user can never read another user's data.
"""

import json
import os

from models.database import get_db_connection, table_columns
from resume_parser.pdf_reader import extract_text_from_pdf


def _query(sql, params=(), one=False):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def _execute(sql, params=()):
    """
    Runs an INSERT/UPDATE/DELETE. Returns (lastrowid, rowcount).
    """

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(sql, params)
        connection.commit()
        return cursor.lastrowid, cursor.rowcount
    finally:
        cursor.close()
        connection.close()


def has_table(name):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        return bool(table_columns(cursor, name))
    finally:
        cursor.close()
        connection.close()


def columns_of(name):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        return table_columns(cursor, name)
    finally:
        cursor.close()
        connection.close()


def loads(value, default):

    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


# =========================================
# Job match results
# =========================================

def get_jd_result(user_id, jd_result_id):
    """
    The saved job match with its parsed result, or None.
    """

    row = _query(
        """
        SELECT jd.*, r.file_name, r.file_path, r.user_id
        FROM jd_results jd
        JOIN resumes r ON r.resume_id = jd.resume_id
        WHERE jd.jd_result_id = %s AND r.user_id = %s
        """,
        (jd_result_id, user_id),
        one=True
    )

    if not row:
        return None

    row["result"] = loads(row.get("details"), {})

    return row


def resume_text_for(row):
    """
    The resume text behind a saved analysis: the stored version text
    if available, otherwise re-read from the saved PDF.
    """

    version_id = row.get("version_id")

    if version_id:

        version = _query(
            "SELECT resume_text FROM resume_versions WHERE version_id = %s AND user_id = %s",
            (version_id, row["user_id"]),
            one=True
        )

        if version and version.get("resume_text"):
            return version["resume_text"]

    path = row.get("file_path")

    if path and os.path.exists(path):
        return extract_text_from_pdf(path)

    return ""


def list_jd_results(user_id, limit=None):

    sql = """
        SELECT jd.jd_result_id, jd.job_title, jd.score, jd.created_at, r.file_name
        FROM jd_results jd
        JOIN resumes r ON r.resume_id = jd.resume_id
        WHERE r.user_id = %s
        ORDER BY jd.created_at DESC, jd.jd_result_id DESC
    """

    if limit:
        sql += f" LIMIT {int(limit)}"

    return _query(sql, (user_id,))


# =========================================
# Generated content (projects, interview questions)
# =========================================

def get_generated(user_id, jd_result_id, kind):

    row = _query(
        "SELECT content FROM generated_content WHERE user_id = %s AND jd_result_id = %s AND kind = %s",
        (user_id, jd_result_id, kind),
        one=True
    )

    return loads(row["content"], None) if row else None


def save_generated(user_id, jd_result_id, kind, content):

    _execute(
        """
        INSERT INTO generated_content (user_id, jd_result_id, kind, content)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE content = VALUES(content), created_at = CURRENT_TIMESTAMP
        """,
        (user_id, jd_result_id, kind, json.dumps(content))
    )


# =========================================
# Resume versions
# =========================================

def list_versions(user_id):

    return _query(
        """
        SELECT version_id, label, file_name, created_at
        FROM resume_versions
        WHERE user_id = %s
        ORDER BY created_at DESC, version_id DESC
        """,
        (user_id,)
    )


def get_version(user_id, version_id):

    return _query(
        "SELECT * FROM resume_versions WHERE version_id = %s AND user_id = %s",
        (version_id, user_id),
        one=True
    )


def add_version(user_id, label, file_name, file_path, text):

    version_id, _ = _execute(
        """
        INSERT INTO resume_versions (user_id, label, file_name, file_path, resume_text)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, label, file_name, file_path, text)
    )

    return version_id


def delete_version(user_id, version_id):

    version = get_version(user_id, version_id)

    if not version:
        return False

    _execute("DELETE FROM resume_versions WHERE version_id = %s AND user_id = %s", (version_id, user_id))

    # Keep the PDF if older analyses still point to it

    still_used = _query("SELECT 1 FROM resumes WHERE file_path = %s LIMIT 1", (version["file_path"],), one=True)

    if not still_used and os.path.exists(version["file_path"]):
        os.remove(version["file_path"])

    return True


# =========================================
# Saved jobs
# =========================================

def list_saved_jobs(user_id):

    return _query(
        """
        SELECT job_id, title, company, created_at, updated_at, LEFT(description, 220) AS preview
        FROM saved_jobs
        WHERE user_id = %s
        ORDER BY updated_at DESC, job_id DESC
        """,
        (user_id,)
    )


def get_saved_job(user_id, job_id):

    row = _query(
        "SELECT * FROM saved_jobs WHERE job_id = %s AND user_id = %s",
        (job_id, user_id),
        one=True
    )

    if row:
        row["requirements_data"] = loads(row.get("requirements"), None)

    return row


def save_job(user_id, title, company, description, requirements, job_id=None):

    if job_id:

        _execute(
            """
            UPDATE saved_jobs SET title = %s, company = %s, description = %s, requirements = %s
            WHERE job_id = %s AND user_id = %s
            """,
            (title, company, description, json.dumps(requirements), job_id, user_id)
        )

        return job_id

    new_id, _ = _execute(
        """
        INSERT INTO saved_jobs (user_id, title, company, description, requirements)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, title, company, description, json.dumps(requirements))
    )

    return new_id


def delete_saved_job(user_id, job_id):

    _, count = _execute("DELETE FROM saved_jobs WHERE job_id = %s AND user_id = %s", (job_id, user_id))

    return count > 0
