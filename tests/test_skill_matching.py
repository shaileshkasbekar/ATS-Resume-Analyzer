from resume_parser.skill_extractor import (
    extract_skills,
    skill_in_text,
    canonical_skill,
    is_known_skill
)
from resume_parser.job_matcher import ResumeView, match_option

from conftest import PYTHON_FRESHER, JAVA_DEVELOPER, NO_SECTIONS


# ---------------- Exact / case / aliases ----------------

def test_case_insensitive():
    assert skill_in_text("I write PYTHON every day", "Python")


def test_aliases():
    assert skill_in_text("Frontend in JS and ReactJS", "JavaScript")
    assert skill_in_text("Frontend in JS and ReactJS", "React")
    assert skill_in_text("Deployed on Amazon Web Services", "AWS")
    assert skill_in_text("Database: Postgres", "PostgreSQL")


def test_canonical_names():
    assert canonical_skill("ReactJS") == "React"
    assert canonical_skill("amazon web services") == "AWS"
    assert canonical_skill("Some Unknown Tool") == "Some Unknown Tool"
    assert is_known_skill("CI/CD")
    assert not is_known_skill("Hibernate/JPA")


# ---------------- No false matches ----------------

def test_java_is_not_javascript():
    assert not skill_in_text("Skills: JavaScript", "Java")


def test_sql_is_not_mysql_and_c_is_not_cpp():
    assert not skill_in_text("Databases: MySQL", "SQL")
    assert not skill_in_text("Languages: C++", "C")


def test_related_technologies_are_not_interchangeable():
    assert not skill_in_text("Built the backend with Flask", "Django")
    assert not skill_in_text("Stored data in MySQL", "MongoDB")


def test_no_duplicates():
    skills = extract_skills("Python, python, PYTHON and Python3 and python")
    assert skills.count("Python") == 1


# ---------------- Match type and evidence ----------------

def test_exact_vs_alias_match_type():
    resume = ResumeView("SKILLS\nJS, Python\nPROJECTS\nBuilt a tool in Python and JS for 50 users")
    assert match_option(resume, "Python")["match_type"] == "exact"
    assert match_option(resume, "JavaScript")["match_type"] == "alias"


def test_evidence_levels():
    resume = ResumeView(PYTHON_FRESHER)

    assert match_option(resume, "Flask")["evidence"] == "project"
    assert match_option(resume, "Git")["evidence"] == "listed"
    assert match_option(resume, "Django") is None


def test_experience_evidence_and_snippet():
    resume = ResumeView(JAVA_DEVELOPER)

    match = match_option(resume, "Spring Boot")

    assert match["evidence"] == "experience"
    assert "Spring Boot" in match["snippet"]


def test_framework_proves_language():
    resume = ResumeView("SKILLS\nJava\nPROJECTS\nShop API | Spring Boot, MySQL\n- Built REST endpoints")

    match = match_option(resume, "Java")

    assert match["evidence"] == "project"
    assert match["evidence_via"] == "Spring Boot"


def test_listed_only_gets_partial_credit():
    resume = ResumeView(PYTHON_FRESHER)
    assert match_option(resume, "Flask")["credit"] == 1.0
    assert 0 < match_option(resume, "Git")["credit"] < 1.0


def test_resume_without_sections():
    resume = ResumeView(NO_SECTIONS)
    assert match_option(resume, "Django")["evidence"] == "unknown"
