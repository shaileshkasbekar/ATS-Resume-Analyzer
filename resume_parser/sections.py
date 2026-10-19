import re


# --------------------------------
# Section headings to look for
# --------------------------------

SECTIONS = {

    "education": [
        "education",
        "academic qualification",
        "academic qualifications",
        "qualification",
        "qualifications",
        "academic background",
        "academics"
    ],

    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "internship",
        "internships"
    ],

    "projects": [
        "projects",
        "project",
        "academic projects",
        "personal projects",
        "key projects"
    ],

    "skills": [
        "skills",
        "technical skills",
        "skills & technologies",
        "technical skills & technologies",
        "core competencies",
        "technologies"
    ],

    "summary": [
        "summary",
        "professional summary",
        "profile",
        "career objective",
        "objective",
        "about me"
    ],

    "certifications": [
        "certifications",
        "certification",
        "certificates",
        "courses"
    ],

    "achievements": [
        "achievements",
        "accomplishments",
        "awards",
        "honors",
        "honours"
    ]
}


def is_heading(line, keywords):
    """
    A heading is a short line (like "TECHNICAL SKILLS" or
    "Projects:") that contains one of the keywords.
    """

    # Headings start with a letter; bullet points start with a symbol

    line = line.strip()

    if not line or not line[0].isalpha():
        return False

    # "Projects | see GitHub" or "Skills: Python, Java" -> keep the first part

    line = re.split(r"[|:–—]", line)[0]

    clean = re.sub(r"[^a-z& ]", " ", line.lower())
    clean = re.sub(r"\s+", " ", clean).strip()

    if not clean or len(clean.split()) > 5:
        return False

    if re.search(r"\d", line):
        return False

    for keyword in keywords:

        if re.search(r"(^|\s|&)" + re.escape(keyword) + r"($|\s|&)", clean):
            return True

    return False


def heading_section(line):
    """
    Returns the section name if the line is a heading, else None.
    """

    for section, keywords in SECTIONS.items():

        if is_heading(line, keywords):
            return section

    return None


def split_sections(text):
    """
    Splits the resume into sections:
    {"header": "...", "skills": "...", "projects": "...", ...}

    Text before the first heading goes into "header".
    """

    result = {"header": ""}

    current = "header"

    for line in text.splitlines():

        if not line.strip():
            continue

        section = heading_section(line)

        if section:

            current = section

            result.setdefault(current, "")

            # "Skills: Python, Java" -> keep the part after the heading

            if ":" in line:
                result[current] += line.split(":", 1)[1] + "\n"

            continue

        result[current] = result.get(current, "") + line + "\n"

    return result
