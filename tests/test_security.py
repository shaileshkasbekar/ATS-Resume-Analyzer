"""
Phase 4: security checks on the running app.
"""

import re

from conftest import login


def token_from(page):
    return re.search(rb'name="csrf_token" value="([0-9a-f]+)"', page).group(1).decode()


def test_post_without_csrf_token_is_rejected(client, test_db):
    from app import app

    app.config["CSRF_ENABLED"] = True

    response = client.post("/login", data={"email": "a@test.com", "password": "x"})

    assert response.status_code == 302
    assert "/dashboard" not in response.headers["Location"]


def test_json_post_without_csrf_token_is_400(client):
    from app import app

    app.config["CSRF_ENABLED"] = True

    login(client, 1)

    response = client.post("/roadmap/item/1", json={"done": True})

    assert response.status_code == 400


def test_post_with_csrf_token_works(client, test_db):
    from app import app

    app.config["CSRF_ENABLED"] = True

    token = token_from(client.get("/login").data)

    response = client.post("/login", data={"email": "nobody@test.com", "password": "wrong", "csrf_token": token}, follow_redirects=True)

    assert b"Invalid Email or Password" in response.data


def test_login_rate_limit(client, test_db):
    for _ in range(10):
        client.post("/login", data={"email": "x@test.com", "password": "bad"})

    response = client.post("/login", data={"email": "x@test.com", "password": "bad"}, follow_redirects=True)

    assert b"Too many requests" in response.data


def test_register_password_policy(client, test_db):
    response = client.post("/register", data={"fullname": "New User", "email": "new@test.com", "password": "short"}, follow_redirects=True)
    assert b"at least 8 characters" in response.data


def test_register_and_login(client, test_db):
    client.post("/register", data={"fullname": "Real User", "email": "Real@Test.com", "password": "longpassword1"})

    response = client.post("/login", data={"email": "real@test.com", "password": "longpassword1"})

    assert response.headers["Location"].endswith("/dashboard")


def test_old_uploads_are_not_public(client):
    assert client.get("/static/uploads/any_resume.pdf").status_code == 404


def test_security_headers(client):
    response = client.get("/login")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"


def test_session_cookie_flags():
    from app import app

    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_protected_pages_require_login(client):
    for path in ["/dashboard", "/resumes", "/jobs", "/roadmap", "/history", "/assistant/1", "/report/jd/1.pdf"]:
        response = client.get(path)
        assert response.status_code == 302, path
        assert "/login" in response.headers["Location"]
