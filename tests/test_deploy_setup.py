"""
Online deployment: MYSQL_URL settings and automatic database setup.
"""

import uuid

import mysql.connector
import pytest


def test_mysql_url_is_split_into_settings(monkeypatch):
    from config import _mysql_from_url

    monkeypatch.setenv("MYSQL_URL", "mysql://root:p%40ss@db.example.com:12345/railway")

    assert _mysql_from_url() == {"MYSQL_HOST": "db.example.com", "MYSQL_PORT": "12345", "MYSQL_USER": "root",
                                 "MYSQL_PASSWORD": "p@ss", "MYSQL_DATABASE": "railway"}

    monkeypatch.setenv("MYSQL_URL", "")
    assert _mysql_from_url() == {}


def test_setup_creates_fresh_database_and_is_safe_to_rerun(monkeypatch):
    from config import Config
    from database import setup

    name = "ats_test_setup_" + uuid.uuid4().hex[:8]

    try:
        admin = mysql.connector.connect(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT,
                                        user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD)
    except mysql.connector.Error:
        pytest.skip("MySQL is not reachable")

    monkeypatch.setattr(Config, "MYSQL_DATABASE", name)

    try:
        setup.run(log=lambda *_: None)
        setup.run(log=lambda *_: None)   # second start: nothing applied twice

        cursor = admin.cursor()
        cursor.execute(f"USE `{name}`")
        cursor.execute("SELECT COUNT(*) FROM schema_files")
        assert cursor.fetchone()[0] == len(setup.FILES)

        cursor.execute("SELECT COUNT(*) FROM job_roles")
        roles = cursor.fetchone()[0]
        assert roles >= 11

        cursor.execute("SHOW COLUMNS FROM jd_results LIKE 'share_token'")
        assert cursor.fetchone() is not None

        # No duplicate roles after the rerun
        cursor.execute("SELECT COUNT(DISTINCT role_name) FROM job_roles")
        assert cursor.fetchone()[0] == roles
    finally:
        admin.cursor().execute(f"DROP DATABASE IF EXISTS `{name}`")
        admin.close()
