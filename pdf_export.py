"""
HTML -> PDF with PyMuPDF (no extra library).

Text in the PDF is selectable, which keeps generated resumes
ATS-friendly. Characters the built-in PDF font cannot draw
(bullets, dashes, smart quotes) are replaced with plain ones.
"""

import io
import re

import fitz


REPLACEMENTS = {
    "•": "-", "●": "-", "▪": "-", "◦": "-", "·": "-", "➢": "-", "✓": "-",
    "–": "-", "—": "-", "−": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", " ": " ", "​": "",
}


def pdf_safe(text):
    """
    Plain-character version of a text for the PDF font.
    """

    text = str(text or "")

    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)

    # Drop anything else outside Latin-1 (icons from PDFs, emoji, private-use glyphs)

    return re.sub(r"[^\x09\x0a\x0d\x20-\xff]", "", text)


BASE_CSS = """
body { font-family: sans-serif; font-size: 10pt; color: #1b1f33; line-height: 1.35; }
h1 { font-size: 18pt; margin: 0 0 4pt 0; }
h2 { font-size: 12pt; margin: 12pt 0 4pt 0; padding-bottom: 2pt; border-bottom: 1px solid #c9cde0; }
h3 { font-size: 10.5pt; margin: 8pt 0 2pt 0; }
p { margin: 0 0 4pt 0; }
.muted { color: #5b6178; }
.small { font-size: 8.5pt; }
.li { margin: 0 0 2pt 10pt; }
table { width: 100%; border-collapse: collapse; }
td, th { border: 1px solid #d5d8e5; padding: 3pt 4pt; font-size: 9pt; vertical-align: top; }
th { background-color: #eef0f8; text-align: left; }
"""


def html_to_pdf(html, css=""):
    """
    Returns PDF bytes. `html` must already be escaped (built with
    Jinja autoescape); it is passed through pdf_safe here.
    """

    story = fitz.Story(html=pdf_safe(html), user_css=BASE_CSS + css)

    buffer = io.BytesIO()

    writer = fitz.DocumentWriter(buffer)

    page = fitz.paper_rect("a4")
    area = page + (42, 42, -42, -42)

    more = True

    while more:

        device = writer.begin_page(page)

        more, _ = story.place(area)

        story.draw(device)

        writer.end_page()

    writer.close()

    return buffer.getvalue()
