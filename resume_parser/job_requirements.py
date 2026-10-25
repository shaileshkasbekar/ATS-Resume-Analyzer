"""
Extract structured requirements from a job description.

Two sources are merged:

1. Rule-based parser: always runs, deterministic, used alone
   when the AI is unavailable.
2. AI extraction: better at understanding wording. Everything the
   AI returns is checked against the job description text, so the
   AI cannot add requirements the employer never wrote.

A requirement item looks like:
    {"name": "MySQL or PostgreSQL", "any_of": ["MySQL", "PostgreSQL"], "category": "skill"}
"""

import re

from resume_parser.ai_client import ask_ai_for_json, as_untrusted
from resume_parser.ai_validation import clean_text, clean_text_list, quote_in_text
from resume_parser.ats_score import calculate_ats_score
from resume_parser.scoring_config import EDUCATION_LEVELS
from resume_parser.skill_extractor import (
    extract_skills,
    canonical_skill,
    skill_in_text,
    find_skill_span,
    find_skill_evidence
)


MAX_MANDATORY = 20
MAX_PREFERRED = 15


PREFERRED_MARKERS = [
    "nice to have", "nice-to-have", "preferred", "is a plus", "a plus",
    "bonus", "good to have", "added advantage", "an advantage",
    "desirable", "optional"
]

REQUIRED_HEADINGS = [
    "requirements", "required", "must have", "must-have", "qualifications",
    "skills required", "required skills", "key skills", "what we are looking for",
    "what we're looking for", "who you are", "eligibility", "technical skills"
]

PREFERRED_HEADINGS = [
    "nice to have", "nice-to-have", "preferred", "preferred qualifications",
    "preferred skills", "good to have", "bonus", "bonus points", "pluses"
]

RESPONSIBILITY_HEADINGS = [
    "responsibilities", "key responsibilities", "roles and responsibilities",
    "role and responsibilities", "what you'll do", "what you will do",
    "your role", "duties", "the role", "job responsibilities"
]

SOFT_SKILLS = [
    "communication", "teamwork", "team player", "problem solving",
    "problem-solving", "leadership", "time management", "collaboration",
    "analytical", "adaptability", "attention to detail", "critical thinking",
    "ownership", "self-motivated", "interpersonal"
]

TOOLS = {
    "git", "github", "docker", "kubernetes", "jenkins", "postman", "vs code",
    "figma", "jira", "bug tracking", "linux", "mysql workbench", "xampp",
    "terraform", "ansible", "prometheus", "grafana", "jupyter", "excel",
    "power bi", "tableau", "ci/cd"
}

EDUCATION_PATTERNS = [
    ("phd", r"\bph\.?\s?d\b|\bdoctorate\b"),
    ("master", r"\bmaster'?s?\b|\bm\.?\s?tech\b|\bm\.e\.|\bm\.?sc\b|\bmca\b|\bmba\b|\bpost[- ]?graduate\b"),
    ("bachelor", r"\bbachelor'?s?\b|\bb\.?\s?tech\b|\bb\.e\.|\bb\.?sc\b|\bbca\b|\bbs\b|\bundergraduate\b|\bgraduate\b|\bdegree\b"),
    ("diploma", r"\bdiploma\b"),
]


# =========================================
# Small helpers
# =========================================

def _strip_bullet(line):

    line = re.sub(r"^[\s\-–—•*▪●◦·>✓■□➢]+", "", line)

    # Numbered lists: "1. ", "2) "

    line = re.sub(r"^\d{1,2}[.)]\s+", "", line)

    return line.strip()


def _sentences(text):
    """
    Splits a line into sentences, so "Java is required. Kafka is a plus."
    marks only Kafka as preferred.
    """

    parts = re.split(r"(?<=[.;!?])\s+(?=[A-Z])", text)

    return [part.strip() for part in parts if part.strip()]


def _heading_type(line):
    """
    "required" / "preferred" / "responsibilities" if the line is a
    section heading of the job description, else None.
    """

    # Bullet points are content, never headings

    if re.match(r"^\s*([\-–—•*▪●◦·>✓■□➢]|\d{1,2}[.)]\s)", line):
        return None

    clean = re.sub(r"[^a-z'\- ]", " ", line.lower())
    clean = re.sub(r"\s+", " ", clean).strip()

    if not clean or len(clean.split()) > 6:
        return None

    # A heading is short; lines like "Experience with React is a plus"
    # are content, not headings

    if len(line.strip()) > 60:
        return None

    for heading in PREFERRED_HEADINGS:
        if heading in clean:
            return "preferred"

    for heading in RESPONSIBILITY_HEADINGS:
        if heading in clean:
            return "responsibilities"

    for heading in REQUIRED_HEADINGS:
        if heading in clean:
            return "required"

    return None


def _is_preferred_line(line, context):

    lower = line.lower()

    return context == "preferred" or any(marker in lower for marker in PREFERRED_MARKERS)


def _item(skills):

    skills = [canonical_skill(s) for s in skills]

    unique = []

    for skill in skills:
        if skill.lower() not in (u.lower() for u in unique):
            unique.append(skill)

    category = "tool" if all(s.lower() in TOOLS for s in unique) else "skill"

    return {
        "name": " or ".join(unique),
        "any_of": unique,
        "category": category
    }


def _item_key(item):

    return frozenset(s.lower() for s in item["any_of"])


def _group_alternatives(line):
    """
    Finds skills in one line and groups alternatives:
    "MySQL or PostgreSQL"  -> one item with any_of [MySQL, PostgreSQL]
    "such as React, Angular or Vue" -> one item with all three
    """

    lower = line.lower()

    skills = extract_skills(line)

    spans = []

    for skill in skills:

        span = find_skill_span(lower, skill)

        if span:
            spans.append((span[0], span[1], skill))

    spans.sort()

    if not spans:
        return []

    # "such as / one of / any of / like / either" before a list means any of them

    choice_list = re.search(r"\b(such as|one of|any of|either|like|or similar)\b", lower)

    groups = [[spans[0][2]]]

    for previous, current in zip(spans, spans[1:]):

        between = lower[previous[1]:current[0]]

        is_or = re.fullmatch(r"\s*(/|\||,?\s*or|,?\s*and/or)\s*", between) is not None

        is_comma = re.fullmatch(r"\s*,\s*", between) is not None

        if is_or or (is_comma and choice_list and choice_list.start() < current[0]):
            groups[-1].append(current[2])
        else:
            groups.append([current[2]])

    return [_item(group) for group in groups]


# =========================================
# Rule-based extraction
# =========================================

def parse_requirements_rules(jd_text):

    found = {
        "mandatory": [],
        "preferred": [],
        "experience_years": [],
        "experience_text": "",
        "education_lines": [],
        "education_levels": [],
        "certifications_required": [],
        "certifications_preferred": [],
        "responsibilities": []
    }

    context = None

    for raw_line in jd_text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        heading = _heading_type(line)

        if heading:
            context = heading
            continue

        line_content = _strip_bullet(line)

        for sentence in _sentences(line_content):
            _parse_sentence(sentence, context, found)

        if context == "responsibilities" and 15 <= len(line_content) <= 220 and len(found["responsibilities"]) < 10:
            found["responsibilities"].append(line_content)

    soft_skills = [
        s for s in SOFT_SKILLS
        if re.search(r"\b" + re.escape(s) + r"\b", jd_text.lower())
    ]

    return {
        "mandatory_skills": _merge_items(found["mandatory"], [], MAX_MANDATORY * 2),
        "preferred_skills": _merge_items(found["preferred"], [], MAX_PREFERRED * 2),
        "experience": {
            "min_years": min(found["experience_years"]) if found["experience_years"] else None,
            "text": found["experience_text"][:200]
        },
        "education": found["education_lines"][:5],
        "education_required_level": min(found["education_levels"]) if found["education_levels"] else None,
        "certifications_required": found["certifications_required"][:5],
        "certifications_preferred": found["certifications_preferred"][:5],
        "responsibilities": found["responsibilities"],
        "soft_skills": soft_skills
    }


def _parse_sentence(content, context, found):
    """
    Reads one sentence of the job description into `found`.
    """

    lower = content.lower()

    preferred_line = _is_preferred_line(content, context)

    # Skills

    for item in _group_alternatives(content):
        (found["preferred"] if preferred_line else found["mandatory"]).append(item)

    # Experience (only from required sentences)

    mentions_experience = (
        "experience" in lower
        or re.search(r"\bexp\b|\bfreshers?\b|\bentry[- ]level\b", lower)
    )

    if mentions_experience and not preferred_line:

        if re.search(r"\bfreshers?\b|\bentry[- ]level\b|\bno (prior )?experience\b", lower):
            found["experience_years"].append(0.0)
            found["experience_text"] = found["experience_text"] or content

        for match in re.finditer(
            r"(\d+(?:\.\d+)?)\s*\+?\s*(?:(?:-|–|to)\s*\d+(?:\.\d+)?\s*\+?\s*)?(?:years?|yrs?)\b",
            lower
        ):
            found["experience_years"].append(float(match.group(1)))
            found["experience_text"] = found["experience_text"] or content

    # Education

    levels = [
        level for level, pattern in EDUCATION_PATTERNS
        if re.search(pattern, lower)
    ]

    if levels and re.search(r"degree|bachelor|master|b\.?\s?tech|m\.?\s?tech|b\.e|m\.e|bsc|msc|bca|mca|ph\.?\s?d|diploma|graduate", lower):

        found["education_lines"].append(content[:200])

        if not preferred_line:
            found["education_levels"].append(min(EDUCATION_LEVELS[level] for level in levels))

    # Certifications

    if "certif" in lower:
        key = "certifications_preferred" if preferred_line else "certifications_required"
        found[key].append(content[:200])


# =========================================
# AI extraction
# =========================================

def _ai_requirements(jd_text):

    prompt = f"""
Extract the requirements from this job description.

{as_untrusted("job_description", jd_text)}

Rules:
1. Only include requirements that are actually written in the job description.
2. mandatory_skills: technical skills, languages, frameworks, databases, tools
   the job requires. Use short standard names ("React", "SQL", "REST API").
   If the job accepts alternatives, write them as one item: "MySQL or PostgreSQL".
3. preferred_skills: skills described as preferred, nice to have, a plus or bonus.
4. Do not put soft skills in the skill lists.
5. responsibilities: up to 8 short phrases copied from the job description.
6. soft_skills: soft skills that are mentioned.
7. If something is not mentioned, use an empty list or empty string.

Return ONLY valid JSON with exactly this structure:
{{
    "job_title": "",
    "company": "",
    "mandatory_skills": [],
    "preferred_skills": [],
    "experience_text": "",
    "education": [],
    "certifications": [],
    "responsibilities": [],
    "soft_skills": []
}}
"""

    return ask_ai_for_json(
        "You extract structured job requirements from job descriptions. Return only valid JSON.",
        prompt
    )


def _validated_ai_items(values, jd_text, limit):
    """
    AI skill strings -> requirement items. An item (or an alternative
    inside it) is dropped if it does not appear in the job description.
    """

    items = []

    for value in clean_text_list(values, max_items=limit * 2, max_len=80):

        options = [
            part.strip() for part in re.split(r"\s+or\s+|\s*/\s*|\s*\|\s*", value)
            if part.strip()
        ]

        verified = [
            option for option in options
            if len(option) <= 40 and (skill_in_text(jd_text, canonical_skill(option)) or skill_in_text(jd_text, option))
        ]

        if verified:
            items.append(_item(verified))

    return items[:limit]


def _words_overlap(text, source, min_share=0.6):

    words = [w for w in re.findall(r"[a-z]{4,}", text.lower())]

    if not words:
        return False

    source_lower = source.lower()

    return sum(1 for w in words if w in source_lower) / len(words) >= min_share


# =========================================
# Merge
# =========================================

def _merge_items(primary, secondary, limit):
    """
    Items from primary first; secondary items are added only
    if none of their skills are already covered.
    """

    result = []
    covered = set()

    for item in primary + secondary:

        key = _item_key(item)

        if key & covered:
            continue

        covered |= key
        result.append(item)

    return result[:limit]


def extract_requirements(jd_text, job_title="", company="", use_ai=True):
    """
    Returns the merged requirements dict.
    """

    rules = parse_requirements_rules(jd_text)

    ai = _ai_requirements(jd_text) if use_ai else None

    ai_available = bool(ai)

    ai = ai or {}

    ai_mandatory = _validated_ai_items(ai.get("mandatory_skills"), jd_text, MAX_MANDATORY)
    ai_preferred = _validated_ai_items(ai.get("preferred_skills"), jd_text, MAX_PREFERRED)

    # Mandatory always wins over preferred for the same skill

    mandatory = _merge_items(ai_mandatory, rules["mandatory_skills"], MAX_MANDATORY)

    mandatory_keys = set()
    for item in mandatory:
        mandatory_keys |= _item_key(item)

    preferred = [
        item for item in _merge_items(ai_preferred, rules["preferred_skills"], MAX_PREFERRED * 2)
        if not (_item_key(item) & mandatory_keys)
    ][:MAX_PREFERRED]

    # Responsibilities / education / certifications from the AI are kept
    # only if they can be found in the job description

    ai_responsibilities = [
        r for r in clean_text_list(ai.get("responsibilities"), 8, 220)
        if quote_in_text(r, jd_text)
    ]

    ai_education = [e for e in clean_text_list(ai.get("education"), 5, 200) if _words_overlap(e, jd_text)]

    ai_certifications = [c for c in clean_text_list(ai.get("certifications"), 5, 200) if _words_overlap(c, jd_text)]

    ai_title = clean_text(ai.get("job_title"), 200)
    ai_company = clean_text(ai.get("company"), 200)

    return {
        "job_title": (job_title or (ai_title if _words_overlap(ai_title, jd_text, 0.5) else "")).strip()[:200],
        "company": (company or (ai_company if ai_company and ai_company.lower() in jd_text.lower() else "")).strip()[:200],
        "mandatory_skills": mandatory,
        "preferred_skills": preferred,
        "experience": rules["experience"],
        "education": rules["education"] or ai_education,
        "education_required_level": rules["education_required_level"],
        "certifications_required": rules["certifications_required"],
        "certifications_preferred": rules["certifications_preferred"] or [
            c for c in ai_certifications if c not in rules["certifications_required"]
        ],
        "responsibilities": ai_responsibilities or rules["responsibilities"],
        "soft_skills": sorted(set(rules["soft_skills"]) | {
            s.lower() for s in clean_text_list(ai.get("soft_skills"), 10, 40)
            if s.lower() in jd_text.lower()
        }),
        "source": "ai+rules" if ai_available else "rules",
        "ai_available": ai_available
    }


# =========================================
# Requirements from a predefined job role
# =========================================

def role_requirements(role_name, role_skill_groups, resume_text):
    """
    Turns a predefined role (from the database) into the same
    requirements shape, so the job match engine works without a JD.

    Common groups: core + supporting -> mandatory, optional -> preferred.
    Technology paths are alternatives: the candidate's strongest path is
    used; if none is found, the paths' core skills become one
    "any of" requirement.
    """

    skills = [s.lower() for s in extract_skills(resume_text, [d["skill_name"] for d in role_skill_groups])]

    evidence = find_skill_evidence(resume_text, skills)

    detected_path = calculate_ats_score(skills, role_skill_groups, evidence)[5]

    mandatory = []
    preferred = []

    path_core = {}

    for data in role_skill_groups:

        item = _item([data["skill_name"]])

        if data["group_type"] == "common":

            (preferred if data["importance"] == "optional" else mandatory).append(item)

        elif data["group_name"] == detected_path:

            (mandatory if data["importance"] == "core" else preferred).append(item)

        elif not detected_path and data["importance"] == "core":

            path_core.setdefault(data["group_name"], data["skill_name"])

    if path_core:
        mandatory.append(_item(list(path_core.values())))

    mandatory = _merge_items(mandatory, [], MAX_MANDATORY)

    mandatory_keys = set()
    for item in mandatory:
        mandatory_keys |= _item_key(item)

    preferred = [p for p in _merge_items(preferred, [], MAX_PREFERRED) if not (_item_key(p) & mandatory_keys)]

    return {
        "job_title": role_name,
        "company": "",
        "mandatory_skills": mandatory,
        "preferred_skills": preferred,
        "experience": {"min_years": None, "text": ""},
        "education": [],
        "education_required_level": None,
        "certifications_required": [],
        "certifications_preferred": [],
        "responsibilities": [],
        "soft_skills": [],
        "source": "role",
        "ai_available": False,
        "detected_path": detected_path or ""
    }
