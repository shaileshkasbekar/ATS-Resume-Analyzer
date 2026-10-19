import fitz


def extract_text_from_pdf(pdf_path):
    """
    Returns the resume text, or an empty string when the
    PDF is corrupt, password protected or a scanned image.
    """

    try:

        document = fitz.open(pdf_path)

    except Exception as e:

        print("PDF Read Error:", e)

        return ""

    text = ""

    for page in document:

        text += page.get_text()

    document.close()

    return text
