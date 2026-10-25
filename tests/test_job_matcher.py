from datetime import date

import pytest

from resume_parser.job_requirements import extract_requirements
from resume_parser.job_matcher import run_job_match, estimate_experience_years
from resume_parser.jd_analyzer import analyze_job_match

from conftest import PYTHON_FRESHER, JAVA_DEVELOPER, PYTHON_JD, JAVA_JD


def match(resume, jd):
    return analyze_job_match(resume, jd, use_ai=False)


def component(result, key):
    return next(c for c in result["components"] if c["key"] == key)


# ---------------- Strong / weak / unrelated ----------------

def test_strong_match_scores_high():
    result = match(PYTHON_FRESHER, PYTHON_JD)
    assert result["score"] >= 70


def test_unrelated_stack_scores_low():
    result = match(PYTHON_FRESHER, JAVA_JD)
    assert result["score"] < 30


def test_java_developer_on_java_job():
    result = match(JAVA_DEVELOPER, JAVA_JD)

    assert result["score"] >= 75
    assert all(m["status"] == "matched" for m in result["mandatory"])


def test_python_developer_not_penalized_for_java():
    result = match(PYTHON_FRESHER, PYTHON_JD)

    required = [s.lower() for m in result["mandatory"] + result["preferred"] for s in m["any_of"]]

    assert "java" not in required
    assert "spring boot" not in required


def test_alternative_requirement_satisfied_by_one_option():
    result = match(PYTHON_FRESHER, PYTHON_JD)

    flask_or_django = next(m for m in result["mandatory"] if m["requirement"] == "Flask or Django")

    assert flask_or_django["status"] == "matched"
    assert flask_or_django["matched_skill"] == "Flask"


# ---------------- Experience ----------------

def test_fresher_on_entry_level_job():
    result = match(PYTHON_FRESHER, PYTHON_JD)
    assert component(result, "experience")["score"] == 100


def test_fresher_on_senior_job():
    result = match(PYTHON_FRESHER, JAVA_JD)
    assert component(result, "experience")["score"] == 0


def test_estimate_experience_years():
    today = date(2026, 1, 1)

    assert estimate_experience_years("Engineer | Jan 2021 - Dec 2023", today) == pytest.approx(2.9, abs=0.1)
    assert estimate_experience_years("Intern | Jun 2025 - Present", today) == pytest.approx(0.6, abs=0.1)
    assert estimate_experience_years("No dates here", today) is None


# ---------------- Scoring consistency ----------------

def test_scores_are_normalized():
    for resume in (PYTHON_FRESHER, JAVA_DEVELOPER, "", "x"):
        for jd in (PYTHON_JD, JAVA_JD):

            result = match(resume, jd)

            assert 0 <= result["score"] <= 100

            applicable = [c for c in result["components"] if c["applicable"]]

            assert sum(c["max_points"] for c in applicable) == pytest.approx(100, abs=0.5)
            assert result["score"] == pytest.approx(sum(c["points"] for c in applicable), abs=0.5)


def test_components_that_do_not_apply_are_skipped():
    result = match(JAVA_DEVELOPER, JAVA_JD)

    assert component(result, "qualifications")["applicable"] is False
    assert component(result, "semantic_relevance")["applicable"] is False


def test_each_skill_counted_once():
    jd = "Requirements:\n- Python\n- Python\n- Strong Python\n- Docker"
    result = match(PYTHON_FRESHER, jd)

    assert [m["requirement"] for m in result["mandatory"]].count("Python") == 1


def test_missing_requirements_explained():
    result = match(PYTHON_FRESHER, PYTHON_JD)

    linux = next(m for m in result["mandatory"] if m["requirement"] == "Linux")

    assert linux["status"] == "missing"
    assert linux["points_lost"] > 0
    assert any(a["requirement"] == "Linux" for a in result["actions"])
    assert result["deductions"]


def test_scoring_version_saved():
    assert match(PYTHON_FRESHER, PYTHON_JD)["scoring_version"].startswith("jm-")


# ---------------- AI assessment validation ----------------

def ai_assessment(**overrides):

    answer = {
        "semantic_matches": [],
        "overall_relevance": {"score": 80, "reason": "Good backend fit."},
        "experience": {"score": 70, "reason": "Projects only."},
        "projects": {"score": 85, "reason": "Relevant API project.", "relevant_projects": []},
        "strengths": [],
        "improvements": []
    }

    answer.update(overrides)

    return answer


def test_semantic_match_needs_real_quote(fake_ai):
    fake_ai(
        None,
        ai_assessment(semantic_matches=[
            {"requirement": "Linux", "evidence_quote": "Administered 40 Ubuntu servers", "reason": "Ubuntu is Linux"}
        ])
    )

    result = analyze_job_match(PYTHON_FRESHER, PYTHON_JD)

    linux = next(m for m in result["mandatory"] if m["requirement"] == "Linux")

    assert linux["status"] == "missing"


def test_valid_semantic_match_gets_partial_credit(fake_ai):
    resume = PYTHON_FRESHER + "- Deployed the API on an Ubuntu server with Nginx\n"

    fake_ai(
        None,
        ai_assessment(semantic_matches=[
            {"requirement": "Linux", "evidence_quote": "Deployed the API on an Ubuntu server", "reason": "Ubuntu is a Linux distribution"}
        ])
    )

    result = analyze_job_match(resume, PYTHON_JD)

    linux = next(m for m in result["mandatory"] if m["requirement"] == "Linux")

    assert linux["status"] == "matched"
    assert linux["match_type"] == "semantic"
    assert 0 < linux["credit"] < 1


def test_semantic_match_cannot_override_existing_match(fake_ai):
    fake_ai(None, ai_assessment(semantic_matches=[
        {"requirement": "Docker", "evidence_quote": "deployed the app with Docker", "reason": "x"}
    ]))

    result = analyze_job_match(PYTHON_FRESHER, PYTHON_JD)

    docker = next(m for m in result["preferred"] if m["requirement"] == "Docker")

    assert docker["match_type"] == "exact"


def test_malformed_ai_assessment(fake_ai):
    fake_ai(None, {
        "semantic_matches": "Linux",
        "overall_relevance": {"score": "abc"},
        "experience": {"score": 150},
        "projects": [],
        "strengths": [{"text": "Great at Kubernetes", "evidence_quote": "Ran Kubernetes clusters"}],
        "improvements": ["not a dict"]
    })

    result = analyze_job_match(PYTHON_FRESHER, PYTHON_JD)

    assert 0 <= result["score"] <= 100
    assert component(result, "experience")["score"] <= 100
    assert not any("Kubernetes" in s["text"] for s in result["strengths"])


def test_ai_failure_still_gives_a_result(no_ai):
    result = analyze_job_match(PYTHON_FRESHER, PYTHON_JD)

    assert result["ai_available"] is False
    assert component(result, "semantic_relevance")["applicable"] is False
    assert 0 < result["score"] <= 100
