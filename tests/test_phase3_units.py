"""
Phase 3: version comparison, multiple jobs, roadmap, projects, interview.
"""

from resume_parser.career import (
    answer_feedback,
    build_roadmap,
    existing_projects,
    interview_questions,
    recommend_projects
)
from resume_parser.jd_analyzer import analyze_job_match
from resume_parser.job_requirements import extract_requirements
from resume_parser.multi_job import compare_jobs
from resume_parser.version_compare import compare_versions

import resume_parser.career as career_module

from conftest import PYTHON_FRESHER, PYTHON_JD, JAVA_JD


V2 = PYTHON_FRESHER.replace(
    "- Wrote unit tests with Pytest and deployed the app with Docker",
    "- Wrote unit tests with Pytest and deployed the app with Docker on a Linux server"
)


# ---------------- Version comparison ----------------

def test_version_comparison_explains_score_change(no_ai):
    c = compare_versions(PYTHON_FRESHER, V2, extract_requirements(PYTHON_JD))

    assert c["skills_added"] == ["Linux"]
    assert c["job"]["b"] > c["job"]["a"]

    linux = next(ch for ch in c["job"]["changes"] if ch["requirement"] == "Linux")

    assert linux["before"] == "missing"
    assert linux["after"] == "found in a project"
    assert linux["points"] > 0
    assert any(s["key"] == "projects" for s in c["section_changes"])


def test_identical_versions_have_no_changes(no_ai):
    c = compare_versions(PYTHON_FRESHER, PYTHON_FRESHER, extract_requirements(PYTHON_JD))

    assert c["job"]["delta"] == 0
    assert c["job"]["changes"] == []
    assert c["skills_added"] == c["skills_removed"] == []


def test_comparison_without_job():
    assert compare_versions(PYTHON_FRESHER, V2)["job"] is None


# ---------------- Multiple jobs ----------------

def test_compare_jobs(no_ai):
    jobs = [
        {"job_id": 1, "title": "Python Dev", "company": "A", "requirements": extract_requirements(PYTHON_JD)},
        {"job_id": 2, "title": "Java Dev", "company": "B", "requirements": extract_requirements(JAVA_JD)},
        {"job_id": 3, "title": "Python Dev 2", "company": "C", "requirements": extract_requirements(PYTHON_JD)},
    ]

    c = compare_jobs(PYTHON_FRESHER, jobs)

    assert c["rows"][0]["title"].startswith("Python")
    assert c["rows"][-1]["title"] == "Java Dev"
    assert "Python" in c["common_skills"]
    assert "Linux" in c["shared_gaps"]
    assert "Java" in next(r for r in c["rows"] if r["title"] == "Java Dev")["unique_skills"]


# ---------------- Roadmap ----------------

def result_for(resume=PYTHON_FRESHER, jd=PYTHON_JD):
    return analyze_job_match(resume, jd, use_ai=False)


def test_roadmap_required_first_without_ai():
    items, used_ai = build_roadmap(result_for(), PYTHON_FRESHER, use_ai=False)

    assert used_ai is False
    assert items[0]["skill"] == "Linux"
    assert items[0]["priority"] == "high"
    assert [i["priority"] for i in items] == sorted([i["priority"] for i in items], key=["high", "medium", "low"].index)
    assert all(i["objectives"] and i["exercises"] and i["demonstrate"] for i in items)


def test_roadmap_ai_output_validated(monkeypatch):
    monkeypatch.setattr(career_module, "ask_ai_for_json", lambda s, p: {
        "items": [{"skill": "Linux", "why": "Servers run Linux.", "objectives": "not a list", "exercises": ["Install Ubuntu"]}]
    })

    items, used_ai = build_roadmap(result_for(), PYTHON_FRESHER)

    linux = items[0]

    assert used_ai is True
    assert linux["why"] == "Servers run Linux."
    assert linux["exercises"] == ["Install Ubuntu"]
    assert isinstance(linux["objectives"], list) and linux["objectives"]


# ---------------- Projects ----------------

def test_existing_projects_detected():
    assert existing_projects(PYTHON_FRESHER) == ["Expense Tracker API", "Library Portal"]


def test_projects_fallback():
    ideas, used_ai = recommend_projects(result_for(), PYTHON_FRESHER, use_ai=False)

    assert not used_ai and ideas
    assert all(i["title"] and i["features"] for i in ideas)


def test_projects_ai_validated(monkeypatch):
    monkeypatch.setattr(career_module, "ask_ai_for_json", lambda s, p: {"projects": [
        {"title": "Expense Tracker API", "objective": "copy", "stack": ["Python"]},
        {"title": "Deploy tracker on Linux", "extends": "Expense Tracker API", "stack": ["Linux", "Rust", "Docker"],
         "features": ["CI"], "objective": "Show Linux"},
    ]})

    ideas, used_ai = recommend_projects(result_for(), PYTHON_FRESHER)

    assert used_ai is True
    assert len(ideas) == 1
    assert ideas[0]["extends"] == "Expense Tracker API"
    assert "Rust" not in ideas[0]["stack"]


# ---------------- Interview ----------------

def test_interview_fallback_questions():
    questions, used_ai = interview_questions(result_for(), PYTHON_FRESHER, use_ai=False)

    categories = {q["category"] for q in questions}

    assert not used_ai
    assert {"skill", "project", "behavioral", "hr"} <= categories
    assert all(q["suggested_answer"] for q in questions)


def test_feedback_without_ai():
    feedback = answer_feedback("Explain how you used Flask.", "In my project I built a Flask REST API for 200 students with MySQL.", PYTHON_FRESHER, use_ai=False)

    assert feedback["basic"] is True
    assert feedback["scores"]["examples"] >= 80
    assert feedback["scores"]["correctness"] is None


def test_feedback_ai_scores_clamped(monkeypatch):
    monkeypatch.setattr(career_module, "ask_ai_for_json", lambda s, p: {
        "scores": {"relevance": 150, "correctness": "abc", "clarity": 70, "completeness": -3, "examples": 50},
        "feedback": "Good.", "improved_answer": "Better."
    })

    feedback = answer_feedback("Q?", "An answer that is long enough.", PYTHON_FRESHER)

    assert feedback["scores"]["relevance"] == 100
    assert feedback["scores"]["correctness"] is None
    assert feedback["scores"]["completeness"] == 0
