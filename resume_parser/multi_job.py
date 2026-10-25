"""
Compare one resume against several saved jobs.

Uses each job's saved requirements and the rule-based matcher (no AI),
so all jobs are scored the same way and the comparison is quick.
"""

from collections import Counter

from resume_parser.jd_analyzer import analyze_role_match
from resume_parser.job_matcher import run_job_match


def _key(match):

    return " or ".join(sorted(s.lower() for s in match["any_of"]))


def compare_jobs(resume_text, jobs, roles=None):
    """
    jobs: [{"job_id", "title", "company", "requirements"}]
    roles: optional {role_name: role_skill_groups} for role suggestions.
    """

    rows = []

    required_counter = Counter()
    names = {}

    for job in jobs:

        result = run_job_match(resume_text, job["requirements"], use_ai=False)

        mandatory = result["mandatory"]
        preferred = result["preferred"]

        for m in mandatory:
            required_counter[_key(m)] += 1
            names[_key(m)] = m["requirement"]

        experience = next(c for c in result["components"] if c["key"] == "experience")

        rows.append({
            "job_id": job["job_id"],
            "title": job["title"] or "Untitled job",
            "company": job["company"] or "",
            "score": result["score"],
            "required_matched": sum(1 for m in mandatory if m["status"] == "matched"),
            "required_total": len(mandatory),
            "preferred_matched": sum(1 for m in preferred if m["status"] == "matched"),
            "preferred_total": len(preferred),
            "missing_critical": [m["requirement"] for m in mandatory if m["status"] == "missing"],
            "experience": experience["score"] if experience["applicable"] else None,
            "experience_note": experience["explanation"],
            "top_actions": [a["action"] for a in result["actions"][:2]],
            "_keys": {_key(m) for m in mandatory},
        })

    rows.sort(key=lambda r: -r["score"])

    common = [names[k] for k, n in required_counter.most_common() if n >= 2]

    for row in rows:
        row["unique_skills"] = [names[k] for k in row.pop("_keys") if required_counter[k] == 1]

    # Skills that would raise several jobs at once

    missing_counter = Counter(skill for row in rows for skill in row["missing_critical"])

    shared_gaps = [skill for skill, n in missing_counter.most_common() if n >= 2]

    suggested_roles = []

    for role_name, groups in (roles or {}).items():

        role_result = analyze_role_match(resume_text, role_name, groups, use_ai=False)

        suggested_roles.append({"role": role_name, "score": role_result["score"]})

    suggested_roles.sort(key=lambda r: -r["score"])

    return {
        "rows": rows,
        "common_skills": common,
        "shared_gaps": shared_gaps,
        "suggested_roles": suggested_roles[:3],
    }
