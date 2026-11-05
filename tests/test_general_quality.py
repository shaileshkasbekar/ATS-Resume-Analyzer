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


# ---------------- Profiles shown as icons / links ----------------

ICON_RESUME = """Aditya Raut
\u00a7 adity1raut | \u00ef aditya1-raut | araut@example.com
EDUCATION
B.Tech in Computer Science, 2023 - 2027
SKILLS
Go, Java, SQL
"""


def test_linkedin_found_from_pdf_link():
    without_links = analyze_resume(ICON_RESUME)
    with_links = analyze_resume(ICON_RESUME, ["https://linkedin.com/in/aditya1-raut", "https://github.com/adity1raut"])

    assert without_links["linkedin"] is False
    assert with_links["linkedin"] is True
    assert with_links["github"] is True


def test_linkedin_found_from_address_in_text():
    assert analyze_resume("Name\nlinkedin.com/in/someone\nSKILLS\nPython")["linkedin"] is True


# ---------------- Summary without a heading ----------------

def test_summary_paragraph_without_heading():
    text = """Riya Sharma
riya@example.com | +91 98765 43210
Final-year Computer Science student who builds backend services in Python and Flask,
with two deployed projects used by more than 200 students and a strong interest in APIs.
EDUCATION
B.Tech in Computer Science, 2022 - 2026
"""
    assert analyze_resume(text)["sections"]["summary"] is True


def test_contact_lines_are_not_a_summary():
    text = """Riya Sharma
riya@example.com | +91 98765 43210 | linkedin.com/in/riya | github.com/riya
EDUCATION
B.Tech in Computer Science, 2022 - 2026
"""
    assert analyze_resume(text)["sections"]["summary"] is False
