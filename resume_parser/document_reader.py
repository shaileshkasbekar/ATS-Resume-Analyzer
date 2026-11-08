"""
One place to read resumes and job descriptions: PDF and Word (.docx).

- Text and clickable links from PDF (PyMuPDF) and DOCX (the .docx file is a
  zip of XML files, read with the standard library - no extra package).
- Scanned PDFs (images only) are read with OCR when Tesseract is installed;
  otherwise they return no text and the user is asked for a text-based file.
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET

import fitz


SUPPORTED = (".pdf", ".docx")

SIGNATURES = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",
}

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def extension(name):

    return os.path.splitext((name or "").lower())[1]


def is_supported(name):

    return extension(name) in SUPPORTED


def has_valid_signature(name, first_bytes):
    """
    The file really is what its name says (not a renamed .exe etc.).
    """

    signature = SIGNATURES.get(extension(name))

    return bool(signature) and first_bytes.startswith(signature)


# =========================================
# DOCX
# =========================================

def _docx_parts(source):
    """
    (document XML root, {relationship id: target}) or (None, {}).
    source: a path or a file-like object.
    """

    try:

        with zipfile.ZipFile(source) as archive:

            root = ET.fromstring(archive.read("word/document.xml"))

            links = {}

            if "word/_rels/document.xml.rels" in archive.namelist():

                rels = ET.fromstring(archive.read("word/_rels/document.xml.rels"))

                for rel in rels:
                    if rel.get("TargetMode") == "External":
                        links[rel.get("Id")] = rel.get("Target")

            return root, links

    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError):

        return None, {}


def _docx_text(root):

    lines = []

    # Paragraphs, including those inside tables, in document order

    for paragraph in root.iter(W + "p"):

        parts = []

        for node in paragraph.iter():

            if node.tag == W + "t" and node.text:
                parts.append(node.text)
            elif node.tag == W + "tab":
                parts.append(" ")
            elif node.tag in (W + "br", W + "cr"):
                parts.append("\n")

        text = "".join(parts)

        # Word list items have no bullet character in the text

        is_list = paragraph.find(f"{W}pPr/{W}numPr") is not None

        if text.strip():
            lines.append(("- " if is_list else "") + text)

    return "\n".join(lines)


def _docx_links(root, rels):

    links = [rels[h.get(R + "id")] for h in root.iter(W + "hyperlink") if h.get(R + "id") in rels]

    # Also field-code links: HYPERLINK "https://..."

    for instr in root.iter(W + "instrText"):
        match = re.search(r'HYPERLINK\s+"([^"]+)"', instr.text or "")
        if match:
            links.append(match.group(1))

    return links


# =========================================
# PDF (with optional OCR)
# =========================================

def ocr_available():

    return bool(os.getenv("TESSDATA_PREFIX")) or any(
        os.path.exists(os.path.join(folder, "tessdata"))
        for folder in (r"C:\Program Files\Tesseract-OCR", r"C:\Program Files (x86)\Tesseract-OCR",
                       "/usr/share/tesseract-ocr/5", "/usr/share/tesseract-ocr/4.00", "/usr/share/tessdata")
    )


def _tessdata():

    if os.getenv("TESSDATA_PREFIX"):
        return os.getenv("TESSDATA_PREFIX")

    for folder in (r"C:\Program Files\Tesseract-OCR", r"C:\Program Files (x86)\Tesseract-OCR"):
        if os.path.exists(os.path.join(folder, "tessdata")):
            return os.path.join(folder, "tessdata")

    for folder in ("/usr/share/tesseract-ocr/5/tessdata", "/usr/share/tesseract-ocr/4.00/tessdata", "/usr/share/tessdata"):
        if os.path.exists(folder):
            return folder

    return None


def _pdf_text(document):

    text = "".join(page.get_text() for page in document)

    # Scanned PDF: almost no text but has pages -> try OCR

    if len(text.strip()) < 30 and len(document) and ocr_available():

        try:
            text = "".join(
                page.get_textpage_ocr(language="eng", dpi=300, full=True, tessdata=_tessdata()).extractText()
                for page in document
            )
        except Exception as e:
            print("OCR failed:", e)

    return text


# =========================================
# Public helpers
# =========================================

def extract_text(path):
    """
    Text of a PDF or DOCX file ("" if it cannot be read).
    """

    if extension(path) == ".docx":
        root, _ = _docx_parts(path)
        return _docx_text(root) if root is not None else ""

    try:
        document = fitz.open(path)
    except Exception as e:
        print("PDF Read Error:", e)
        return ""

    try:
        return _pdf_text(document)
    finally:
        document.close()


def extract_text_from_bytes(name, data):
    """
    Same as extract_text for a file held in memory (job description uploads).
    """

    import io

    if extension(name) == ".docx":
        root, _ = _docx_parts(io.BytesIO(data))
        return _docx_text(root) if root is not None else ""

    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        print("PDF Read Error:", e)
        return ""

    try:
        return _pdf_text(document)
    finally:
        document.close()


def extract_links(path):
    """
    Addresses behind clickable links (LinkedIn / GitHub shown as icons).
    """

    if not path or not os.path.exists(path):
        return []

    if extension(path) == ".docx":
        root, rels = _docx_parts(path)
        return _docx_links(root, rels) if root is not None else []

    try:
        document = fitz.open(path)
    except Exception:
        return []

    try:
        return [link["uri"] for page in document for link in page.get_links() if link.get("uri")]
    finally:
        document.close()
