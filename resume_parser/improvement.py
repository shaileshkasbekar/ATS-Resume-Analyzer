"""
AI Resume Improvement Assistant.

Generates rewrite suggestions for a resume, aimed at a target job.
Every suggestion is validated so nothing is invented:

- "original" must really exist in the resume
- "improved" may not introduce skills the resume does not have
- numbers that were not in the original are replaced with a
  placeholder, so the user adds a real metric
"""

import re

from resume_parser.ai_client import ask_ai_for_json, as_untrusted
from resume_parser.ai_validation import clean_text, clean_dict_list, quote_in_text
from resume_parser.skill_extractor import extract_skills
from resume_parser.sections import split_sections
from resume_parser.general_analyzer import WEAK_PHRASES, ACTION_VERBS, BULLET_CHARS


KINDS = ("summary", "experience", "project", "skills", "advice")

KIND_LABELS = {
    "summary": "Professional summary",
    "experience": "Experience bullet",
    "project": "Project description",
    "skills": "Skills section",
    "advice": "How to show a skill",
}

METRIC_PLACEHOLDER = "[add real number]"

MAX_SUGGESTIONS = 10


def _numbers(text):

    return set(re.findall(r"\d+(?:[.,]\d+)?", text or ""))


def remove_invented_numbers(improved, allowed_text):
    """
    Replaces numbers that do not appear in allowed_text with a
    placeholder. Digits inside names (Python3, EC2, HTML5) are left alone.
    Returns (text, needs_metric).
    """

    allowed = _numbers(allowed_text)

    needs_metric = False

    def replace(match):

        nonlocal needs_metric

        if match.group(1) in allowed:
            return match.group(0)

        needs_metric = True

        return METRIC_PLACEHOLDER

    text = re.sub(
        r"(?<![\w.])(\d+(?:[.,]\d+)?)(\s*(?:%|\+|x|k))?(?![A-Za-z])",
        replace,
        improved
    )

    return text, needs_metric or METRIC_PLACEHOLDER in text


def validate_suggestions(raw, resume_text, missing_requirements=()):
    """
    Keeps only safe suggestions from the AI answer.
    """

    resume_skills = {s.lower() for s in extract_skills(resume_text)}

    result = []
    seen = set()

    for item in clean_dict_list(raw, MAX_SUGGESTIONS * 2):

        kind = clean_text(item.get("kind"), 20).lower()
        kind = kind if kind in KINDS else "experience"

        original = clean_text(item.get("original"), 800)
        improved = clean_text(item.get("improved"), 800)

        if not improved:
            continue

        # The original text must exist (a brand-new summary or advice may have none)

        if original and not quote_in_text(original, resume_text):
            continue

        if not original and kind not in ("summary", "advice"):
            continue

        evidence = clean_text(item.get("evidence"), 400)

        if evidence and not quote_in_text(evidence, resume_text):
            evidence = ""

        # No new skills. A rewritten bullet may only mention skills from that
        # bullet (or its verified evidence) — adding "Docker" to a project
        # that never used Docker would invent experience. Summaries and the
        # skills section may use any skill from the resume. Advice may name
        # a missing skill to learn.

        if kind in ("experience", "project"):
            allowed_skills = {s.lower() for s in extract_skills(original + " " + evidence)}
        else:
            allowed_skills = resume_skills

        if kind != "advice":

            new_skills = {s.lower() for s in extract_skills(improved)} - allowed_skills

            if new_skills:
                continue

        # No invented numbers

        allowed = original if original else resume_text

        improved, needs_metric = remove_invented_numbers(improved, allowed)

        key = (kind, original.lower() or improved.lower())

        if key in seen:
            continue

        seen.add(key)

        result.append({
            "kind": kind,
            "original": original,
            "improved": improved,
            "reason": clean_text(item.get("reason"), 400),
            "requirement": clean_text(item.get("requirement"), 200),
            "evidence": evidence,
            "needs_metric": needs_metric
        })

        if len(result) >= MAX_SUGGESTIONS:
            break

    return result


def _ai_suggestions(resume_text, job_title, requirements_text, gaps_text):

    prompt = f"""
Improve this resume for the target job. Suggest specific rewrites.

TARGET JOB: {job_title or "not specified"}

JOB REQUIREMENTS:
{requirements_text}

GAPS FOUND BY THE ANALYZER:
{gaps_text}

{as_untrusted("resume", resume_text, 9000)}

Rules (very important):
1. "original" must be copied EXACTLY from the resume (one bullet or sentence).
2. "improved" may only use facts that are already in the resume.
   NEVER add a skill, tool, company, achievement, certification or number
   that is not in the resume. If a metric would help, write [add real number].
3. Use strong action verbs, remove vague words and repetition, fix grammar,
   and use the job's exact keywords only where the resume already supports them.
4. kind is one of: summary, experience, project, skills, advice.
   - summary: rewrite the professional summary (original may be "" if there is none)
   - advice: how to demonstrate a missing or weakly shown requirement
     (original ""), e.g. "If you used Docker in project X, add a bullet saying ..."
5. requirement: the job requirement this helps with (or "").
6. evidence: an exact quote from the resume that supports the improved text (or "").
7. Up to {MAX_SUGGESTIONS} suggestions, most useful first.

Return ONLY valid JSON:
{{
    "suggestions": [
        {{"kind": "", "original": "", "improved": "", "reason": "", "requirement": "", "evidence": ""}}
    ]
}}
"""

    answer = ask_ai_for_json(
        "You are a careful resume editor. You improve wording without ever inventing facts. Return only valid JSON.",
        prompt
    )

    return (answer or {}).get("suggestions") if answer else None


def _rule_suggestions(resume_text, result):
    """
    Suggestions without AI: weak bullets and skills that are only listed.
    """

    suggestions = []

    for line in resume_text.splitlines():

        clean = line.strip().lstrip(BULLET_CHARS).strip()
        lower = clean.lower()

        weak = next((p for p in WEAK_PHRASES if p in lower), None)

        if weak and len(clean) > 20:
            suggestions.append({
                "kind": "advice",
                "original": clean,
                "improved": f"Rewrite without \"{weak}\": start with an action verb (Built, Developed, Led), say what you did and add the result with a real number.",
                "reason": f"\"{weak}\" describes duties, not achievements.",
                "requirement": "",
                "evidence": clean,
                "needs_metric": True
            })

    for match in result.get("mandatory", []):

        if match.get("status") == "matched" and match.get("evidence") in ("listed", "mentioned"):

            skill = match.get("matched_skill") or match["requirement"]

            suggestions.append({
                "kind": "advice",
                "original": "",
                "improved": f"If you used {skill} in a project or job, add a bullet there that says what you built with it and the result.",
                "reason": f"{skill} is only listed, so it gets partial credit for this job.",
                "requirement": match["requirement"],
                "evidence": match.get("snippet", ""),
                "needs_metric": False
            })

    return suggestions[:MAX_SUGGESTIONS]


def generate_suggestions(resume_text, result):
    """
    Returns (suggestions, used_ai).
    """

    requirements = result.get("mandatory", []) + result.get("preferred", [])

    requirements_text = "\n".join(
        f"- [{m['importance']}] {m['requirement']}" for m in requirements
    ) or "- none"

    gaps = [
        f"- {m['requirement']}: {'missing' if m['status'] == 'missing' else 'only ' + m['evidence']}"
        for m in result.get("mandatory", [])
        if m["status"] == "missing" or m.get("evidence") in ("listed", "mentioned")
    ]

    raw = _ai_suggestions(resume_text, result.get("job_title"), requirements_text, "\n".join(gaps) or "- none")

    if raw is None:
        return _rule_suggestions(resume_text, result), False

    missing = [m["requirement"] for m in requirements if m["status"] == "missing"]

    return validate_suggestions(raw, resume_text, missing), True
