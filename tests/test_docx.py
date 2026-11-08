"""
Word (.docx) resumes: text, bullets, tables, hidden links, and the full workflow.
"""

import io
import zipfile

from conftest import PYTHON_JD, login
from resume_parser.document_reader import (
    extract_text, extract_text_from_bytes, extract_links, has_valid_signature, is_supported
)


def make_docx(paragraphs, link=None):
    """
    A minimal real .docx. paragraphs: list of (text, is_bullet).
    link: (text, url) added as a clickable hyperlink.
    """

    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' \
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'

    body = ""

    for text, bullet in paragraphs:
        num = '<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>' if bullet else ""
        body += f"<w:p>{num}<w:r><w:t>{text}</w:t></w:r></w:p>"

    rels = ""

    if link:
        body += f'<w:p><w:hyperlink r:id="rId9"><w:r><w:t>{link[0]}</w:t></w:r></w:hyperlink></w:p>'
        rels = f'<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{link[1]}" TargetMode="External"/>'

    # A table cell too
    body += "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table cell Docker</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", f'<?xml version="1.0"?><w:document {w}><w:body>{body}</w:body></w:document>')
        z.writestr("word/_rels/document.xml.rels",
                   f'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>')

    return buffer.getvalue()


RESUME_DOCX = [
    ("Riya Sharma", False),
    ("riya@example.com | +91 98765 43210", False),
    ("PROJECTS", False),
    ("Expense Tracker API | Python, Flask, MySQL", False),
    ("Built a REST API with Flask and MySQL used by 200+ students", True),
    ("Deployed the app with Docker on a Linux server, code on Git", True),
    ("SKILLS", False),
    ("Python, Flask, MySQL, Git, Docker, Linux", False),
    ("EDUCATION", False),
    ("B.Tech in Computer Science, 2022 - 2026", False),
]


def test_docx_text_bullets_tables_and_links(tmp_path):
    path = tmp_path / "r.docx"
    path.write_bytes(make_docx(RESUME_DOCX, ("LinkedIn", "https://linkedin.com/in/riya")))

    text = extract_text(str(path))

    assert "Riya Sharma" in text
    assert "- Built a REST API with Flask" in text      # list items become bullets
    assert "Table cell Docker" in text
    assert extract_links(str(path)) == ["https://linkedin.com/in/riya"]


def test_docx_from_bytes_and_types():
    data = make_docx(RESUME_DOCX)

    assert "Expense Tracker API" in extract_text_from_bytes("job.docx", data)
    assert is_supported("cv.DOCX") and is_supported("cv.pdf") and not is_supported("cv.doc")
    assert has_valid_signature("cv.docx", data[:8])
    assert not has_valid_signature("cv.docx", b"%PDF-1.4")


def test_broken_docx_returns_no_text(tmp_path):
    path = tmp_path / "broken.docx"
    path.write_bytes(b"PK\x03\x04 not really a zip")

    assert extract_text(str(path)) == ""
    assert extract_links(str(path)) == []


def test_job_match_with_docx_resume(client, test_db):
    login(client, 1)

    response = client.post("/job-match", data={
        "mode": "paste", "job_description": PYTHON_JD,
        "resume": (io.BytesIO(make_docx(RESUME_DOCX)), "riya.docx")
    }, content_type="multipart/form-data")

    assert response.status_code == 200
    assert b"How your score was calculated" in response.data
    assert b"Python" in response.data


def test_quality_check_with_docx_and_hidden_linkedin(client, test_db):
    login(client, 1)

    response = client.post("/general-analyzer", data={
        "resume": (io.BytesIO(make_docx(RESUME_DOCX, ("Profile", "https://www.linkedin.com/in/riya"))), "riya.docx")
    }, content_type="multipart/form-data")

    assert response.status_code == 200
    assert b"LinkedIn profile found" in response.data


def test_docx_job_description_file(client, test_db):
    login(client, 1)

    jd = make_docx([(line, False) for line in PYTHON_JD.splitlines() if line.strip()])

    from conftest import make_pdf, PYTHON_FRESHER

    response = client.post("/job-match", data={
        "mode": "file", "jd_file": (io.BytesIO(jd), "job.docx"),
        "resume": (io.BytesIO(make_pdf(PYTHON_FRESHER)), "r.pdf")
    }, content_type="multipart/form-data")

    assert response.status_code == 200
    assert b"How your score was calculated" in response.data
