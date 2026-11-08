"""
Quality guard: the Job Match engine must keep its accuracy on the
hand-labelled evaluation cases (evaluation/cases.py).
"""

import re

import mysql.connector

from config import Config
from evaluation.evaluate import evaluate


def test_engine_accuracy_on_labelled_cases(no_ai):
    metrics, rows, mistakes = evaluate()

    assert metrics["cases"] >= 8
    assert metrics["requirement_precision"] >= 0.95, mistakes
    assert metrics["requirement_recall"] >= 0.95, mistakes
    assert metrics["match_accuracy"] >= 0.95, mistakes
    assert metrics["evidence_accuracy"] >= 0.90, mistakes


def test_every_role_skill_is_known_to_the_job_reader(test_db):
    """
    A skill used by a predefined role must also be recognised in job
    descriptions; otherwise postings asking for it lose that requirement.
    """

    connection = mysql.connector.connect(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER,
                                         password=Config.MYSQL_PASSWORD, database=test_db)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT skill_name FROM job_role_skills")
        role_skills = [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()

    source = open("resume_parser/skill_extractor.py", encoding="utf-8").read()
    block = source[source.index("skills_database = ["):source.index("]", source.index("skills_database = ["))]
    built_in = {name.lower() for name in re.findall(r'"([^"]+)"', block)}

    missing = [s for s in role_skills if s.lower() not in built_in]

    assert not missing, f"Add these to skills_database in skill_extractor.py: {missing}"
