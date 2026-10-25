"""
Job match entry points used by the routes.

- analyze_job_match: resume vs a real job description (primary feature)
- analyze_role_match: resume vs a predefined role, when there is no JD
"""

from resume_parser.job_requirements import extract_requirements, role_requirements
from resume_parser.job_matcher import run_job_match


def analyze_job_match(resume_text, jd_text, job_title="", company="", use_ai=True):

    requirements = extract_requirements(jd_text, job_title, company, use_ai=use_ai)

    result = run_job_match(resume_text, requirements, jd_text, use_ai=use_ai)

    result["requirements"] = requirements
    result["job_title"] = requirements["job_title"]
    result["company"] = requirements["company"]
    result["source_type"] = "job_description"

    return result


def analyze_role_match(resume_text, role_name, role_skill_groups, use_ai=True):

    requirements = role_requirements(role_name, role_skill_groups, resume_text)

    context = f"Predefined role: {role_name}. No job description was provided."

    result = run_job_match(resume_text, requirements, context, use_ai=use_ai)

    result["requirements"] = requirements
    result["job_title"] = role_name
    result["company"] = ""
    result["source_type"] = "role"

    return result


def plan_skills(result):
    """
    Missing skills + importance, in the shape build_learning_plan expects.
    For "A or B" requirements the first option is suggested.
    """

    missing = []
    importance = []

    for key, level in (("mandatory", "core"), ("preferred", "supporting")):

        for match in result.get(key, []):

            if match.get("status") == "missing" and match.get("any_of"):

                skill = match["any_of"][0]

                missing.append(skill)
                importance.append({"skill_name": skill, "importance": level})

    return missing, importance
