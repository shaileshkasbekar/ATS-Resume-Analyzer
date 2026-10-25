"""
Prepares a saved job match result for the redesigned result page.

Only re-arranges data that already exists in the result (no new scoring):
- a short, evidence-based interpretation
- the three priority actions, each with evidence and a working action
- skills grouped into matched / partial / missing required / missing preferred
- an evidence row per requirement, with an honest uncertainty note
"""

EVIDENCE_SECTION = {
    "experience": "Work experience",
    "project": "Projects",
    "listed": "Skills list",
    "mentioned": "Elsewhere (summary or other)",
    "unknown": "Resume (section not detected)",
}

MATCH_LABEL = {
    "exact": "Exact match",
    "alias": "Alias match",
    "semantic": "Matched by meaning",
    "missing": "Missing",
}


def uncertainty(match):
    """
    How sure we are about this requirement, in plain words.
    """

    if match["status"] == "missing":
        return "Not found. If you have this skill, it is not visible in your resume."

    if match["match_type"] == "semantic":
        return "Judged by AI from related wording. The quote is verified, but check it is really the same skill."

    if match["evidence"] == "listed":
        return "Only listed in skills, with no project or job showing it."

    if match["evidence"] == "mentioned":
        return "Mentioned, but not shown in a project or job."

    if match["evidence"] == "unknown":
        return "Found, but resume sections could not be detected."

    if match.get("evidence_via"):
        return f"Shown through {match['evidence_via']}, which uses it."

    return "Clearly shown."


def interpretation(result):

    mandatory = result.get("mandatory", [])

    shown = [m for m in mandatory if m["status"] == "matched" and m.get("evidence") in ("experience", "project")]
    partial = [m for m in mandatory if m["status"] == "matched" and m not in shown]
    missing = [m for m in mandatory if m["status"] == "missing"]

    parts = []

    if mandatory:
        parts.append(
            f"Your resume clearly shows {len(shown)} of {len(mandatory)} required skills"
            + (f", {len(partial)} more only weakly" if partial else "")
            + "."
        )

    if missing:
        names = ", ".join(m["requirement"] for m in missing[:3])
        parts.append(f"Missing: {names}{' and more' if len(missing) > 3 else ''}.")

    experience = result.get("experience", {})
    required = experience.get("required_years")
    candidate = experience.get("candidate_years")

    if required:
        if candidate is None:
            parts.append(f"The job asks for {required:g}+ years; no dated work experience was found.")
        elif candidate < required:
            parts.append(f"The job asks for {required:g}+ years; your resume shows about {candidate:g}.")

    if result.get("education", {}).get("met") is False:
        parts.append("The degree requirement is not clearly met.")

    return " ".join(parts) or "No specific requirements could be extracted from this job."


def priority_actions(result, jd_result_id, can_use_tools, has_roadmap):
    """
    The three most important improvements, from the result's own actions.
    """

    matches = {m["requirement"]: m for m in result.get("mandatory", []) + result.get("preferred", [])}

    priorities = []

    for action in result.get("actions", []):

        if len(priorities) == 3:
            break

        requirement = action.get("requirement", "")
        match = matches.get(requirement)

        if match and match["status"] == "missing":
            evidence = "Not found anywhere in your resume."
        elif match:
            evidence = f"Found in: {EVIDENCE_SECTION.get(match['evidence'], 'resume')} — \"{match['snippet']}\""
        else:
            evidence = ""

        buttons = []

        if can_use_tools and jd_result_id:

            buttons.append({"label": "Fix with the assistant", "url": f"/assistant/{jd_result_id}", "icon": "fa-wand-magic-sparkles"})

            if match and match["status"] == "missing" and match["importance"] == "mandatory" and not has_roadmap:
                buttons.append({"label": "Add to learning roadmap", "url": f"/roadmap/create/{jd_result_id}",
                                "icon": "fa-graduation-cap", "post": True})

        if not buttons:
            buttons.append({"label": "See the requirements", "url": "#skills", "icon": "fa-list-check"})

        priorities.append({
            "title": action["action"],
            "why": action.get("reason", ""),
            "evidence": evidence,
            "requirement": requirement,
            "high": bool(match and match["status"] == "missing" and match["importance"] == "mandatory"),
            "source": action.get("source", "rules"),
            "buttons": buttons,
        })

    return priorities


def skill_groups(result):

    def full(m):
        return m["status"] == "matched" and m["match_type"] != "semantic" and m.get("evidence") in ("experience", "project")

    everything = result.get("mandatory", []) + result.get("preferred", [])

    return {
        "matched": [m for m in everything if full(m)],
        "partial": [m for m in everything if m["status"] == "matched" and not full(m)],
        "missing_required": [m for m in result.get("mandatory", []) if m["status"] == "missing"],
        "missing_preferred": [m for m in result.get("preferred", []) if m["status"] == "missing"],
    }


def evidence_rows(result):

    rows = []

    for m in result.get("mandatory", []) + result.get("preferred", []):

        rows.append({
            "requirement": m["requirement"],
            "importance": "Required" if m["importance"] == "mandatory" else "Preferred",
            "section": EVIDENCE_SECTION.get(m.get("evidence"), "—") if m["status"] == "matched" else "—",
            "text": m.get("snippet") or "",
            "classification": MATCH_LABEL.get(m.get("match_type"), m.get("match_type")),
            "missing": m["status"] == "missing",
            "uncertainty": uncertainty(m),
            "reason": m.get("reason", ""),
        })

    return rows
