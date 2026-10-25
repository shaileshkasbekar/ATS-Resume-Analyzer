"""
Job Match engine: compares a resume with extracted job requirements.

Every requirement gets:
- a match type: exact / alias / semantic / missing
- an evidence level: experience / project / listed / mentioned
- a snippet from the resume that proves it

The score is built from components (see scoring_config.py), and every
lost point is explained. AI output is validated: semantic matches and
strengths are only kept when their quoted evidence really exists in
the resume.
"""

import re
from datetime import date

from resume_parser.ai_client import ask_ai_for_json, as_untrusted
from resume_parser.ai_validation import (
    clean_text,
    clean_text_list,
    clean_score,
    clean_dict_list,
    quote_in_text
)
from resume_parser.job_requirements import EDUCATION_PATTERNS
from resume_parser.scoring_config import (
    SCORING_VERSION,
    COMPONENT_WEIGHTS,
    COMPONENT_LABELS,
    MATCH_TYPE_CREDIT,
    EVIDENCE_CREDIT,
    EDUCATION_LEVELS
)
from resume_parser.sections import split_sections
from resume_parser.skill_extractor import (
    IMPLIED_BY,
    skill_names,
    find_skill_span,
    _word_pattern
)


MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


# =========================================
# Resume preparation
# =========================================

class ResumeView:
    """
    The resume split into the parts the matcher needs.
    """

    def __init__(self, text):

        self.text = text or ""

        sections = split_sections(self.text)

        self.experience = sections.get("experience", "")
        self.projects = sections.get("projects", "")
        self.skills = sections.get("skills", "")
        self.education = sections.get("education", "")

        self.other = "\n".join(
            value for key, value in sections.items()
            if key not in ("experience", "projects", "skills")
        )

        self.has_sections = bool(
            self.experience.strip() or self.projects.strip() or self.skills.strip()
        )

    def section_of(self, quote):
        """
        Evidence level for a quoted piece of the resume.
        """

        if quote_in_text(quote, self.experience):
            return "experience"

        if quote_in_text(quote, self.projects):
            return "project"

        if quote_in_text(quote, self.skills):
            return "listed"

        return "mentioned" if self.has_sections else "unknown"


def _snippet(text, span, max_len=160):
    """
    The resume line around a match.
    """

    start = text.rfind("\n", 0, span[0]) + 1
    end = text.find("\n", span[1])
    end = len(text) if end == -1 else end

    line = re.sub(r"\s+", " ", text[start:end]).strip(" •-–*▪●◦·")

    if len(line) <= max_len:
        return line

    # Keep the part around the match

    position = span[0] - start
    left = max(0, position - max_len // 2)

    return ("…" if left else "") + line[left:left + max_len].strip() + "…"


def _find_in(text, skill):
    """
    (span, snippet) of the skill in a text, or None.
    """

    span = find_skill_span(text, skill)

    if not span:
        return None

    return span, _snippet(text, span)


# =========================================
# Matching one requirement
# =========================================

def match_option(resume, skill):
    """
    How one skill appears in the resume. Returns None if absent.
    """

    if not find_skill_span(resume.text, skill):
        return None

    # Exact if the main name appears, otherwise found via another name

    exact = re.search(_word_pattern(skill), resume.text.lower()) is not None

    match_type = "exact" if exact else "alias"

    # Strongest evidence first

    evidence = None
    via = ""
    snippet = ""

    for level, section_text in (("experience", resume.experience), ("project", resume.projects)):

        found = _find_in(section_text, skill)

        if found:
            evidence, snippet = level, found[1]
            break

        # Framework use proves the language: Spring Boot -> Java

        for proof in IMPLIED_BY.get(skill.lower(), []):

            found = _find_in(section_text, proof)

            if found:
                evidence, snippet, via = level, found[1], proof
                break

        if evidence:
            break

    if not evidence:

        if not resume.has_sections:
            evidence = "unknown"
            snippet = _find_in(resume.text, skill)[1]

        elif _find_in(resume.skills, skill):
            evidence = "listed"
            snippet = _find_in(resume.skills, skill)[1]

        else:
            evidence = "mentioned"
            snippet = _find_in(resume.text, skill)[1]

    return {
        "matched_skill": skill,
        "match_type": match_type,
        "evidence": evidence,
        "evidence_via": via,
        "snippet": snippet,
        "credit": round(MATCH_TYPE_CREDIT[match_type] * EVIDENCE_CREDIT[evidence], 3)
    }


def match_requirement(resume, item, importance):
    """
    Best match among the requirement's alternatives.
    """

    best = None

    for option in item["any_of"]:

        found = match_option(resume, option)

        if found and (best is None or found["credit"] > best["credit"]):
            best = found

    result = {
        "requirement": item["name"],
        "any_of": item["any_of"],
        "category": item.get("category", "skill"),
        "importance": importance,
    }

    if best:
        result.update(best, status="matched", reason="")
    else:
        result.update(
            status="missing", match_type="missing", matched_skill="",
            evidence="", evidence_via="", snippet="", credit=0.0, reason=""
        )

    return result


# =========================================
# Experience / education helpers
# =========================================

def estimate_experience_years(experience_text, today=None):
    """
    Adds up date ranges like "Jan 2023 - Present" or "2021 - 2023"
    in the experience section. Returns years (1 decimal) or None.
    """

    today = today or date.today()

    month = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*"

    pattern = (
        r"(?:" + month + r")?((?:19|20)\d{2})\s*(?:-|–|—|to)\s*"
        r"(?:(?:" + month + r")?((?:19|20)\d{2})|(present|current|now|ongoing|till date))"
    )

    total_months = 0
    found = False

    for match in re.finditer(pattern, (experience_text or "").lower()):

        start_month = MONTHS.get((match.group(1) or "")[:3])
        start_year = int(match.group(2))

        if match.group(5):
            end_year, end_month = today.year, today.month
        else:
            end_year = int(match.group(4))
            end_month = MONTHS.get((match.group(3) or "")[:3])

        if start_month is None and end_month is None:
            start_month = end_month = 1
        else:
            start_month = start_month or 6
            end_month = end_month or 6

        months = (end_year * 12 + end_month) - (start_year * 12 + start_month)

        if 0 <= months <= 600:
            total_months += max(months, 1)
            found = True

    return round(total_months / 12, 1) if found else None


def resume_education_level(resume):
    """
    (level, in_progress) of the highest degree found, or (None, False).
    """

    text = (resume.education or resume.text).lower()

    levels = [
        EDUCATION_LEVELS[level]
        for level, pattern in EDUCATION_PATTERNS
        if level != "bachelor" and re.search(pattern, text)
    ]

    # "degree"/"graduate" alone is too vague in a resume; look for real degree names

    if re.search(r"\bbachelor|\bb\.?\s?tech\b|\bb\.e\b|\bb\.?sc\b|\bbca\b|\bb\.?com\b|\bb\.?a\b", text):
        levels.append(EDUCATION_LEVELS["bachelor"])

    if not levels:
        return None, False

    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", text)]

    in_progress = bool(years) and max(years) > date.today().year

    return max(levels), in_progress


def _words_found(requirement_text, resume_text, min_share=0.6):

    stop = {"certification", "certified", "certificate", "required", "preferred", "with", "from", "plus"}

    words = [w for w in re.findall(r"[a-z0-9]{3,}", requirement_text.lower()) if w not in stop]

    if not words:
        return False

    resume_lower = resume_text.lower()

    return sum(1 for w in words if w in resume_lower) / len(words) >= min_share


# =========================================
# AI assessment (semantic matches + relevance)
# =========================================

def _ai_assessment(resume_text, requirements, context_text, unmatched):

    lines = [
        f"- [{'mandatory' if i < len(requirements['mandatory_skills']) else 'preferred'}] {item['name']}"
        for i, item in enumerate(requirements["mandatory_skills"] + requirements["preferred_skills"])
    ]

    prompt = f"""
Compare the candidate's resume with the job.

JOB TITLE: {clean_text(requirements.get("job_title"), 200)}

JOB REQUIREMENTS (already extracted):
{chr(10).join(lines) or "- none"}

{as_untrusted("job_description", context_text, 6000)}

{as_untrusted("resume", resume_text, 9000)}

Tasks:
1. semantic_matches: ONLY for these unmatched requirements: {", ".join(unmatched) or "none"}.
   Include one only if the resume shows clearly equivalent experience under
   another name. Related but different technologies do NOT count
   (Flask is not Django, MySQL is not MongoDB, Java is not JavaScript).
   evidence_quote must be copied EXACTLY from the resume.
2. overall_relevance: how relevant the candidate is for this job (0-100), with a short reason.
3. experience: how well the work experience / internships match the job (0-100).
   For an entry-level job, internships and strong projects count.
4. projects: how relevant the candidate's projects are to this job (0-100),
   naming the most relevant projects with a quote copied exactly from the resume.
5. strengths: up to 5, each with an evidence_quote copied exactly from the resume.
6. improvements: up to 5 concrete actions. Never suggest inventing experience;
   if a metric is missing, ask the candidate to add a real one.

Return ONLY valid JSON with exactly this structure:
{{
    "semantic_matches": [{{"requirement": "", "evidence_quote": "", "reason": ""}}],
    "overall_relevance": {{"score": 0, "reason": ""}},
    "experience": {{"score": 0, "reason": ""}},
    "projects": {{"score": 0, "reason": "", "relevant_projects": [{{"name": "", "evidence_quote": "", "reason": ""}}]}},
    "strengths": [{{"text": "", "evidence_quote": "", "requirement": ""}}],
    "improvements": [{{"action": "", "reason": "", "requirement": ""}}]
}}
"""

    return ask_ai_for_json(
        "You are a careful technical recruiter. You only make claims you can support "
        "with exact quotes from the resume. Return only valid JSON.",
        prompt
    )


def _section_score(ai, key):

    value = ai.get(key)

    if not isinstance(value, dict):
        return None, ""

    return clean_score(value.get("score")), clean_text(value.get("reason"), 400)


def validate_assessment(ai, resume, unmatched):
    """
    Keeps only the parts of the AI answer that pass validation.
    """

    unmatched_lower = {u.lower(): u for u in unmatched}

    semantic = []

    for item in clean_dict_list(ai.get("semantic_matches"), 20):

        requirement = clean_text(item.get("requirement"), 100)
        quote = clean_text(item.get("evidence_quote"), 400)

        if requirement.lower() in unmatched_lower and quote_in_text(quote, resume.text):
            semantic.append({
                "requirement": unmatched_lower[requirement.lower()],
                "evidence_quote": quote,
                "reason": clean_text(item.get("reason"), 300)
            })

    relevance, relevance_reason = _section_score(ai, "overall_relevance")
    experience, experience_reason = _section_score(ai, "experience")
    projects, projects_reason = _section_score(ai, "projects")

    relevant_projects = []

    if isinstance(ai.get("projects"), dict):

        for item in clean_dict_list(ai["projects"].get("relevant_projects"), 5):

            quote = clean_text(item.get("evidence_quote"), 400)

            if quote_in_text(quote, resume.text):
                relevant_projects.append({
                    "name": clean_text(item.get("name"), 120),
                    "evidence_quote": quote,
                    "reason": clean_text(item.get("reason"), 300)
                })

    strengths = []

    for item in clean_dict_list(ai.get("strengths"), 8):

        quote = clean_text(item.get("evidence_quote"), 400)

        if quote_in_text(quote, resume.text):
            strengths.append({
                "text": clean_text(item.get("text"), 300),
                "evidence": quote,
                "requirement": clean_text(item.get("requirement"), 100)
            })

    improvements = []

    for item in clean_dict_list(ai.get("improvements"), 8):

        action = clean_text(item.get("action"), 300)

        if action:
            improvements.append({
                "action": action,
                "reason": clean_text(item.get("reason"), 300),
                "requirement": clean_text(item.get("requirement"), 100),
                "source": "ai"
            })

    return {
        "semantic_matches": semantic,
        "relevance": relevance,
        "relevance_reason": relevance_reason,
        "experience": experience,
        "experience_reason": experience_reason,
        "projects": projects,
        "projects_reason": projects_reason,
        "relevant_projects": relevant_projects,
        "strengths": [s for s in strengths if s["text"]][:5],
        "improvements": improvements[:5]
    }


# =========================================
# Scoring
# =========================================

def _coverage(matches):
    """
    0-100 coverage of a requirement list, or None if empty.
    Each requirement counts once (duplicates were merged earlier).
    """

    if not matches:
        return None

    return round(sum(m["credit"] for m in matches) / len(matches) * 100, 2)


def build_components(values, explanations):
    """
    values: {component: score or None (not applicable)}.
    Weights of applicable components are scaled to 100.
    """

    applicable = {k: v for k, v in values.items() if v is not None}

    total_weight = sum(COMPONENT_WEIGHTS[k] for k in applicable) or 1

    components = []
    final = 0.0

    for key, weight in COMPONENT_WEIGHTS.items():

        score = values.get(key)

        if score is None:

            components.append({
                "key": key, "label": COMPONENT_LABELS[key], "weight": weight,
                "applicable": False, "score": None, "max_points": 0, "points": 0,
                "explanation": explanations.get(key, "Not applicable for this job.")
            })
            continue

        max_points = weight / total_weight * 100
        points = max_points * score / 100
        final += points

        components.append({
            "key": key, "label": COMPONENT_LABELS[key], "weight": weight,
            "applicable": True, "score": round(score, 1),
            "max_points": round(max_points, 1), "points": round(points, 1),
            "explanation": explanations.get(key, "")
        })

    return round(min(max(final, 0), 100), 2), components


def _plural(n, word):

    return f"{n} {word}{'' if n == 1 else 's'}"


# =========================================
# Main entry point
# =========================================

def run_job_match(resume_text, requirements, context_text="", use_ai=True):
    """
    Returns the full job match result (stored as JSON in history).
    """

    resume = ResumeView(resume_text)

    mandatory = [match_requirement(resume, item, "mandatory") for item in requirements["mandatory_skills"]]
    preferred = [match_requirement(resume, item, "preferred") for item in requirements["preferred_skills"]]

    unmatched = [m["requirement"] for m in mandatory + preferred if m["status"] == "missing"]

    # ---------------- AI assessment ----------------

    ai_raw = _ai_assessment(resume_text, requirements, context_text, unmatched) if use_ai else None

    ai_available = bool(ai_raw)

    ai = validate_assessment(ai_raw or {}, resume, unmatched)

    # Semantic matches: verified quotes only, partial credit

    for semantic in ai["semantic_matches"]:

        for m in mandatory + preferred:

            if m["requirement"] == semantic["requirement"] and m["status"] == "missing":

                evidence = resume.section_of(semantic["evidence_quote"])

                m.update(
                    status="matched", match_type="semantic", matched_skill="",
                    evidence=evidence, snippet=semantic["evidence_quote"],
                    reason=semantic["reason"],
                    credit=round(MATCH_TYPE_CREDIT["semantic"] * EVIDENCE_CREDIT[evidence], 3)
                )

    # ---------------- Component scores ----------------

    values = {}
    explanations = {}

    values["required_skills"] = _coverage(mandatory)
    values["preferred_skills"] = _coverage(preferred)

    for key, matches in (("required_skills", mandatory), ("preferred_skills", preferred)):

        if not matches:
            explanations[key] = "The job does not list any." if key == "preferred_skills" else "No required skills could be extracted."
            continue

        full = sum(1 for m in matches if m["credit"] >= 1)
        partial = sum(1 for m in matches if 0 < m["credit"] < 1)
        missing = sum(1 for m in matches if m["status"] == "missing")

        explanations[key] = (
            f"{_plural(full, 'requirement')} fully shown, {partial} with partial credit "
            f"(only listed, only mentioned or matched by meaning), {missing} missing."
        )

    # Overall relevance (AI only)

    values["semantic_relevance"] = ai["relevance"] if ai_available else None
    explanations["semantic_relevance"] = ai["relevance_reason"] if ai_available else "AI unavailable, so this part was skipped."

    # Experience

    required_years = requirements.get("experience", {}).get("min_years")
    candidate_years = estimate_experience_years(resume.experience)

    rule_experience = None

    if required_years is not None:

        if required_years == 0:
            rule_experience = 100.0
        else:
            rule_experience = round(min(1.0, (candidate_years or 0) / required_years) * 100, 1)

    ai_experience = ai["experience"] if ai_available else None

    known = [v for v in (rule_experience, ai_experience) if v is not None]

    values["experience"] = round(sum(known) / len(known), 1) if known else None

    experience_parts = []

    if required_years is not None:
        experience_parts.append(
            "Entry-level role." if required_years == 0 else f"Job asks for {required_years:g}+ years."
        )
        experience_parts.append(
            f"Your resume shows about {candidate_years:g} years in dated experience entries."
            if candidate_years is not None else "No dated work experience was found in your resume."
        )

    if ai_experience is not None and ai["experience_reason"]:
        experience_parts.append(ai["experience_reason"])

    explanations["experience"] = " ".join(experience_parts) or "The job does not state an experience requirement."

    # Projects

    all_matches = mandatory + preferred

    if ai_available and ai["projects"] is not None:

        values["projects"] = ai["projects"]
        explanations["projects"] = ai["projects_reason"]

    elif all_matches and (resume.projects.strip() or resume.experience.strip()):

        shown = sum(1 for m in all_matches if m["evidence"] in ("project", "experience"))

        values["projects"] = round(shown / len(all_matches) * 100, 1)
        explanations["projects"] = f"{shown} of {len(all_matches)} job skills are shown in your projects or experience."

    else:

        values["projects"] = None
        explanations["projects"] = "No projects section found, or no skills to compare."

    # Qualifications (only when the job asks for them)

    qualification_checks = []

    education = {"required_level": requirements.get("education_required_level"), "resume_level": None, "met": None, "in_progress": False}

    if education["required_level"] is not None:

        level, in_progress = resume_education_level(resume)

        education.update(resume_level=level, in_progress=in_progress)

        if level is None:
            education["met"] = False
            qualification_checks.append(0.0)
        elif level >= education["required_level"]:
            education["met"] = True
            qualification_checks.append(100.0)
        else:
            education["met"] = False
            qualification_checks.append(40.0)

    certifications = []

    for cert in requirements.get("certifications_required", []):

        met = _words_found(cert, resume_text)
        certifications.append({"requirement": cert, "met": met})
        qualification_checks.append(100.0 if met else 0.0)

    values["qualifications"] = round(sum(qualification_checks) / len(qualification_checks), 1) if qualification_checks else None

    qualification_parts = []

    if education["met"] is True:
        qualification_parts.append("Degree requirement met" + (" (degree in progress)." if education["in_progress"] else "."))
    elif education["met"] is False:
        qualification_parts.append("Degree requirement not clearly met.")

    if certifications:
        qualification_parts.append(f"{sum(1 for c in certifications if c['met'])} of {len(certifications)} required certifications found.")

    explanations["qualifications"] = " ".join(qualification_parts) or "The job does not ask for a specific degree or certification."

    score, components = build_components(values, explanations)

    # ---------------- Deductions ----------------

    deductions = []

    for component in components:

        if component["applicable"] and component["points"] < component["max_points"] - 0.05:

            deductions.append({
                "component": component["label"],
                "points": round(component["max_points"] - component["points"], 1),
                "reason": component["explanation"]
            })

    deductions.sort(key=lambda d: -d["points"])

    # Points lost per required skill

    required_component = next(c for c in components if c["key"] == "required_skills")

    for m in mandatory:
        m["points_lost"] = round(required_component["max_points"] / len(mandatory) * (1 - m["credit"]), 1) if mandatory else 0

    for m in preferred:
        preferred_component = next(c for c in components if c["key"] == "preferred_skills")
        m["points_lost"] = round(preferred_component["max_points"] / len(preferred) * (1 - m["credit"]), 1)

    # ---------------- Strengths and actions ----------------

    strengths = [
        {
            "text": f"{m['matched_skill'] or m['requirement']} shown in your {('work experience' if m['evidence'] == 'experience' else 'projects')}",
            "evidence": m["snippet"],
            "requirement": m["requirement"]
        }
        for m in mandatory
        if m["status"] == "matched" and m["evidence"] in ("experience", "project") and m["match_type"] != "semantic"
    ][:5]

    # AI strengths: only real sentences, not single skill names

    strengths += [s for s in ai["strengths"] if len(s["text"]) >= 20]

    actions = []

    for m in sorted(mandatory, key=lambda x: -x["points_lost"]):

        if m["status"] == "missing":
            actions.append({
                "action": f"If you have used {m['requirement']}, add it to a project or experience bullet that shows what you built with it. If not, it is a skill gap (see your learning plan).",
                "reason": f"Required by the job and not found in your resume (−{m['points_lost']} points).",
                "requirement": m["requirement"], "source": "rules"
            })
        elif m["evidence"] in ("listed", "mentioned"):
            actions.append({
                "action": f"Show {m['matched_skill'] or m['requirement']} in a project or experience bullet, not only in your skills list.",
                "reason": f"Skills only listed get partial credit (−{m['points_lost']} points).",
                "requirement": m["requirement"], "source": "rules"
            })
        elif m["match_type"] == "semantic":
            actions.append({
                "action": f"Use the exact term \"{m['requirement']}\" where you describe this work.",
                "reason": "It was matched only by meaning; many ATS systems look for the exact keyword.",
                "requirement": m["requirement"], "source": "rules"
            })

    if required_years and candidate_years is not None and candidate_years < required_years:
        actions.append({
            "action": "Make sure every internship and job has clear start and end dates, and highlight projects that show similar responsibility.",
            "reason": f"The job asks for {required_years:g}+ years; your resume shows about {candidate_years:g}.",
            "requirement": "Experience", "source": "rules"
        })

    if education["met"] is False:
        actions.append({
            "action": "Make your degree, branch and graduation year clearly visible in the Education section.",
            "reason": "The job asks for a degree and it was not clearly found.",
            "requirement": "Education", "source": "rules"
        })

    missing_preferred = [m["requirement"] for m in preferred if m["status"] == "missing"]

    if missing_preferred:
        actions.append({
            "action": "Optional: mention " + ", ".join(missing_preferred[:5]) + " if you have real experience with them.",
            "reason": "Preferred by the job; they add points but are not required.",
            "requirement": "Preferred skills", "source": "rules"
        })

    actions = (actions[:7] + ai["improvements"])[:10]

    return {
        "scoring_version": SCORING_VERSION,
        "ai_available": ai_available,
        "score": score,
        "components": components,
        "deductions": deductions,
        "mandatory": mandatory,
        "preferred": preferred,
        "experience": {
            "required_years": required_years,
            "required_text": requirements.get("experience", {}).get("text", ""),
            "candidate_years": candidate_years
        },
        "education": education,
        "certifications": certifications,
        "relevant_projects": ai["relevant_projects"],
        "strengths": strengths,
        "actions": actions
    }
