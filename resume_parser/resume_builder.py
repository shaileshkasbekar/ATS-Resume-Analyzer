"""
Builds an optimized, ATS-friendly resume from the original resume text
plus the suggestions the user accepted. The original file is never changed.

Templates: classic, modern, technical, fresher. All use standard section
headings, one column and real (selectable) text.
"""

import re

from resume_parser.ai_validation import _normalize
from resume_parser.sections import split_sections


SECTION_TITLES = {
    "summary": "Professional Summary",
    "experience": "Experience",
    "projects": "Projects",
    "skills": "Technical Skills",
    "education": "Education",
    "certifications": "Certifications",
    "achievements": "Achievements",
}

TEMPLATES = {
    "classic": {
        "label": "Classic",
        "description": "Traditional, serif, works for every company.",
        "order": ["summary", "experience", "projects", "skills", "education", "certifications", "achievements"],
    },
    "modern": {
        "label": "Modern",
        "description": "Clean sans-serif with a colour accent.",
        "order": ["summary", "skills", "experience", "projects", "education", "certifications", "achievements"],
    },
    "technical": {
        "label": "Technical",
        "description": "Skills and projects first, compact. For engineering roles.",
        "order": ["summary", "skills", "projects", "experience", "education", "certifications", "achievements"],
    },
    "fresher": {
        "label": "Fresher",
        "description": "Education and projects first. For students and new graduates.",
        "order": ["summary", "education", "skills", "projects", "experience", "achievements", "certifications"],
    },
}

TEMPLATE_CSS = {
    "classic": """
        .resume { font-family: serif; font-size: 10.5pt; }
        .resume h1 { text-align: center; font-size: 20pt; }
        .resume .contact { text-align: center; }
        .resume h2 { font-size: 11.5pt; text-transform: uppercase; border-bottom: 1px solid #222; }
    """,
    "modern": """
        .resume { font-family: sans-serif; font-size: 10pt; }
        .resume h1 { font-size: 21pt; color: #3730a3; }
        .resume h2 { font-size: 11.5pt; color: #3730a3; border-bottom: 1.5px solid #c7c9f5; }
    """,
    "technical": """
        .resume { font-family: sans-serif; font-size: 9.5pt; }
        .resume h1 { font-size: 18pt; }
        .resume h2 { font-size: 10pt; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #888; }
        .resume p { margin-bottom: 2pt; }
    """,
    "fresher": """
        .resume { font-family: sans-serif; font-size: 10pt; }
        .resume h1 { font-size: 20pt; color: #0f5132; }
        .resume h2 { font-size: 11pt; color: #0f5132; border-bottom: 1.5px solid #9fd3b8; }
    """,
}

COMMON_CSS = """
    .resume { color: #111; line-height: 1.35; }
    .resume h1 { margin: 0 0 3pt 0; }
    .resume .contact { color: #333; font-size: 9pt; margin-bottom: 6pt; }
    .resume h2 { margin: 10pt 0 4pt 0; padding-bottom: 2pt; }
    .resume p { margin: 0 0 3pt 0; }
    .resume .li { margin-left: 10pt; }
"""


# =========================================
# Text -> items
# =========================================

def _is_bullet(line):

    return bool(line) and not line[0].isalnum() and line[0] not in "([\"'+"


def _clean(line):

    line = re.sub(r"^[^\w(\[\"'+]+", "", line)

    return re.sub(r"\s+", " ", line).strip()


def to_items(text):
    """
    Lines -> items. Bullets that wrapped onto several lines in the PDF
    are joined back into one item.
    """

    items = []

    for raw in (text or "").splitlines():

        line = raw.strip()

        if not line:
            continue

        bullet = _is_bullet(line)
        clean = _clean(line)

        if not clean:
            continue

        previous = items[-1] if items else None

        continuation = (
            previous is not None
            and not bullet
            and (
                clean[0].islower()
                or previous["text"].endswith((",", "-", "&", "/"))
                or (previous["bullet"] and not previous["text"].endswith((".", ":", ";")) and " | " not in clean)
            )
        )

        if continuation:
            previous["text"] += " " + clean
        else:
            items.append({"text": clean, "bullet": bullet})

    return items


# =========================================
# Apply accepted suggestions
# =========================================

def apply_suggestions(sections, suggestions):
    """
    Replaces the original text of each accepted suggestion.
    Returns the list of suggestions that could not be placed.
    """

    not_applied = []

    for suggestion in suggestions:

        if suggestion["kind"] == "advice":
            continue

        original = suggestion.get("original") or ""
        improved = suggestion["improved"]

        if not original:

            if suggestion["kind"] == "summary":
                sections["summary"] = [{"text": improved, "bullet": False}]
            else:
                not_applied.append(suggestion)

            continue

        target = _normalize(original)

        if not _replace_in_sections(sections, target, improved):
            not_applied.append(suggestion)

    return not_applied


def _replace_in_sections(sections, target, improved):

    for items in sections.values():

        for i, item in enumerate(items):

            text = _normalize(item["text"])

            # The original is most of this item: replace the whole item

            if target in text and len(target) >= 0.6 * len(text):
                item["text"] = improved
                return True

            # The original spans this item and the next one

            if i + 1 < len(items):

                joined = _normalize(item["text"] + " " + items[i + 1]["text"])

                if target in joined and len(target) >= 0.6 * len(joined):
                    item["text"] = improved
                    del items[i + 1]
                    return True

            # A smaller part of the item: replace just that part

            if target in text and original_in(item["text"], target):
                item["text"] = _replace_part(item["text"], target, improved)
                return True

    return False


def original_in(text, target):

    return _locate(text, target) is not None


def _locate(text, target):
    """
    (start, end) in `text` of the normalized `target`, or None.
    """

    words = target.split()

    if not words:
        return None

    pattern = r"[^a-z0-9+#.%/]*".join(re.escape(w) for w in words)

    match = re.search(pattern, text.lower())

    return (match.start(), match.end()) if match else None


def _replace_part(text, target, improved):

    span = _locate(text, target)

    return text[:span[0]] + improved + text[span[1]:] if span else text


# =========================================
# Build the resume
# =========================================

def build_resume(resume_text, accepted_suggestions, template="modern"):
    """
    Returns a dict ready for templates/resume_doc.html.
    """

    template = template if template in TEMPLATES else "modern"

    parts = split_sections(resume_text)

    header_lines = [_clean(l) for l in parts.get("header", "").splitlines() if _clean(l)]

    name = header_lines[0] if header_lines else "Your Name"

    contact = " | ".join(header_lines[1:4])

    sections = {
        key: to_items(parts.get(key, ""))
        for key in SECTION_TITLES
    }

    not_applied = apply_suggestions(sections, accepted_suggestions)

    ordered = [
        {"key": key, "title": SECTION_TITLES[key], "items": sections[key]}
        for key in TEMPLATES[template]["order"]
        if sections.get(key)
    ]

    return {
        "template": template,
        "name": name,
        "contact": contact,
        "sections": ordered,
        "css": COMMON_CSS + TEMPLATE_CSS[template],
        "not_applied": not_applied,
        "applied_count": len([s for s in accepted_suggestions if s["kind"] != "advice"]) - len(not_applied),
    }


def doc_to_text(doc):
    """
    Plain text of a built resume (with its section headings), so it can be
    scored by the same engine as the original resume.
    """

    lines = [doc["name"], doc["contact"]]

    for section in doc["sections"]:

        lines.append(section["title"])

        for item in section["items"]:
            lines.append(("- " if item["bullet"] else "") + item["text"])

    return "\n".join(line for line in lines if line)
