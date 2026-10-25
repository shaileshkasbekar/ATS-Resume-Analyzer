from resume_parser.job_requirements import (
    parse_requirements_rules,
    extract_requirements,
    role_requirements
)

from conftest import PYTHON_JD, JAVA_JD, PYTHON_FRESHER


def names(items):
    return [item["name"] for item in items]


# ---------------- Rule-based parsing ----------------

def test_mandatory_and_preferred_by_heading():
    result = parse_requirements_rules(PYTHON_JD)

    assert "Python" in names(result["mandatory_skills"])
    assert "Docker" in names(result["preferred_skills"])
    assert "AWS" in names(result["preferred_skills"])
    assert "Docker" not in names(result["mandatory_skills"])


def test_alternatives_are_one_requirement():
    result = parse_requirements_rules(PYTHON_JD)

    assert "Flask or Django" in names(result["mandatory_skills"])
    assert "MySQL or PostgreSQL" in names(result["mandatory_skills"])


def test_such_as_list_is_one_requirement():
    result = parse_requirements_rules("Requirements:\n- A framework such as React, Angular or Vue")
    assert names(result["mandatory_skills"]) == ["React or Angular or Vue"]


def test_comma_list_is_separate_requirements():
    result = parse_requirements_rules("Requirements:\n- Java, Spring Boot, MySQL")
    assert names(result["mandatory_skills"]) == ["Java", "Spring Boot", "MySQL"]


def test_preferred_marker_only_affects_its_sentence():
    result = parse_requirements_rules(JAVA_JD)

    assert "Kafka" in names(result["preferred_skills"])
    assert "Java" in names(result["mandatory_skills"])


def test_experience_years():
    assert parse_requirements_rules(JAVA_JD)["experience"]["min_years"] == 3.0
    assert parse_requirements_rules(PYTHON_JD)["experience"]["min_years"] == 0.0
    assert parse_requirements_rules("Requirements:\n- Python")["experience"]["min_years"] is None


def test_education_and_soft_skills():
    result = parse_requirements_rules(PYTHON_JD)

    assert result["education_required_level"] == 1
    assert "communication" in result["soft_skills"]


def test_certifications_required_vs_preferred():
    result = parse_requirements_rules("Requirements:\n- AWS Certified Developer certification required\nNice to have:\n- Azure certification")

    assert result["certifications_required"]
    assert result["certifications_preferred"]


def test_responsibilities():
    result = parse_requirements_rules(PYTHON_JD)
    assert "Build and maintain REST APIs for our payments platform" in result["responsibilities"]


def test_duplicates_merged():
    result = parse_requirements_rules("Requirements:\n- Python\n- Strong Python skills\n- python scripting")
    assert names(result["mandatory_skills"]).count("Python") == 1


# ---------------- AI extraction is validated ----------------

def test_ai_cannot_add_requirements_not_in_the_jd(fake_ai):
    fake_ai({
        "mandatory_skills": ["Python", "Kubernetes", "MySQL or Oracle"],
        "preferred_skills": ["Docker"],
        "responsibilities": ["Lead a team of 50 engineers"],
        "job_title": "Junior Backend Developer"
    })

    result = extract_requirements(PYTHON_JD)

    all_skills = [s for item in result["mandatory_skills"] + result["preferred_skills"] for s in item["any_of"]]

    assert "Kubernetes" not in all_skills
    assert "Oracle" not in all_skills
    assert "Lead a team of 50 engineers" not in result["responsibilities"]
    assert result["source"] == "ai+rules"


def test_mandatory_wins_over_preferred(fake_ai):
    fake_ai({"mandatory_skills": ["Docker"], "preferred_skills": []})

    result = extract_requirements(PYTHON_JD)

    assert "Docker" in names(result["mandatory_skills"])
    assert "Docker" not in names(result["preferred_skills"])


def test_malformed_ai_output_falls_back_to_rules(fake_ai):
    fake_ai({"mandatory_skills": "Python", "preferred_skills": [1, None, {"x": 1}], "job_title": 42})

    result = extract_requirements(PYTHON_JD)

    assert "Python" in names(result["mandatory_skills"])


def test_ai_unavailable(no_ai):
    result = extract_requirements(PYTHON_JD)

    assert result["source"] == "rules"
    assert result["mandatory_skills"]


# ---------------- Predefined roles ----------------

BACKEND_ROLE = [
    {"group_name": "Common", "group_type": "common", "skill_name": "SQL", "importance": "core", "weight": 4},
    {"group_name": "Common", "group_type": "common", "skill_name": "Docker", "importance": "optional", "weight": 1},
    {"group_name": "Python Backend", "group_type": "technology", "skill_name": "Python", "importance": "core", "weight": 5},
    {"group_name": "Python Backend", "group_type": "technology", "skill_name": "Flask", "importance": "supporting", "weight": 3},
    {"group_name": "Java Backend", "group_type": "technology", "skill_name": "Java", "importance": "core", "weight": 5},
    {"group_name": "Java Backend", "group_type": "technology", "skill_name": "Spring Boot", "importance": "supporting", "weight": 3},
]


def test_role_uses_candidates_path():
    result = role_requirements("Backend Developer", BACKEND_ROLE, PYTHON_FRESHER)

    all_skills = [s for item in result["mandatory_skills"] + result["preferred_skills"] for s in item["any_of"]]

    assert result["detected_path"] == "Python Backend"
    assert "Python" in all_skills
    assert "Java" not in all_skills
    assert "Spring Boot" not in all_skills


def test_role_without_path_needs_any_one():
    result = role_requirements("Backend Developer", BACKEND_ROLE, "SKILLS\nSQL")

    assert "Python or Java" in names(result["mandatory_skills"])
