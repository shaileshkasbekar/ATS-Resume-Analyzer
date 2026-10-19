"""
Match a resume against a pasted job description.

1. The AI reads the job description and the resume
   (must-have / nice-to-have skills, relevance, gaps, ...).
2. The code checks each skill in the resume itself, so the
   keyword score does not depend only on what the AI says.
"""

from resume_parser.ai_client import ask_ai_for_json, get_score
from resume_parser.ats_score import LISTED_ONLY_CREDIT
from resume_parser.skill_extractor import (
    extract_skills,
    canonical_skill,
    is_known_skill,
    skill_in_text,
    find_skill_evidence
)


MAX_MUST_HAVE = 15
MAX_NICE_TO_HAVE = 10


def _ai_job_match(resume_text, jd_text, job_title):

    prompt = f"""
You are an expert technical recruiter and ATS system.

Compare the RESUME with the JOB DESCRIPTION.

JOB TITLE (may be empty):
{job_title}

JOB DESCRIPTION:
{jd_text[:8000]}

RESUME:
{resume_text[:8000]}

Rules:
1. must_have_skills: technical skills, tools or technologies the job
   clearly requires. Use short standard names like "React", "SQL",
   "Docker", "REST API". Maximum {MAX_MUST_HAVE}.
2. nice_to_have_skills: skills described as preferred, a plus or bonus.
   Maximum {MAX_NICE_TO_HAVE}.
3. Do not put soft skills (communication, teamwork) in the skill lists.
4. ai_relevance: how well the candidate fits this job overall (0-100).
5. experience_match: how well the candidate's experience level and
   years match what the job asks for (0-100). For freshers applying
   to fresher/intern roles, this can be high.
6. keywords_to_add: important words from the job description that are
   missing from the resume and that the candidate could honestly add.
7. suggested_summary: a 2-3 sentence professional summary for this
   candidate, tailored to this job, using only facts from the resume.

Return ONLY valid JSON with exactly this structure:
{{
    "job_title": "",
    "must_have_skills": [],
    "nice_to_have_skills": [],
    "required_experience": "",
    "ai_relevance": 0,
    "experience_match": 0,
    "strengths": [],
    "gaps": [],
    "recommendations": [],
    "keywords_to_add": [],
    "suggested_summary": ""
}}
"""

    return ask_ai_for_json(
        "You are a professional recruiter and ATS system. Return only valid JSON.",
        prompt
    )


def _clean_skill_list(items, limit):

    result = []
    seen = set()

    for item in items or []:

        if not isinstance(item, str):
            continue

        # "Hibernate/JPA" -> "Hibernate", "JPA"
        # (but keep real names like "CI/CD" or "TCP/IP")

        if "/" in item and not is_known_skill(item):
            parts = item.split("/")
        else:
            parts = [item]

        for part in parts:

            name = canonical_skill(part)

            # Skip empty items and long sentences

            if not name or len(name) > 40 or name.lower() in seen:
                continue

            seen.add(name.lower())
            result.append(name)

    return result[:limit]


def _text_list(items):

    return [str(item) for item in (items or []) if str(item).strip()]


def analyze_job_match(resume_text, jd_text, job_title=""):
    """
    Returns a dict with the score and all details,
    and whether the AI part worked ("ai_available").
    """

    ai = _ai_job_match(resume_text, jd_text, job_title) or {}

    ai_available = bool(ai)

    # -----------------------------------------
    # Skills the job asks for
    # -----------------------------------------

    must_have = _clean_skill_list(ai.get("must_have_skills"), MAX_MUST_HAVE)

    nice_to_have = [
        skill for skill in _clean_skill_list(ai.get("nice_to_have_skills"), MAX_NICE_TO_HAVE)
        if skill.lower() not in {s.lower() for s in must_have}
    ]

    # Known skills found in the job text by the rule-based matcher.
    # Without AI they are the must-haves; with AI, extra ones are nice-to-have.

    rule_skills = extract_skills(jd_text)

    known = {s.lower() for s in must_have + nice_to_have}

    for skill in rule_skills:

        if skill.lower() in known:
            continue

        if ai_available:
            if len(nice_to_have) < MAX_NICE_TO_HAVE:
                nice_to_have.append(skill)
        elif len(must_have) < MAX_MUST_HAVE:
            must_have.append(skill)

        known.add(skill.lower())

    # -----------------------------------------
    # Check each skill in the resume
    # -----------------------------------------

    all_skills = must_have + nice_to_have

    found = [skill for skill in all_skills if skill_in_text(resume_text, skill)]

    evidence = find_skill_evidence(resume_text, found)

    matched = []
    missing = []

    total_weight = 0
    earned_weight = 0

    for skill in all_skills:

        weight = 2 if skill in must_have else 1

        total_weight += weight

        if skill in found:

            matched.append(skill)

            if evidence.get(skill.lower()) == "listed":
                earned_weight += weight * LISTED_ONLY_CREDIT
            else:
                earned_weight += weight

        else:

            missing.append(skill)

    keyword_score = round(earned_weight / total_weight * 100, 2) if total_weight else 0

    # -----------------------------------------
    # Final score
    #
    # Keyword match      50%
    # AI relevance       30%
    # Experience match   20%
    #
    # Without AI: keyword match only
    # -----------------------------------------

    ai_relevance = get_score(ai, "ai_relevance")
    experience_match = get_score(ai, "experience_match")

    if ai_available:
        score = keyword_score * 0.50 + ai_relevance * 0.30 + experience_match * 0.20
    else:
        score = keyword_score

    score = round(min(max(score, 0), 100), 2)

    return {
        "ai_available": ai_available,
        "job_title": (job_title or str(ai.get("job_title") or "")).strip()[:200],
        "score": score,
        "keyword_score": keyword_score,
        "ai_relevance": ai_relevance,
        "experience_match": experience_match,
        "details": {
            "must_have_skills": must_have,
            "nice_to_have_skills": nice_to_have,
            "matched_skills": matched,
            "missing_must_have": [s for s in missing if s in must_have],
            "missing_nice_to_have": [s for s in missing if s not in must_have],
            "skill_evidence": evidence,
            "required_experience": str(ai.get("required_experience") or ""),
            "strengths": _text_list(ai.get("strengths")),
            "gaps": _text_list(ai.get("gaps")),
            "recommendations": _text_list(ai.get("recommendations")),
            "keywords_to_add": _text_list(ai.get("keywords_to_add")),
            "suggested_summary": str(ai.get("suggested_summary") or "")
        }
    }


def plan_skills(details):
    """
    Missing skills + importance, in the shape build_learning_plan expects.
    """

    missing = details["missing_must_have"] + details["missing_nice_to_have"]

    importance = (
        [{"skill_name": s, "importance": "core"} for s in details["missing_must_have"]]
        + [{"skill_name": s, "importance": "supporting"} for s in details["missing_nice_to_have"]]
    )

    return missing, importance
