"""
Writing tools for one job match:

- a cover letter for the job
- a LinkedIn headline and "About" section

Same honesty rules as the improvement assistant, enforced in code:
- a sentence naming a skill the resume does not show is removed
- numbers that are not in the resume become "[add real number]"
A simple template is used when the AI is unavailable.
"""

import re

from resume_parser.ai_client import ask_ai_for_json, as_untrusted
from resume_parser.ai_validation import clean_text
from resume_parser.improvement import remove_invented_numbers
from resume_parser.skill_extractor import extract_skills


MAX_LETTER = 3500
MAX_ABOUT = 2600
MAX_HEADLINE = 220


def _sentences(text):

    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def keep_only_true_facts(text, resume_text):
    """
    Returns (cleaned text, removed sentences, needs_metric).
    """

    resume_skills = {s.lower() for s in extract_skills(resume_text)}

    kept_paragraphs = []
    removed = []

    for paragraph in re.split(r"\n\s*\n", text.strip()):

        kept = []

        for sentence in _sentences(paragraph):

            new_skills = {s.lower() for s in extract_skills(sentence)} - resume_skills

            if new_skills:
                removed.append(sentence)
            else:
                kept.append(sentence)

        if kept:
            kept_paragraphs.append(" ".join(kept))

    cleaned, needs_metric = remove_invented_numbers("\n\n".join(kept_paragraphs), resume_text)

    return cleaned, removed, needs_metric


def _name(resume_text):

    for line in (resume_text or "").splitlines():
        line = line.strip()
        if line and "@" not in line and len(line.split()) <= 5 and not re.search(r"\d", line):
            return line

    return "Your Name"


def _shown_skills(result):

    return [m.get("matched_skill") or m["requirement"]
            for m in result.get("mandatory", []) + result.get("preferred", [])
            if m.get("status") == "matched" and m.get("evidence") in ("experience", "project")]


# =========================================
# Fallbacks (no AI)
# =========================================

def _template_letter(result, resume_text):

    title = result.get("job_title") or "this role"
    company = result.get("company") or "your company"
    skills = _shown_skills(result)[:4]

    skill_line = (f"In my projects and experience I have worked with {', '.join(skills)}, "
                  "which match the requirements of this role." if skills else
                  "My resume shows the projects and skills I would bring to this role.")

    return (
        "Dear Hiring Manager,\n\n"
        f"I am applying for the {title} position at {company}. {skill_line}\n\n"
        "[Add one or two sentences about your strongest project: what you built, the tools you used and the result.]\n\n"
        f"I would welcome the chance to discuss how I can contribute to {company}. Thank you for your time.\n\n"
        f"Sincerely,\n{_name(resume_text)}"
    )


def _template_linkedin(result, resume_text):

    skills = _shown_skills(result)[:5]
    title = result.get("job_title") or "Software Developer"

    headline = f"Aspiring {title}" + (f" | {' · '.join(skills[:3])}" if skills else "")

    about = (
        f"I am working towards a role as a {title}. "
        + (f"I have hands-on experience with {', '.join(skills)} through my projects and work. " if skills else "")
        + "[Add what you enjoy building, your strongest project and what you are learning now.]"
    )

    return headline[:MAX_HEADLINE], about


# =========================================
# AI versions
# =========================================

def write_cover_letter(result, resume_text, use_ai=True):
    """
    Returns {"text", "removed", "needs_metric", "ai"}.
    """

    answer = None

    if use_ai:

        requirements = ", ".join(m["requirement"] for m in result.get("mandatory", []))

        prompt = f"""
Write a cover letter for this candidate and job.

JOB TITLE: {clean_text(result.get("job_title"), 200)}
COMPANY: {clean_text(result.get("company"), 200) or "not given"}
JOB REQUIREMENTS: {requirements or "not listed"}

{as_untrusted("resume", resume_text, 8000)}

Rules:
- 3 short paragraphs, 200-300 words, professional and specific.
- Use ONLY facts from the resume. Never add a skill, tool, employer,
  achievement or number that is not in the resume. Where a number would
  help, write [add real number].
- Mention the job's requirements only when the resume shows them.
- Start with "Dear Hiring Manager," and end with the candidate's name.

Return ONLY valid JSON: {{"letter": ""}}
"""

        answer = ask_ai_for_json("You are a careful career coach who never invents facts. Return only valid JSON.",
                                 prompt, cache=False)

    # Keep the AI's paragraph breaks (clean_text would collapse them)

    letter = answer.get("letter") if answer else ""
    letter = letter.strip()[:MAX_LETTER] if isinstance(letter, str) else ""

    if not letter:
        return {"text": _template_letter(result, resume_text), "removed": [], "needs_metric": True, "ai": False}

    text, removed, needs_metric = keep_only_true_facts(letter, resume_text)

    return {"text": text, "removed": removed, "needs_metric": needs_metric, "ai": True}


def write_linkedin(result, resume_text, use_ai=True):
    """
    Returns {"headline", "about", "removed", "needs_metric", "ai"}.
    """

    answer = None

    if use_ai:

        prompt = f"""
Write a LinkedIn headline and "About" section for this candidate, aimed at
roles like: {clean_text(result.get("job_title"), 200) or "their target role"}.

{as_untrusted("resume", resume_text, 8000)}

Rules:
- headline: under 200 characters, e.g. "Backend Developer | Python · Flask · MySQL".
- about: 120-220 words, first person, friendly and professional.
- Use ONLY facts from the resume; never invent skills, employers, awards or
  numbers. Where a number would help, write [add real number].

Return ONLY valid JSON: {{"headline": "", "about": ""}}
"""

        answer = ask_ai_for_json("You are a careful personal-branding coach who never invents facts. Return only valid JSON.",
                                 prompt, cache=False)

    headline = clean_text((answer or {}).get("headline"), MAX_HEADLINE) if answer else ""
    about = (answer or {}).get("about") if answer else ""
    about = about.strip()[:MAX_ABOUT] if isinstance(about, str) else ""

    if not headline or not about:
        headline, about = _template_linkedin(result, resume_text)
        return {"headline": headline, "about": about, "removed": [], "needs_metric": True, "ai": False}

    headline, removed_h, metric_h = keep_only_true_facts(headline, resume_text)
    about, removed_a, metric_a = keep_only_true_facts(about, resume_text)

    if not headline:
        headline = _template_linkedin(result, resume_text)[0]

    return {"headline": headline, "about": about, "removed": removed_h + removed_a,
            "needs_metric": metric_h or metric_a, "ai": True}
