"""
Phases 2-4 through the web routes, on the throwaway test database.
"""

import io
import json

import fitz
import mysql.connector

from config import Config
from conftest import PYTHON_FRESHER, PYTHON_JD, JAVA_JD, make_pdf, login


USER_A = 1
USER_B = 2


def db(test_db):
    return mysql.connector.connect(
        host=Config.MYSQL_HOST, user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD, database=test_db
    )


def one(test_db, sql, params=()):
    connection = db(test_db)
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    connection.close()
    return row


def run_job_match(client, test_db, resume_text=PYTHON_FRESHER, **fields):
    data = {"mode": "paste", "job_description": PYTHON_JD, "job_title": "Backend Dev"}
    data.update(fields)
    data.setdefault("resume", (io.BytesIO(make_pdf(resume_text)), "resume.pdf"))

    client.post("/job-match", data=data, content_type="multipart/form-data")

    return one(test_db, "SELECT * FROM jd_results ORDER BY jd_result_id DESC LIMIT 1")["jd_result_id"]


def add_version(client, test_db, label, text=PYTHON_FRESHER):
    client.post("/resumes", data={"label": label, "resume": (io.BytesIO(make_pdf(text)), "r.pdf")},
                content_type="multipart/form-data")
    return one(test_db, "SELECT version_id FROM resume_versions WHERE label = %s ORDER BY version_id DESC LIMIT 1", (label,))["version_id"]


def add_saved_job(client, test_db, title, description):
    client.post("/jobs/new", data={"title": title, "company": "Acme", "description": description})
    return one(test_db, "SELECT job_id FROM saved_jobs WHERE title = %s ORDER BY job_id DESC LIMIT 1", (title,))["job_id"]


# ---------------- Improvement assistant + optimized resume ----------------

def test_assistant_workflow(client, test_db):
    login(client, USER_A)

    resume = PYTHON_FRESHER + "- Responsible for testing the payment module\n"
    jd_id = run_job_match(client, test_db, resume_text=resume)

    assert client.get(f"/assistant/{jd_id}").status_code == 200

    client.post(f"/assistant/{jd_id}/generate")

    suggestion = one(test_db, "SELECT * FROM resume_suggestions WHERE jd_result_id = %s LIMIT 1", (jd_id,))

    assert suggestion is not None

    response = client.post(f"/assistant/suggestion/{suggestion['suggestion_id']}", json={"status": "accepted", "improved": "Tested the payment module with 40 Pytest cases"})

    assert response.get_json()["status"] == "accepted"
    assert one(test_db, "SELECT status FROM resume_suggestions WHERE suggestion_id = %s", (suggestion["suggestion_id"],))["status"] == "accepted"

    assert client.post(f"/assistant/suggestion/{suggestion['suggestion_id']}", json={"status": "hacked"}).status_code == 400


def test_optimized_resume_preview_download_and_save(client, test_db):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db)

    for template in ("classic", "modern", "technical", "fresher"):
        assert client.get(f"/optimize/{jd_id}?template={template}").status_code == 200

    pdf = client.get(f"/optimize/{jd_id}/download?template=modern")

    assert pdf.mimetype == "application/pdf"
    assert "Riya Sharma" in fitz.open(stream=pdf.data, filetype="pdf")[0].get_text()

    client.post(f"/optimize/{jd_id}/save", data={"template": "fresher"})

    version = one(test_db, "SELECT * FROM resume_versions WHERE label LIKE 'Optimized for%%' ORDER BY version_id DESC LIMIT 1")

    assert version and "Riya Sharma" in version["resume_text"]


def test_other_user_cannot_use_assistant(client, test_db):
    login(client, USER_A)
    jd_id = run_job_match(client, test_db)
    client.post(f"/assistant/{jd_id}/generate")
    suggestion = one(test_db, "SELECT suggestion_id FROM resume_suggestions WHERE jd_result_id = %s LIMIT 1", (jd_id,))

    login(client, USER_B)

    assert client.get(f"/assistant/{jd_id}").status_code == 302
    assert client.get(f"/optimize/{jd_id}/download").status_code == 302

    if suggestion:
        response = client.post(f"/assistant/suggestion/{suggestion['suggestion_id']}", json={"status": "rejected"})
        assert response.status_code == 404


# ---------------- Reports ----------------

def test_reports(client, test_db):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db)

    connection = db(test_db)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO resumes (user_id, file_name, file_path) VALUES (%s, 'old.pdf', 'none')", (USER_A,))
    resume_id = cursor.lastrowid
    cursor.execute("INSERT INTO resume_results (resume_id, role_id, ats_score, matched_skills, missing_skills, recommended_skills, strengths) "
                   "VALUES (%s, 6, 71.5, 'Python, SQL', 'Docker', %s, %s)",
                   (resume_id, json.dumps(["Learn Docker, then Kubernetes"]), json.dumps(["Good projects"])))
    ats_id = cursor.lastrowid
    cursor.execute("INSERT INTO general_results (resume_id, score, email_detected, phone_detected, word_count, skills, sections, recommendations) "
                   "VALUES (%s, 80, 1, 1, 400, '[\"Python\"]', '{\"skills\": true}', '[\"Add a summary\"]')", (resume_id,))
    general_id = cursor.lastrowid
    connection.commit()
    connection.close()

    for url, expected in ((f"/report/jd/{jd_id}.pdf", "Job Match Report"),
                          (f"/report/ats/{ats_id}.pdf", "ATS Role Report"),
                          (f"/report/general/{general_id}.pdf", "Resume Quality Report")):

        response = client.get(url)

        assert response.mimetype == "application/pdf", url
        assert expected in fitz.open(stream=response.data, filetype="pdf")[0].get_text()

    # Recommendations with commas are kept whole (saved as JSON)

    text = fitz.open(stream=client.get(f"/report/ats/{ats_id}.pdf").data, filetype="pdf")[0].get_text()
    assert "Learn Docker, then Kubernetes" in text

    login(client, USER_B)

    for url in (f"/report/jd/{jd_id}.pdf", f"/report/ats/{ats_id}.pdf", f"/report/general/{general_id}.pdf"):
        assert client.get(url).status_code == 302


# ---------------- Versions + saved jobs ----------------

def test_versions_and_comparison(client, test_db):
    login(client, USER_A)

    v1 = add_version(client, test_db, "v1 original")
    v2 = add_version(client, test_db, "v2 with linux", PYTHON_FRESHER.replace("with Docker", "with Docker on Linux"))
    job = add_saved_job(client, test_db, "Python job", PYTHON_JD)

    page = client.get(f"/resumes/compare?a={v1}&b={v2}&job={job}").data

    assert b"What changed the job match score" in page
    assert b"Linux" in page

    # Job match with a saved job and a saved version (no upload)

    jd_id = run_job_match(client, test_db, mode="saved", saved_job_id=str(job), resume_version_id=str(v2),
                          resume=(io.BytesIO(b""), ""))

    row = one(test_db, "SELECT version_id, saved_job_id FROM jd_results WHERE jd_result_id = %s", (jd_id,))

    assert row["version_id"] == v2 and row["saved_job_id"] == job

    assert b"Python job" in client.get("/resumes").data

    login(client, USER_B)

    assert client.get(f"/resumes/compare?a={v1}&b={v2}").status_code == 302
    client.post(f"/resumes/{v1}/delete")
    assert one(test_db, "SELECT 1 AS x FROM resume_versions WHERE version_id = %s", (v1,))


def test_saved_jobs_crud_and_ownership(client, test_db):
    login(client, USER_A)

    job = add_saved_job(client, test_db, "Editable job", PYTHON_JD)

    saved = one(test_db, "SELECT requirements FROM saved_jobs WHERE job_id = %s", (job,))
    assert "Python" in saved["requirements"]

    client.post(f"/jobs/{job}/edit", data={"title": "Edited job", "company": "", "description": JAVA_JD + "\n" * 3 + "x" * 80})

    assert one(test_db, "SELECT title FROM saved_jobs WHERE job_id = %s", (job,))["title"] == "Edited job"

    login(client, USER_B)

    assert client.get(f"/jobs/{job}").status_code == 302
    client.post(f"/jobs/{job}/delete")
    assert one(test_db, "SELECT 1 AS x FROM saved_jobs WHERE job_id = %s", (job,))

    login(client, USER_A)
    client.post(f"/jobs/{job}/delete")
    assert one(test_db, "SELECT 1 AS x FROM saved_jobs WHERE job_id = %s", (job,)) is None


def test_multi_job_comparison(client, test_db):
    login(client, USER_A)

    version = add_version(client, test_db, "compare me")
    a = add_saved_job(client, test_db, "Compare Python", PYTHON_JD)
    b = add_saved_job(client, test_db, "Compare Java", JAVA_JD + "\n" + "Requirements: Git, Linux, SQL. " * 3)

    page = client.post("/jobs/compare", data={"version_id": version, "job_ids": [a, b]}, follow_redirects=True).data

    assert b"Compare Python" in page and b"Compare Java" in page
    assert b"Roles that fit your skills" in page


# ---------------- Roadmap, projects, interview ----------------

def test_roadmap_progress(client, test_db):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db)

    client.post(f"/roadmap/create/{jd_id}")

    item = one(test_db, "SELECT * FROM roadmap_items WHERE jd_result_id = %s ORDER BY item_id LIMIT 1", (jd_id,))

    assert item["skill"] == "Linux"

    body = client.post(f"/roadmap/item/{item['item_id']}", json={"done": True}).get_json()

    assert body["done"] >= 1
    assert b"Linux" in client.get("/roadmap").data
    assert client.get("/roadmap.pdf").mimetype == "application/pdf"

    login(client, USER_B)

    assert client.post(f"/roadmap/item/{item['item_id']}", json={"done": False}).status_code == 404


def test_projects_and_interview_without_ai(client, test_db):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db)

    client.post(f"/projects/{jd_id}")
    assert b"Core features" in client.get(f"/projects/{jd_id}").data

    client.post(f"/interview/{jd_id}")
    assert b"Show suggested answer" in client.get(f"/interview/{jd_id}").data

    response = client.post(f"/interview/{jd_id}/answer", json={"index": 0, "answer": "In my project I built a Flask API for 200 students."})

    assert response.get_json()["feedback"]["basic"] is True
    assert client.post(f"/interview/{jd_id}/answer", json={"index": 99, "answer": "A long enough answer here."}).status_code == 404
    assert client.post(f"/interview/{jd_id}/answer", json={"index": 0, "answer": "short"}).status_code == 400


# ---------------- Dashboard + history ----------------

def test_dashboard_with_data_and_empty(client, test_db):
    login(client, USER_A)
    run_job_match(client, test_db)
    run_job_match(client, test_db)

    page = client.get("/dashboard").data

    assert b"Job match score history" in page
    assert b"Most frequently missing skills" in page
    assert b"Continue where you left off" in page
    assert b"chart.umd.min.js" in page

    connection = db(test_db)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO users (full_name, email, password) VALUES ('Empty', 'empty@test.com', 'x')")
    empty_user = cursor.lastrowid
    connection.commit()
    connection.close()

    login(client, empty_user)

    empty = client.get("/dashboard").data

    assert b"How to get started" in empty
    assert b"Continue where you left off" not in empty


def test_history_filters_sorting_pagination(client, test_db):
    login(client, USER_A)

    for i in range(3):
        run_job_match(client, test_db, job_title=f"Paged Job {i}")

    assert b"Paged Job" in client.get("/history?type=jd&q=Paged").data
    assert b"No analyses match these filters" in client.get("/history?type=general&q=Paged").data
    assert client.get("/history?sort=score_desc&page=999").status_code == 200
    assert client.get("/history?sort=DROP TABLE&type=x").status_code == 200

    # Pagination: more than one page of results

    for i in range(16):
        run_job_match(client, test_db, job_title=f"Many {i}")

    assert b'class="pagination"' in client.get("/history").data
