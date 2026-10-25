"""
Shared test setup.

- AI calls are replaced by fakes (fast, repeatable, no API key needed).
- Route tests use a throwaway MySQL database that is created from
  database/*.sql before the tests and dropped afterwards. Your real
  database is never touched. If MySQL is not reachable those tests
  are skipped.
"""

import os
import sys
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, ROOT)
os.chdir(ROOT)

os.environ.setdefault("SECRET_KEY", "test-secret-key")


# =========================================
# Sample documents
# =========================================

PYTHON_FRESHER = """Riya Sharma
riya@example.com | +91 98765 43210 | linkedin.com/in/riya | github.com/riya

SUMMARY
Final-year Computer Science student building backend applications with Python.

EDUCATION
B.Tech in Computer Science, ABC Institute of Technology, 2022 - 2026

TECHNICAL SKILLS
Languages: Python, SQL, JavaScript
Frameworks: Flask, REST APIs
Databases: MySQL
Tools: Git, Docker

PROJECTS
Expense Tracker API | Python, Flask, MySQL
- Built a REST API with Flask and MySQL used by 200+ students
- Wrote unit tests with Pytest and deployed the app with Docker
Library Portal | JavaScript, HTML, CSS
- Developed a responsive frontend for searching 5,000 books
"""

JAVA_DEVELOPER = """Arjun Patil
arjun@example.com | 9876543210

EXPERIENCE
Software Engineer, XYZ Systems | Jan 2021 - Dec 2023
- Developed microservices with Spring Boot and Hibernate for a payments platform
- Optimized MySQL queries, reducing response time by 35%

SKILLS
Java, Spring Boot, Hibernate, MySQL, Kafka, Git

EDUCATION
B.E. in Information Technology, 2016 - 2020
"""

NO_SECTIONS = """Sam Lee sam@example.com
I know Python and Django and have used PostgreSQL for a few apps.
"""

PYTHON_JD = """Junior Backend Developer
Responsibilities:
- Build and maintain REST APIs for our payments platform
- Write unit tests and take part in code reviews
Requirements:
- 0-2 years of experience, freshers welcome
- Strong Python and Flask or Django
- Experience with MySQL or PostgreSQL
- Git and Linux
- B.Tech in Computer Science or a related degree
- Good communication skills
Nice to have:
- Docker, AWS
"""

JAVA_JD = """Senior Java Developer
Requirements:
- 3+ years of experience building backend systems
- Java, Spring Boot, Hibernate and Microservices
- Kafka is a plus.
"""


@pytest.fixture
def no_ai(monkeypatch):
    """
    Every AI call returns None (as if the AI service is down).
    """

    import resume_parser.ai_client as ai_client

    monkeypatch.setattr(ai_client, "client", None)


@pytest.fixture
def fake_ai(monkeypatch):
    """
    fake_ai(answers): AI calls return the given answers in order.
    """

    import resume_parser.job_requirements as job_requirements
    import resume_parser.job_matcher as job_matcher

    def install(*answers):

        queue = list(answers)

        def fake(system_message, prompt):
            return queue.pop(0) if queue else None

        monkeypatch.setattr(job_requirements, "ask_ai_for_json", fake)
        monkeypatch.setattr(job_matcher, "ask_ai_for_json", fake)

    return install


def make_pdf(text):
    """
    A real text-based PDF with the given text.
    """

    import fitz

    document = fitz.open()
    page = document.new_page()

    y = 50

    for line in text.splitlines():
        page.insert_text((40, y), line, fontsize=9)
        y += 12

    data = document.tobytes()
    document.close()

    return data


# =========================================
# Throwaway test database
# =========================================

@pytest.fixture(scope="session")
def test_db():

    import mysql.connector

    from config import Config

    sys.path.insert(0, os.path.join(ROOT, "database"))

    from run_sql import split_statements

    name = "ats_test_" + uuid.uuid4().hex[:8]

    try:
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST, user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD
        )
    except mysql.connector.Error:
        pytest.skip("MySQL is not reachable")

    cursor = connection.cursor()

    try:

        cursor.execute(f"CREATE DATABASE {name}")

        for path in ["database/schema.sql", "database/upgrade_v3.sql", "database/upgrade_v4.sql", "database/upgrade_v5.sql"]:

            sql = open(path, encoding="utf-8").read().replace("ats_resume_analyzer_v2", name)

            for statement in split_statements(sql):
                cursor.execute(statement)

        cursor.execute(f"USE {name}")
        cursor.execute("INSERT INTO users (full_name, email, password) VALUES ('User A', 'a@test.com', 'x'), ('User B', 'b@test.com', 'x')")
        connection.commit()

        yield name

    finally:

        cursor.execute(f"DROP DATABASE IF EXISTS {name}")
        connection.close()


@pytest.fixture
def client(test_db, monkeypatch, tmp_path, no_ai):
    """
    Flask test client using the test database and a temp upload folder.
    """

    from config import Config

    monkeypatch.setattr(Config, "MYSQL_DATABASE", test_db)
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))

    from app import app
    from security import reset_rate_limits

    app.config["TESTING"] = True

    # Most tests post forms directly; CSRF itself is tested in test_security.py

    app.config["CSRF_ENABLED"] = False

    reset_rate_limits()

    yield app.test_client()

    app.config["CSRF_ENABLED"] = True


def login(client, user_id, name="Test"):

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["fullname"] = name
