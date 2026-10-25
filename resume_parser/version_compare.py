"""
Compare two resume versions, optionally against the same job.

Uses the rule-based engines only (no AI), so the comparison is
consistent: the same two resumes always give the same result, and
score changes come only from what actually changed in the resume.
"""

from resume_parser.ai_validation import _normalize
from resume_parser.general_analyzer import analyze_resume
from resume_parser.job_matcher import run_job_match
from resume_parser.resume_builder import SECTION_TITLES, to_items
from resume_parser.sections import split_sections
from resume_parser.skill_extractor import extract_skills


EVIDENCE_WORDS = {
    "experience": "work experience",
    "project": "a project",
    "listed": "the skills list only",
    "mentioned": "a mention only",
    "unknown": "the resume",
    "": "nowhere",
}


def _section_items(text):

    parts = split_sections(text)

    return {
        key: [item["text"] for item in to_items(parts.get(key, ""))]
        for key in SECTION_TITLES
    }


def _diff_items(before, after):

    before_norm = {_normalize(x): x for x in before}
    after_norm = {_normalize(x): x for x in after}

    return {
        "added": [after_norm[k] for k in after_norm if k not in before_norm],
        "removed": [before_norm[k] for k in before_norm if k not in after_norm],
    }


def _describe(match):

    if match["status"] == "missing":
        return "missing"

    how = "matched by meaning in" if match["match_type"] == "semantic" else "found in"

    return f"{how} {EVIDENCE_WORDS.get(match['evidence'], match['evidence'])}"


def compare_versions(text_a, text_b, requirements=None):

    skills_a = extract_skills(text_a)
    skills_b = extract_skills(text_b)

    lower_a = {s.lower() for s in skills_a}
    lower_b = {s.lower() for s in skills_b}

    items_a = _section_items(text_a)
    items_b = _section_items(text_b)

    section_changes = []

    for key, title in SECTION_TITLES.items():

        diff = _diff_items(items_a.get(key, []), items_b.get(key, []))

        if diff["added"] or diff["removed"]:
            section_changes.append({"key": key, "title": title, **diff})

    general_a = analyze_resume(text_a)
    general_b = analyze_resume(text_b)

    comparison = {
        "skills_added": [s for s in skills_b if s.lower() not in lower_a],
        "skills_removed": [s for s in skills_a if s.lower() not in lower_b],
        "skills_common": [s for s in skills_b if s.lower() in lower_a],
        "section_changes": section_changes,
        "general": {
            "a": general_a["score"],
            "b": general_b["score"],
            "content_a": general_a["content"],
            "content_b": general_b["content"],
        },
        "job": None,
    }

    if requirements:

        match_a = run_job_match(text_a, requirements, use_ai=False)
        match_b = run_job_match(text_b, requirements, use_ai=False)

        by_requirement = {m["requirement"]: m for m in match_a["mandatory"] + match_a["preferred"]}

        changes = []

        for after in match_b["mandatory"] + match_b["preferred"]:

            before = by_requirement.get(after["requirement"])

            if not before or abs(before["credit"] - after["credit"]) < 0.001:
                continue

            changes.append({
                "requirement": after["requirement"],
                "importance": after["importance"],
                "before": _describe(before),
                "after": _describe(after),
                "points": round(before.get("points_lost", 0) - after.get("points_lost", 0), 1),
                "evidence": after["snippet"],
            })

        changes.sort(key=lambda c: -abs(c["points"]))

        components = []

        for comp_a, comp_b in zip(match_a["components"], match_b["components"]):

            if comp_a["applicable"] or comp_b["applicable"]:
                components.append({
                    "label": comp_b["label"],
                    "a": comp_a["points"],
                    "b": comp_b["points"],
                    "delta": round(comp_b["points"] - comp_a["points"], 1),
                })

        remaining = [
            m["requirement"] + (" (missing)" if m["status"] == "missing" else " (only in skills list)")
            for m in match_b["mandatory"]
            if m["status"] == "missing" or m["evidence"] in ("listed", "mentioned")
        ]

        comparison["job"] = {
            "a": match_a["score"],
            "b": match_b["score"],
            "delta": round(match_b["score"] - match_a["score"], 1),
            "changes": changes,
            "components": components,
            "remaining": remaining,
        }

    return comparison
