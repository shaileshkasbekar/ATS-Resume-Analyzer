"""
UX pass: navigation, journey pages, Action Center, settings,
form preservation and that no page links to a missing route.
"""

import io
import re

from conftest import PYTHON_FRESHER, PYTHON_JD, make_pdf, login
from test_phase_routes import USER_A, USER_B, one, run_job_match


def internal_links(html):
    """
    All internal GET links on a page (no anchors, no external URLs).
    """

    links = set(re.findall(r'href="(/[^"#]*)', html.decode()))

    return {l for l in links if not l.startswith("/static/") and l != "/logout"}


def assert_links_work(client, page_url):

    page = client.get(page_url)

    assert page.status_code == 200, page_url

    for link in internal_links(page.data):

        response = client.get(link)

        assert response.status_code in (200, 302), f"{page_url} -> {link} gave {response.status_code}"

        if response.status_code == 302:
            assert "/login" not in response.headers["Location"], f"{link} needs login unexpectedly"


# ---------------- Navigation and links ----------------

def test_every_link_on_main_pages_works(client, test_db):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db)
    client.post(f"/assistant/{jd_id}/generate")
    client.post(f"/roadmap/create/{jd_id}")

    for url in ["/dashboard", "/action-center", f"/history/jd/{jd_id}", f"/assistant/{jd_id}",
                f"/optimize/{jd_id}", "/roadmap", "/job-match", "/settings", "/history"]:
        assert_links_work(client, url)


def test_sidebar_groups_and_active_page(client, test_db):
    login(client, USER_A)

    page = client.get("/roadmap").data

    for group in (b"Dashboard", b"Resume Tools", b"Career Tools", b"My Workspace", b"Settings"):
        assert group in page

    assert re.search(rb'href="/roadmap" class="active" aria-current="page"', page)
    assert b'class="skip-link"' in page


# ---------------- Pick an analysis ----------------

def test_pick_page(client, test_db):
    from test_phase_routes import db

    connection = db(test_db)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO users (full_name, email, password) VALUES ('Picker', 'pick@test.com', 'x')")
    user = cursor.lastrowid
    connection.commit()
    connection.close()

    login(client, user)

    assert b"No job matches yet" in client.get("/pick/interview").data
    assert client.get("/pick/unknown").status_code == 302

    jd_id = run_job_match(client, test_db)

    # Only one analysis: straight to the tool

    response = client.get("/pick/assistant")
    assert response.status_code == 302 and response.headers["Location"].endswith(f"/assistant/{jd_id}")

    run_job_match(client, test_db)

    assert b"Choose a job match" in client.get("/pick/assistant").data


# ---------------- Action Center ----------------

def test_action_center(client, test_db):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db, job_title="Action Job")
    client.post(f"/roadmap/create/{jd_id}")

    page = client.get(f"/action-center?jd={jd_id}").data

    assert b"Missing job requirements" in page
    assert b"Linux" in page
    assert b"Learning tasks" in page

    # Another user's analysis id is ignored

    login(client, USER_B)

    assert b"Action Job" not in client.get(f"/action-center?jd={jd_id}").data


# ---------------- Job match form ----------------

def test_requirements_preview(client, test_db):
    login(client, USER_A)

    body = client.post("/job-match/preview", json={"job_description": PYTHON_JD}).get_json()

    assert "Python" in body["mandatory"]
    assert "Docker" in body["preferred"]
    assert body["experience_years"] == 0

    assert client.post("/job-match/preview", json={"job_description": "too short"}).status_code == 400


def test_form_keeps_input_after_error(client, test_db):
    login(client, USER_A)

    typed = "Backend role with Python. " * 2

    response = client.post("/job-match", data={
        "mode": "paste", "job_description": typed, "job_title": "Kept Title", "company": "Kept Co",
        "resume": (io.BytesIO(make_pdf(PYTHON_FRESHER)), "r.pdf")
    }, content_type="multipart/form-data")

    assert response.status_code == 400
    assert b"too short" in response.data
    assert typed.encode() in response.data
    assert b'value="Kept Title"' in response.data and b'value="Kept Co"' in response.data


def test_saved_job_form_keeps_input(client, test_db):
    login(client, USER_A)

    response = client.post("/jobs/new", data={"title": "Draft job", "company": "", "description": "short text"})

    assert response.status_code == 400
    assert b"short text" in response.data and b"Draft job" in response.data


# ---------------- Result page ----------------

def test_result_page_sections_and_suggestions(client, test_db):
    login(client, USER_A)

    resume = PYTHON_FRESHER + "- Responsible for testing the payment module\n"
    jd_id = run_job_match(client, test_db, resume_text=resume)

    page = client.get(f"/history/jd/{jd_id}").data

    for text in (b"Job Match Score", b"Resume Quality", b"What this means", b"Fix these first",
                 b"Skills analysis", b"Resume evidence for every requirement", b"Get suggestions",
                 b"Next steps for this job"):
        assert text in page, text

    response = client.post(f"/assistant/{jd_id}/generate", data={"next": "result"})

    assert response.headers["Location"].endswith(f"/history/jd/{jd_id}#suggestions")
    assert b"data-edit-suggestion" in client.get(f"/history/jd/{jd_id}").data or b"Got it" in client.get(f"/history/jd/{jd_id}").data


def test_builder_shows_effect_of_accepted_change(client, test_db):
    login(client, USER_A)

    resume = PYTHON_FRESHER + "- Responsible for testing the payment module\n"
    jd_id = run_job_match(client, test_db, resume_text=resume)

    client.post(f"/assistant/{jd_id}/generate")

    suggestion = one(test_db, "SELECT suggestion_id FROM resume_suggestions WHERE jd_result_id = %s AND original LIKE 'Responsible%%'", (jd_id,))

    # The user edits the text with a fact of their own (Linux) and accepts

    client.post(f"/assistant/suggestion/{suggestion['suggestion_id']}",
                json={"status": "accepted", "improved": "Tested the payment module on a Linux server"})

    # Rule suggestions are advice; turn it into an experience edit for the builder

    from test_phase_routes import db
    connection = db(test_db)
    cursor = connection.cursor()
    cursor.execute("UPDATE resume_suggestions SET kind = 'experience' WHERE suggestion_id = %s", (suggestion["suggestion_id"],))
    connection.commit()
    connection.close()

    page = client.get(f"/optimize/{jd_id}").data

    assert b"Effect of your changes" in page
    assert b"Linux" in page


# ---------------- Other redesigned pages ----------------

def test_general_result_fix_first(client, test_db):
    login(client, USER_A)

    response = client.post("/general-analyzer", data={"resume": (io.BytesIO(make_pdf(PYTHON_FRESHER)), "r.pdf")},
                           content_type="multipart/form-data")

    assert b"Fix these first" in response.data or b"Improve it with" in response.data


def test_roadmap_grouped_by_priority(client, test_db):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db)
    client.post(f"/roadmap/create/{jd_id}")

    page = client.get("/roadmap").data

    assert b"Required skills to learn" in page
    assert b"Roadmaps by job" in page


def test_interview_one_question_at_a_time(client, test_db):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db)
    client.post(f"/interview/{jd_id}")

    page = client.get(f"/interview/{jd_id}").data

    assert b"data-interview" in page and b"data-pager" in page
    assert b"Question 1 of" in page


# ---------------- Settings ----------------

def test_settings_profile_and_password(client, test_db):
    from werkzeug.security import generate_password_hash
    from test_phase_routes import db

    connection = db(test_db)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO users (full_name, email, password) VALUES ('Old Name', 'settings@test.com', %s)",
                   (generate_password_hash("oldpassword1"),))
    user = cursor.lastrowid
    connection.commit()
    connection.close()

    login(client, user)

    client.post("/settings/profile", data={"fullname": "New Name"})
    assert b"New Name" in client.get("/settings").data

    wrong = client.post("/settings/password", data={"current_password": "nope", "new_password": "newpassword1",
                                                    "confirm_password": "newpassword1"}, follow_redirects=True)
    assert b"current password is not correct" in wrong.data

    mismatch = client.post("/settings/password", data={"current_password": "oldpassword1", "new_password": "newpassword1",
                                                       "confirm_password": "different1"}, follow_redirects=True)
    assert b"do not match" in mismatch.data

    ok = client.post("/settings/password", data={"current_password": "oldpassword1", "new_password": "newpassword1",
                                                 "confirm_password": "newpassword1"}, follow_redirects=True)
    assert b"Password changed" in ok.data

    client.get("/logout")
    response = client.post("/login", data={"email": "settings@test.com", "password": "newpassword1"})
    assert response.headers["Location"].endswith("/dashboard")
