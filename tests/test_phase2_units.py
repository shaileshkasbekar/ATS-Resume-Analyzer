"""
Phase 2: improvement assistant validation, resume builder, PDF export.
"""

import fitz

from pdf_export import html_to_pdf, pdf_safe
from resume_parser.improvement import remove_invented_numbers, validate_suggestions, generate_suggestions
from resume_parser.jd_analyzer import analyze_job_match
from resume_parser.resume_builder import TEMPLATES, build_resume, to_items

from conftest import PYTHON_FRESHER, PYTHON_JD


# ---------------- Suggestion validation ----------------

def test_original_must_exist_in_resume():
    result = validate_suggestions([
        {"kind": "experience", "original": "Led a team of 20 engineers at Google", "improved": "Led 20 engineers"},
    ], PYTHON_FRESHER)

    assert result == []


def test_rewrite_cannot_add_new_skills():
    result = validate_suggestions([
        {"kind": "project", "original": "Built a REST API with Flask and MySQL used by 200+ students",
         "improved": "Built a REST API with Flask, Kubernetes and MySQL used by 200+ students"},
    ], PYTHON_FRESHER)

    assert result == []


def test_bullet_cannot_borrow_skill_from_elsewhere_in_resume():
    # Docker is in the resume, but not in this project's line
    result = validate_suggestions([
        {"kind": "project", "original": "Developed a responsive frontend for searching 5,000 books",
         "improved": "Developed a responsive frontend for searching 5,000 books, deployed with Docker"},
    ], PYTHON_FRESHER)

    assert result == []


def test_summary_may_use_resume_skills():
    result = validate_suggestions([
        {"kind": "summary", "original": "", "improved": "Student building Python and Flask APIs with Docker."},
    ], PYTHON_FRESHER)

    assert len(result) == 1


def test_invented_numbers_replaced():
    result = validate_suggestions([
        {"kind": "project", "original": "Developed a responsive frontend for searching 5,000 books",
         "improved": "Developed a responsive frontend for searching 5,000 books, cutting search time by 60%"},
    ], PYTHON_FRESHER)

    assert len(result) == 1
    assert "5,000" in result[0]["improved"]
    assert "60" not in result[0]["improved"]
    assert "[add real number]" in result[0]["improved"]
    assert result[0]["needs_metric"] is True


def test_advice_may_mention_missing_skill():
    result = validate_suggestions([
        {"kind": "advice", "original": "", "improved": "If you used Linux to deploy, add a bullet about it."},
    ], PYTHON_FRESHER)

    assert len(result) == 1


def test_unverified_evidence_removed_and_duplicates_dropped():
    item = {"kind": "summary", "original": "", "improved": "Backend-focused student building Python APIs.",
            "evidence": "Worked at Microsoft"}

    result = validate_suggestions([item, dict(item)], PYTHON_FRESHER)

    assert len(result) == 1
    assert result[0]["evidence"] == ""


def test_numbers_inside_names_are_kept():
    text, needs_metric = remove_invented_numbers("Deployed on EC2 with Python3", "Deployed with Python3")
    assert text == "Deployed on EC2 with Python3"
    assert needs_metric is False


def test_rule_suggestions_without_ai(no_ai):
    resume = PYTHON_FRESHER + "- Responsible for testing the payment module\n"

    suggestions, used_ai = generate_suggestions(resume, analyze_job_match(resume, PYTHON_JD, use_ai=False))

    assert used_ai is False
    assert any("responsible for" in s["reason"].lower() for s in suggestions)


# ---------------- Resume builder ----------------

def test_wrapped_bullets_are_joined():
    items = to_items("- Built a REST API with Flask\nand MySQL for students\n- Wrote tests")

    assert [i["text"] for i in items] == ["Built a REST API with Flask and MySQL for students", "Wrote tests"]


def test_accepted_suggestion_replaces_original():
    doc = build_resume(PYTHON_FRESHER, [{
        "kind": "project",
        "original": "Built a REST API with Flask and MySQL used by 200+ students",
        "improved": "Designed and built a Flask + MySQL REST API used by 200+ students"
    }], "modern")

    text = " ".join(i["text"] for s in doc["sections"] for i in s["items"])

    assert "Designed and built a Flask + MySQL REST API" in text
    assert "Built a REST API with Flask and MySQL used by 200+ students" not in text
    assert doc["not_applied"] == []


def test_new_summary_and_not_applied():
    doc = build_resume(PYTHON_FRESHER, [
        {"kind": "summary", "original": "", "improved": "New summary text."},
        {"kind": "experience", "original": "Text that is not in the resume at all", "improved": "x"},
    ], "classic")

    summary = next(s for s in doc["sections"] if s["key"] == "summary")

    assert summary["items"][0]["text"] == "New summary text."
    assert len(doc["not_applied"]) == 1


def test_template_section_order():
    fresher = build_resume(PYTHON_FRESHER, [], "fresher")
    technical = build_resume(PYTHON_FRESHER, [], "technical")

    assert [s["key"] for s in fresher["sections"]][:2] == ["summary", "education"]
    assert [s["key"] for s in technical["sections"]][:2] == ["summary", "skills"]
    assert set(TEMPLATES) == {"classic", "modern", "technical", "fresher"}


def test_original_text_not_changed():
    original = PYTHON_FRESHER
    build_resume(original, [{"kind": "summary", "original": "", "improved": "x"}])
    assert original == PYTHON_FRESHER


# ---------------- PDF export ----------------

def test_pdf_has_selectable_text():
    data = html_to_pdf("<h1>Riya Sharma</h1><p class='li'>- Built a REST API • fast — reliable</p>")

    document = fitz.open(stream=data, filetype="pdf")
    text = document[0].get_text()

    assert "Riya Sharma" in text
    assert "Built a REST API - fast - reliable" in text
    assert "�" not in text


def test_pdf_safe():
    assert pdf_safe("“Hi” – ok •  done") == '"Hi" - ok -  done'
