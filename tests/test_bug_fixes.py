"""
Regression tests for bugs found by checking real results:

1. a skill listed as both matched and missing (AI said "missing", rules found "K8s")
2. an AI technology path that is not one of the role's paths
3. duplicate skills from AI names (HTML5 / HTML, REST APIs / REST API)
4. MySQL reported missing when the resume uses PostgreSQL
"""

import io

import mysql.connector

from config import Config
from conftest import make_pdf, login
from resume_parser.ats_score import calculate_ats_score
from resume_parser.job_requirements import role_requirements


RESUME = """Aditya Raut
aditya@example.com | +91 98765 43210
EXPERIENCE
Web Lead, Pragyaa | Oct 2025 - Mar 2026
- Deployed services on Kubernetes (K8s) and Docker with GitHub Actions CI/CD on Linux
- Built HTML5 and CSS3 pages with JavaScript and REST APIs
PROJECTS
Job Scheduler | Go, PostgreSQL, Redis
- Built a scheduler with PostgreSQL and REST APIs
SKILLS
Go, JavaScript, SQL, PostgreSQL, Docker, Kubernetes, Linux, Git
EDUCATION
B.Tech in Computer Science, 2023 - 2027
"""

DB_GROUP = [
    {"group_name": "Database", "group_type": "common", "skill_name": "SQL", "importance": "core", "weight": 4},
    {"group_name": "Database", "group_type": "common", "skill_name": "MySQL", "importance": "supporting", "weight": 2},
    {"group_name": "Database", "group_type": "common", "skill_name": "PostgreSQL", "importance": "supporting", "weight": 2},
]


# ---------------- 4. Alternatives ----------------

def test_postgresql_satisfies_mysql_in_role_score():
    score, matched, missing, recommended, groups, path = calculate_ats_score(["sql", "postgresql"], DB_GROUP)

    assert "MySQL" not in missing
    assert "MySQL (via PostgreSQL)" in matched
    assert not any("MySQL" in r for r in recommended)
    assert score == 100


def test_alternative_only_counts_inside_same_group():
    groups = [
        {"group_name": "Database", "group_type": "common", "skill_name": "MySQL", "importance": "supporting", "weight": 2},
        {"group_name": "Other", "group_type": "common", "skill_name": "PostgreSQL", "importance": "supporting", "weight": 2},
    ]

    missing = calculate_ats_score(["postgresql"], groups)[2]

    assert "MySQL" in missing


def test_role_requirements_group_alternatives():
    requirements = role_requirements("Backend", DB_GROUP, RESUME)

    names = [item["name"] for item in requirements["mandatory_skills"]]

    assert "MySQL or PostgreSQL" in names
    assert "MySQL" not in names


# ---------------- 1-3. Role check now uses the Job Match engine ----------------

def test_old_role_check_address_forwards_to_job_match(client, test_db):
    login(client, 1)

    response = client.post("/upload", data={"role_id": "6"})

    assert response.status_code == 307
    assert response.headers["Location"].endswith("/job-match")


def test_role_check_form_gives_consistent_result(client, test_db):
    login(client, 1)

    connection = mysql.connector.connect(host=Config.MYSQL_HOST, user=Config.MYSQL_USER,
                                         password=Config.MYSQL_PASSWORD, database=test_db)
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT role_id FROM job_roles WHERE role_name = 'DevOps Engineer'")
        role_id = cursor.fetchone()["role_id"]
    finally:
        connection.close()

    # Exactly what the ATS Role Check page sends

    response = client.post("/job-match", data={
        "mode": "role", "role_id": str(role_id),
        "resume": (io.BytesIO(make_pdf(RESUME)), "r.pdf")
    }, content_type="multipart/form-data")

    assert response.status_code == 200

    connection = mysql.connector.connect(host=Config.MYSQL_HOST, user=Config.MYSQL_USER,
                                         password=Config.MYSQL_PASSWORD, database=test_db)
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM jd_results ORDER BY jd_result_id DESC LIMIT 1")
        row = cursor.fetchone()
    finally:
        connection.close()

    import json
    result = json.loads(row["details"])

    assert row["source_type"] == "role"

    requirements = result["mandatory"] + result["preferred"]
    matched = {m["requirement"].lower() for m in requirements if m["status"] == "matched"}
    missing = {m["requirement"].lower() for m in requirements if m["status"] == "missing"}

    assert "kubernetes" in matched            # "K8s" / "Kubernetes" in the resume
    assert not (matched & missing)            # never both
    assert len(requirements) == len({m["requirement"].lower() for m in requirements})  # no duplicates
