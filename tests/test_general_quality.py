"""
Phase 4: general resume quality (experience level, confirmed vs potential issues).
"""

from resume_parser.general_analyzer import analyze_resume

from conftest import PYTHON_FRESHER, JAVA_DEVELOPER


def test_fresher_detected_and_not_penalized():
    result = analyze_resume(PYTHON_FRESHER)

    assert result["experience_level"] == "fresher"
    assert not any("Experience" in i["text"] for i in result["issues"]["confirmed"])
    assert any("Experience" in i["text"] for i in result["issues"]["potential"])
    assert "Add an Experience or Internship section." not in result["recommendations"]


def test_experienced_candidate():
    assert analyze_resume(JAVA_DEVELOPER)["experience_level"] == "experienced"


def test_experienced_without_experience_section_is_confirmed_issue():
    text = PYTHON_FRESHER.replace("2022 - 2026", "2010 - 2014")
    result = analyze_resume(text)

    assert result["experience_level"] != "fresher"
    assert any("No Experience section" in i["text"] for i in result["issues"]["confirmed"])


def test_repetition_and_vague_wording():
    text = PYTHON_FRESHER + "\n- Built a CLI tool\n- Built a scraper for various sites etc\n- Built a bot\n"

    issues = analyze_resume(text)["issues"]["confirmed"]

    assert any(i["category"] == "Repetition" for i in issues)
    assert any(i["category"] == "Vague wording" for i in issues)


def test_pdf_extraction_problems_are_potential():
    text = PYTHON_FRESHER + "" * 6 + "\nName        Email        Phone\nSkills      Projects     Tools\n" * 5

    potential = analyze_resume(text)["issues"]["potential"]

    assert sum(1 for i in potential if i["category"] == "PDF extraction") >= 2


def test_scoring_version():
    assert analyze_resume(PYTHON_FRESHER)["scoring_version"] == "gen-2.0"
