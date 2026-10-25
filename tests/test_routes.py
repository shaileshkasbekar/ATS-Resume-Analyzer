"""
Full workflow tests through the web routes, on a throwaway database.
"""

import io

import mysql.connector

from config import Config
from conftest import PYTHON_FRESHER, PYTHON_JD, make_pdf, login


USER_A = 1
USER_B = 2


def post_job_match(client, **fields):

    data = {"mode": "paste", "job_description": PYTHON_JD, "job_title": "Backend Dev", "company": "Acme"}
    data.update(fields)

    if "resume" not in data:
        data["resume"] = (io.BytesIO(make_pdf(PYTHON_FRESHER)), "resume.pdf")

    return client.post("/job-match", data=data, content_type="multipart/form-data", follow_redirects=True)


def latest_jd_result(test_db):

    connection = mysql.connector.connect(
        host=Config.MYSQL_HOST, user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD, database=test_db
    )
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT jd.*, r.user_id FROM jd_results jd JOIN resumes r ON r.resume_id = jd.resume_id "
        "ORDER BY jd.jd_result_id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    connection.close()

    return row


# ---------------- Access ----------------

def test_login_required(client):
    response = client.get("/job-match")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------- Validation ----------------

def test_short_job_description_rejected(client):
    login(client, USER_A)
    response = post_job_match(client, job_description="Python developer")
    assert b"too short" in response.data


def test_resume_must_be_pdf(client):
    login(client, USER_A)
    response = post_job_match(client, resume=(io.BytesIO(b"hello"), "resume.docx"))
    assert b"Only PDF resumes" in response.data


def test_malformed_resume_pdf(client):
    login(client, USER_A)
    response = post_job_match(client, resume=(io.BytesIO(b"%PDF-1.4 broken"), "resume.pdf"))
    assert b"Could not read text" in response.data


def test_job_description_file_type(client):
    login(client, USER_A)
    response = post_job_match(client, mode="file", jd_file=(io.BytesIO(b"x" * 200), "job.docx"))
    assert b"must be a PDF or TXT" in response.data


def test_invalid_mode(client):
    login(client, USER_A)
    response = post_job_match(client, mode="hack")
    assert b"choose how to provide the job" in response.data


# ---------------- Complete workflow ----------------

def test_paste_workflow_saves_result(client, test_db):
    login(client, USER_A)

    response = post_job_match(client)

    assert response.status_code == 200
    assert b"How your score was calculated" in response.data

    row = latest_jd_result(test_db)

    assert row["user_id"] == USER_A
    assert row["company_name"] == "Acme"
    assert row["scoring_version"].startswith("jm-")
    assert row["source_type"] == "paste"
    assert 0 < float(row["score"]) <= 100


def test_txt_file_workflow(client, test_db):
    login(client, USER_A)

    response = post_job_match(client, mode="file", jd_file=(io.BytesIO(PYTHON_JD.encode()), "job.txt"))

    assert response.status_code == 200
    assert latest_jd_result(test_db)["source_type"] == "file"


def test_pdf_file_workflow(client, test_db):
    login(client, USER_A)

    response = post_job_match(client, mode="file", jd_file=(io.BytesIO(make_pdf(PYTHON_JD)), "job.pdf"))

    assert response.status_code == 200
    assert latest_jd_result(test_db)["source_type"] == "file"


def test_role_workflow(client, test_db):
    login(client, USER_A)

    response = post_job_match(client, mode="role", role_id="6")

    assert response.status_code == 200
    assert latest_jd_result(test_db)["source_type"] == "role"


# ---------------- History and ownership ----------------

def test_history_shows_own_job_match(client, test_db):
    login(client, USER_A)
    post_job_match(client)

    row = latest_jd_result(test_db)

    page = client.get("/history").data

    assert b"Backend Dev" in page
    assert client.get(f"/history/jd/{row['jd_result_id']}").status_code == 200


def test_other_user_cannot_view_or_delete(client, test_db):
    login(client, USER_A)
    post_job_match(client)

    row = latest_jd_result(test_db)

    login(client, USER_B)

    response = client.get(f"/history/jd/{row['jd_result_id']}")

    assert response.status_code == 302
    assert b"Backend Dev" not in client.get("/history").data

    client.post(f"/history/delete/jd/{row['jd_result_id']}")

    assert latest_jd_result(test_db)["jd_result_id"] == row["jd_result_id"]


def test_owner_can_delete(client, test_db):
    login(client, USER_A)
    post_job_match(client, job_title="Delete Me")

    row = latest_jd_result(test_db)

    client.post(f"/history/delete/jd/{row['jd_result_id']}")

    newest = latest_jd_result(test_db)

    assert newest is None or newest["jd_result_id"] != row["jd_result_id"]
