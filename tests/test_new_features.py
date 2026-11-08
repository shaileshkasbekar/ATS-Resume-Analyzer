"""
Application tracker, writing tools, share links, reminders and admin.
"""

import mysql.connector

from config import Config
from conftest import PYTHON_FRESHER, login
from test_phase_routes import USER_A, USER_B, add_version, add_saved_job, one, run_job_match
from conftest import PYTHON_JD


def db(test_db):
    return mysql.connector.connect(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER,
                                   password=Config.MYSQL_PASSWORD, database=test_db)


# ---------------- Application tracker ----------------

def test_tracker_add_move_edit_delete(client, test_db):
    login(client, USER_A)

    version = add_version(client, test_db, "tracker version")
    job = add_saved_job(client, test_db, "Tracker job", PYTHON_JD)

    client.post("/applications/new", data={"company": "Acme", "job_title": "Backend Dev", "status": "saved",
                                           "version_id": str(version), "saved_job_id": str(job),
                                           "job_url": "https://acme.example/jobs/1"})

    app = one(test_db, "SELECT * FROM applications WHERE company = 'Acme' ORDER BY application_id DESC LIMIT 1")

    assert app["version_id"] == version and app["saved_job_id"] == job

    client.post(f"/applications/{app['application_id']}/status", data={"status": "applied"})

    moved = one(test_db, "SELECT status, applied_on FROM applications WHERE application_id = %s", (app["application_id"],))
    assert moved["status"] == "applied" and moved["applied_on"] is not None

    page = client.get("/applications").data
    assert b"Backend Dev" in page and b"tracker version" in page

    client.post(f"/applications/{app['application_id']}/delete")
    assert one(test_db, "SELECT 1 AS x FROM applications WHERE application_id = %s", (app["application_id"],)) is None


def test_tracker_validation_keeps_input(client, test_db):
    login(client, USER_A)

    response = client.post("/applications/new", data={"company": "Kept Co", "job_title": "", "job_url": "javascript:alert(1)"})

    assert response.status_code == 400
    assert b"Kept Co" in response.data
    assert b"required" in response.data and b"must start with http" in response.data


def test_tracker_cannot_touch_other_users_or_link_their_records(client, test_db):
    login(client, USER_B)
    other_version = add_version(client, test_db, "B secret version")

    login(client, USER_A)
    client.post("/applications/new", data={"company": "Mine", "job_title": "Role", "status": "saved",
                                           "version_id": str(other_version)})

    mine = one(test_db, "SELECT * FROM applications WHERE company = 'Mine' ORDER BY application_id DESC LIMIT 1")
    assert mine["version_id"] is None          # someone else's version is never linked

    login(client, USER_B)
    client.post(f"/applications/{mine['application_id']}/delete")
    client.post(f"/applications/{mine['application_id']}/status", data={"status": "offer"})

    still = one(test_db, "SELECT status FROM applications WHERE application_id = %s", (mine["application_id"],))
    assert still["status"] == "saved"
    assert client.get(f"/applications/{mine['application_id']}/edit").status_code == 302


# ---------------- Writing tools ----------------

def test_writer_without_ai_creates_templates(client, test_db):
    login(client, USER_A)
    jd_id = run_job_match(client, test_db)

    client.post(f"/write/{jd_id}/cover_letter")
    client.post(f"/write/{jd_id}/linkedin")

    page = client.get(f"/write/{jd_id}").data
    assert b"Dear Hiring Manager" in page
    assert b"Riya Sharma" in page

    client.post(f"/write/{jd_id}/cover_letter/save", data={"text": "My edited letter"})
    download = client.get(f"/write/{jd_id}/cover_letter.txt")
    assert download.data == b"My edited letter"

    login(client, USER_B)
    assert client.get(f"/write/{jd_id}").status_code == 302


def test_writer_removes_invented_skills_and_numbers():
    from resume_parser.writer import keep_only_true_facts

    text, removed, needs_metric = keep_only_true_facts(
        "I built a Flask API used by 200+ students. I also led a Kubernetes migration. It cut costs by 45%.",
        PYTHON_FRESHER
    )

    assert "Flask API used by 200+ students" in text
    assert "Kubernetes" not in text and len(removed) == 1
    assert "45" not in text and "[add real number]" in text and needs_metric


# ---------------- Share links ----------------

def test_share_link_on_off_and_public_view(client, test_db):
    login(client, USER_A)
    jd_id = run_job_match(client, test_db, job_title="Shared Job")

    client.post(f"/share/{jd_id}")
    token = one(test_db, "SELECT share_token FROM jd_results WHERE jd_result_id = %s", (jd_id,))["share_token"]
    assert token and len(token) >= 20

    client.get("/logout")                       # a visitor without an account

    public = client.get(f"/shared/{token}")
    assert public.status_code == 200
    assert b"Shared Job" in public.data and b"read-only" in public.data
    assert b"Next steps for this job" not in public.data
    assert public.headers["X-Robots-Tag"] == "noindex, nofollow"

    login(client, USER_B)                       # someone else cannot turn it off
    client.post(f"/share/{jd_id}", data={"action": "off"})
    assert client.get(f"/shared/{token}").status_code == 200

    login(client, USER_A)
    client.post(f"/share/{jd_id}", data={"action": "off"})
    assert client.get(f"/shared/{token}").status_code == 404
    assert client.get("/shared/short").status_code == 404


# ---------------- Reminders ----------------

def test_reminders_setting_and_sending(client, test_db, monkeypatch):
    login(client, USER_A)

    jd_id = run_job_match(client, test_db)
    client.post(f"/roadmap/create/{jd_id}")
    client.post("/settings/reminders", data={"reminders_enabled": "1"})

    assert one(test_db, "SELECT reminders_enabled FROM users WHERE user_id = %s", (USER_A,))["reminders_enabled"] == 1

    import tools.reminders as reminders

    sent = []

    class FakeSMTP:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, user, password): pass
        def send_message(self, message): sent.append(message)

    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_USER", "bot@test")
    monkeypatch.setenv("SMTP_PASSWORD", "x")

    connection = db(test_db)
    try:
        assert reminders.send_all(connection=connection, smtp_factory=FakeSMTP) >= 1
        assert any(m["To"] == "a@test.com" and "Linux" in m.get_content() for m in sent)

        # Not again within 6 days
        sent.clear()
        reminders.send_all(connection=connection, smtp_factory=FakeSMTP)
        assert not any(m["To"] == "a@test.com" for m in sent)
    finally:
        connection.close()


def test_reminders_not_configured(monkeypatch, capsys, test_db):
    import tools.reminders as reminders

    for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    connection = db(test_db)
    try:
        assert reminders.send_all(connection=connection) == 0
    finally:
        connection.close()

    assert "not configured" in capsys.readouterr().out


# ---------------- Admin ----------------

def test_admin_only_for_listed_emails(client, test_db, monkeypatch):
    login(client, USER_A)

    monkeypatch.setenv("ADMIN_EMAILS", "")
    assert client.get("/admin").status_code == 404

    monkeypatch.setenv("ADMIN_EMAILS", "b@test.com")
    assert client.get("/admin").status_code == 404

    monkeypatch.setenv("ADMIN_EMAILS", "a@test.com")
    assert client.get("/admin").status_code == 200


def test_admin_add_role_group_skill_and_use_it(client, test_db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "a@test.com")
    login(client, USER_A)

    client.post("/admin/roles", data={"role_name": "Rust Developer"})
    role = one(test_db, "SELECT role_id FROM job_roles WHERE role_name = 'Rust Developer'")

    client.post("/admin/groups", data={"role_id": str(role["role_id"]), "group_name": "Rust Core", "group_type": "common"})
    group = one(test_db, "SELECT group_id FROM role_skill_groups WHERE group_name = 'Rust Core'")

    client.post("/admin/skills", data={"group_id": str(group["group_id"]), "skill_name": "Rust", "importance": "core", "weight": "5"})
    client.post("/admin/skills", data={"group_id": str(group["group_id"]), "skill_name": "Tokio", "importance": "bogus", "weight": "5"})

    assert one(test_db, "SELECT COUNT(*) AS n FROM job_role_skills WHERE group_id = %s", (group["group_id"],))["n"] == 1

    # The new skill is recognised immediately
    from resume_parser.skill_extractor import extract_skills
    assert "Rust" in extract_skills("Systems tools written in Rust")


def test_admin_cannot_delete_used_role(client, test_db, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "a@test.com")
    login(client, USER_A)

    from conftest import make_pdf
    import io

    client.post("/job-match", data={"mode": "role", "role_id": "1", "resume": (io.BytesIO(make_pdf(PYTHON_FRESHER)), "r.pdf")},
                content_type="multipart/form-data")

    response = client.post("/admin/roles/1/delete", follow_redirects=True)

    assert b"cannot be deleted" in response.data
    assert one(test_db, "SELECT 1 AS x FROM job_roles WHERE role_id = 1")
