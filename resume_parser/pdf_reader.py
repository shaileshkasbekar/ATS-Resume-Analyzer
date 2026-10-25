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


def extract_text_from_pdf_bytes(data):
    """
    Same as above for a PDF held in memory (e.g. an uploaded
    job description that does not need to be saved).
    """

    try:

        document = fitz.open(stream=data, filetype="pdf")

    except Exception as e:

        print("PDF Read Error:", e)

        return ""

    text = "".join(page.get_text() for page in document)

    document.close()

    return text
