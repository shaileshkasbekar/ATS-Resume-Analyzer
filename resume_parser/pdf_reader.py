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


def extract_links_from_pdf(pdf_path):
    """
    Web addresses behind clickable links in the PDF. Many resumes show
    LinkedIn / GitHub only as an icon or a word, with the real address
    hidden in the link, so the text alone is not enough.
    """

    try:

        document = fitz.open(pdf_path)

    except Exception:

        return []

    links = [
        link["uri"]
        for page in document
        for link in page.get_links()
        if link.get("uri")
    ]

    document.close()

    return links


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
