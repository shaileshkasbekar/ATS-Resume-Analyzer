"""
Tools: the existing project functions, exposed to the LLM.

An agent cannot run Python by itself. It can only *ask* for a tool by name
with JSON arguments ("function calling"). This file defines, for every tool:

    name         what the LLM writes to call it
    description  when to use it (the LLM reads this to decide)
    parameters   JSON schema of the arguments the LLM must send
    run          the Python function that does the real work

The heavy work is done by the existing, tested code in resume_parser/
(skill matching, the Job Match engine, validated suggestions, roadmap ...).
The LLM decides WHICH tool to use and WHEN; scores and matches always
come from the rule engine, never from the LLM's imagination.

Large inputs (resume text, job description) are not sent through the LLM
as arguments. They live in the AgentContext, which every tool receives.
"""

import json

from models.database import get_db_connection
from models import repository

from resume_parser.career import build_roadmap, gaps, recommend_projects
from resume_parser.general_analyzer import analyze_resume
from resume_parser.improvement import generate_suggestions
from resume_parser.job_matcher import run_job_match
from resume_parser.job_requirements import extract_requirements, role_requirements
from resume_parser.jd_analyzer import plan_skills
from resume_parser.recommendation import build_learning_plan
from resume_parser.sections import split_sections
from resume_parser.skill_extractor import extract_skills, find_skill_evidence

from agents import memory


MAX_RESULT_CHARS = 3500


class ToolError(Exception):
    """A problem the agent can fix (wrong order, bad argument). Sent back to the LLM."""


class AgentContext:
    """
    Everything the tools share during one run.
    """

    def __init__(self, user_id, resume_text, jd_text="", job_title="", use_ai=True, links=None):

        self.user_id = user_id
        self.resume_text = resume_text or ""
        self.jd_text = jd_text or ""
        self.job_title = job_title or ""
        self.use_ai = use_ai
        self.links = links or []

        self.requirements = None    # extracted job requirements
        self.match = None           # latest job match result (full)
        self.role_groups = None     # skill groups when matched against a role
        self.gaps = None            # prioritised skill gaps

        self.artifacts = {}         # tool name -> compact result for the page


# =========================================================
# Helpers
# =========================================================

def _need_match(ctx):

    if not ctx.match:
        raise ToolError(
            "No job match yet. First call match_resume_to_job (when a job description "
            "was given) or match_resume_to_role / suggest_best_role."
        )


def _role_rows(role_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT jr.role_id, jr.role_name, rsg.group_id, rsg.group_name, rsg.group_type,
                   jrs.skill_name, jrs.importance, jrs.weight
            FROM job_roles jr
            JOIN role_skill_groups rsg ON jr.role_id = rsg.role_id
            JOIN job_role_skills jrs ON rsg.group_id = jrs.group_id
            WHERE jr.role_id = %s
            ORDER BY rsg.group_id, jrs.id
            """,
            (role_id,)
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def _all_roles():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT role_id, role_name FROM job_roles ORDER BY role_name")
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def _find_role(name):

    name = (name or "").strip().lower()
    roles = _all_roles()

    for role in roles:
        if role["role_name"].lower() == name:
            return role

    for role in roles:
        if name and (name in role["role_name"].lower() or role["role_name"].lower() in name):
            return role

    words = set(name.replace("-", " ").split())

    best = max(roles, key=lambda r: len(words & set(r["role_name"].lower().split())), default=None)

    if best and words & set(best["role_name"].lower().split()):
        return best

    return None


def _match_summary(result):
    """
    The job match result, small enough for the LLM to read.
    """

    def items(key):
        return [
            {
                "requirement": m["requirement"],
                "status": m["status"],
                "how": m.get("match_type") or "",
                "evidence": m.get("evidence") or "",
                "points_lost": m.get("points_lost", 0),
            }
            for m in result.get(key, [])
        ]

    return {
        "job_title": result.get("job_title"),
        "score": result.get("score"),
        "score_parts": [
            {"part": c["label"], "score": c["score"], "explanation": c["explanation"]}
            for c in result.get("components", []) if c.get("applicable")
        ],
        "required": items("mandatory"),
        "preferred": items("preferred"),
        "experience": result.get("experience"),
        "education_met": (result.get("education") or {}).get("met"),
    }


# =========================================================
# Resume Analysis tools
# =========================================================

def get_resume_profile(ctx):

    text = ctx.resume_text

    if not text.strip():
        raise ToolError("No resume text is available.")

    skills = extract_skills(text)
    evidence = find_skill_evidence(text, skills)
    sections = split_sections(text)
    general = analyze_resume(text, ctx.links)

    education_lines = [line.strip() for line in sections.get("education", "").splitlines() if line.strip()][:3]

    profile = {
        "experience_level": general["experience_level"],
        "sections_present": [k for k, v in general["sections"].items() if v],
        "sections_missing": [k for k, v in general["sections"].items() if not v],
        "skills_used_in_projects_or_work": [s for s in skills if evidence.get(s.lower()) == "used"],
        "skills_only_listed": [s for s in skills if evidence.get(s.lower()) == "listed"],
        "education": education_lines,
        "contact": {"email": general["email"], "phone": general["phone"],
                    "linkedin": general["linkedin"], "github": general["github"]},
        "word_count": general["word_count"],
    }

    ctx.artifacts["profile"] = profile

    return profile


def check_resume_quality(ctx):

    general = analyze_resume(ctx.resume_text, ctx.links)

    quality = {
        "quality_score": general["score"],
        "confirmed_issues": [i["text"] for i in general["issues"]["confirmed"]][:6],
        "potential_issues": [i["text"] for i in general["issues"]["potential"]][:6],
        "recommendations": general["recommendations"][:6],
    }

    ctx.artifacts["quality"] = quality

    return quality


# =========================================================
# Job Matching tools
# =========================================================

def list_job_roles(ctx):

    return {"roles": [r["role_name"] for r in _all_roles()]}


def extract_job_requirements(ctx):

    if not ctx.jd_text.strip():
        raise ToolError("No job description was given. Use match_resume_to_role or suggest_best_role instead.")

    ctx.requirements = extract_requirements(ctx.jd_text, ctx.job_title, "", use_ai=ctx.use_ai)

    req = ctx.requirements

    summary = {
        "job_title": req.get("job_title"),
        "required_skills": [m["name"] for m in req["mandatory_skills"]],
        "preferred_skills": [m["name"] for m in req["preferred_skills"]],
        "experience": (req.get("experience") or {}).get("text", ""),
        "education": req.get("education"),
        "soft_skills": req.get("soft_skills", [])[:6],
    }

    ctx.artifacts["requirements"] = summary

    return summary


def match_resume_to_job(ctx):

    if not ctx.jd_text.strip():
        raise ToolError("No job description was given. Use match_resume_to_role or suggest_best_role instead.")

    if ctx.requirements is None:
        extract_job_requirements(ctx)

    result = run_job_match(ctx.resume_text, ctx.requirements, ctx.jd_text, use_ai=ctx.use_ai)
    result["requirements"] = ctx.requirements
    result["job_title"] = ctx.requirements.get("job_title") or ctx.job_title or "Target job"

    ctx.match = result
    ctx.role_groups = None

    summary = _match_summary(result)
    ctx.artifacts["match"] = summary

    return summary


def match_resume_to_role(ctx, role_name):

    # The user gave a real job posting: matching a generic role would answer the wrong question
    if ctx.jd_text.strip():
        raise ToolError("A job description was given. Use match_resume_to_job: it matches the real posting.")

    role = _find_role(role_name)

    if not role:
        raise ToolError(f"Unknown role '{role_name}'. Call list_job_roles to see the available roles.")

    rows = _role_rows(role["role_id"])

    requirements = role_requirements(role["role_name"], rows, ctx.resume_text)

    result = run_job_match(ctx.resume_text, requirements,
                           f"Predefined role: {role['role_name']}. No job description was provided.",
                           use_ai=ctx.use_ai)
    result["requirements"] = requirements
    result["job_title"] = role["role_name"]

    ctx.requirements = requirements
    ctx.match = result
    ctx.role_groups = rows

    summary = _match_summary(result)
    ctx.artifacts["match"] = summary

    return summary


def suggest_best_role(ctx):
    """
    Rule-based match against every predefined role (fast, no AI), best first.
    """

    scores = []

    for role in _all_roles():

        rows = _role_rows(role["role_id"])

        if not rows:
            continue

        requirements = role_requirements(role["role_name"], rows, ctx.resume_text)
        result = run_job_match(ctx.resume_text, requirements, "", use_ai=False)

        scores.append({"role": role["role_name"], "score": result["score"]})

    scores.sort(key=lambda s: -s["score"])

    ctx.artifacts["role_fit"] = scores[:5]

    return {"best_roles": scores[:5],
            "note": "Rule-based scores. Call match_resume_to_role with the chosen role for the full match."}


def get_past_analyses(ctx):

    rows = repository.list_jd_results(ctx.user_id, limit=5) if ctx.user_id else []

    return {"past_job_matches": [
        {"job": r.get("job_title"), "score": float(r["score"]) if r.get("score") is not None else None,
         "date": str(r.get("created_at"))[:10]}
        for r in rows
    ]}


# =========================================================
# Skill Gap tools
# =========================================================

def prioritize_skill_gaps(ctx):

    _need_match(ctx)

    items = gaps(ctx.match)

    labels = {
        ("high", "missing"): "Required by the job and missing",
        ("medium", "weak"): "Required, but only listed (not shown in a project or job)",
        ("low", "missing"): "Preferred by the job and missing",
    }

    result = [
        {"skill": g["skill"], "requirement": g["requirement"], "priority": g["priority"],
         "why": labels.get((g["priority"], g["reason"]), g["reason"])}
        for g in items
    ]

    ctx.gaps = result
    ctx.artifacts["gaps"] = result

    return {"skill_gaps": result, "count": len(result)}


def get_learning_resources(ctx, skills):

    if not isinstance(skills, list) or not skills:
        raise ToolError("Send 'skills' as a non-empty list of skill names.")

    skills = [str(s).strip()[:60] for s in skills if str(s).strip()][:6]

    if ctx.role_groups:
        role_groups = ctx.role_groups
    elif ctx.match:
        _, role_groups = plan_skills(ctx.match)
    else:
        role_groups = None

    plan = build_learning_plan(skills, role_groups)

    resources = [
        {"skill": p["skill"], "importance": p.get("importance"), "time": p.get("time"),
         "resource": p.get("resource_name"), "url": p.get("resource_url"),
         "practice_project": p.get("project"), "steps": p.get("steps", [])[:4]}
        for p in plan
    ]

    ctx.artifacts["resources"] = resources

    return {"learning_resources": resources}


# =========================================================
# Resume Improvement tools
# =========================================================

def suggest_resume_improvements(ctx):

    _need_match(ctx)

    suggestions, used_ai = generate_suggestions(ctx.resume_text, ctx.match)

    compact = [
        {"type": s["kind"], "original": s["original"], "improved": s["improved"],
         "reason": s["reason"], "requirement": s.get("requirement", "")}
        for s in suggestions[:8]
    ]

    ctx.artifacts["suggestions"] = compact

    return {"suggestions": compact, "ai_used": used_ai,
            "note": "Already validated: no invented skills; invented numbers replaced by [add real number]."}


def recommend_ats_keywords(ctx):

    _need_match(ctx)

    add_if_true, move_to_bullets, exact_terms = [], [], []

    for m in ctx.match.get("mandatory", []) + ctx.match.get("preferred", []):

        if m["status"] == "missing":
            add_if_true.append({"keyword": m["requirement"], "importance": m["importance"]})

        elif m.get("evidence") in ("listed", "mentioned"):
            move_to_bullets.append(m.get("matched_skill") or m["requirement"])

        elif m.get("match_type") == "semantic":
            exact_terms.append(m["requirement"])

    soft = [s for s in (ctx.match.get("requirements") or {}).get("soft_skills", [])
            if s and s.lower() not in ctx.resume_text.lower()][:5]

    keywords = {
        "add_only_if_you_really_have_it": add_if_true,
        "move_from_skills_list_into_project_bullets": move_to_bullets,
        "use_the_exact_job_wording": exact_terms,
        "soft_skills_to_show_with_examples": soft,
    }

    ctx.artifacts["keywords"] = keywords

    return keywords


# =========================================================
# Career Roadmap tools
# =========================================================

def build_learning_roadmap(ctx):

    _need_match(ctx)

    items, used_ai = build_roadmap(ctx.match, ctx.resume_text, use_ai=ctx.use_ai)

    roadmap = [
        {"step": i + 1, "skill": it["skill"], "priority": it["priority"], "time": it.get("time"),
         "why": it.get("why"), "objectives": it.get("objectives", [])[:3],
         "resource": it.get("resource_name"), "url": it.get("resource_url"),
         "show_it_on_resume": it.get("demonstrate")}
        for i, it in enumerate(items)
    ]

    ctx.artifacts["roadmap"] = roadmap

    return {"roadmap": roadmap, "ai_used": used_ai}


def recommend_projects_tool(ctx):

    _need_match(ctx)

    ideas, used_ai = recommend_projects(ctx.match, ctx.resume_text, use_ai=ctx.use_ai)

    projects = [
        {"title": p.get("title"), "objective": p.get("objective"), "stack": p.get("stack", [])[:6],
         "features": p.get("features", [])[:4], "relevance": p.get("relevance")}
        for p in ideas
    ]

    ctx.artifacts["projects"] = projects

    return {"projects": projects, "ai_used": used_ai}


# =========================================================
# Memory tools
# =========================================================

def recall_user_memory(ctx):

    return {"memory": memory.recall(ctx.user_id) if ctx.user_id else {}}


def save_user_memory(ctx, key, value):

    ok, message = memory.remember(ctx.user_id, key, value, source="agent")

    if not ok:
        raise ToolError(message)

    return {"saved": True, "message": message}


# =========================================================
# Registry
# =========================================================

def _schema(properties=None, required=None):

    return {"type": "object", "properties": properties or {}, "required": required or []}


TOOLS = {
    "get_resume_profile": {
        "run": get_resume_profile,
        "description": "Read the uploaded resume: experience level, sections, skills shown in projects/work vs only listed, education, contact links.",
        "parameters": _schema(),
    },
    "check_resume_quality": {
        "run": check_resume_quality,
        "description": "General resume quality check (0-100) with confirmed and potential issues and recommendations. Same for every job.",
        "parameters": _schema(),
    },
    "list_job_roles": {
        "run": list_job_roles,
        "description": "List the predefined job roles that can be used with match_resume_to_role.",
        "parameters": _schema(),
    },
    "extract_job_requirements": {
        "run": extract_job_requirements,
        "description": "Extract required and preferred skills, experience and education from the job description the user gave. Only works when a job description was given.",
        "parameters": _schema(),
    },
    "match_resume_to_job": {
        "run": match_resume_to_job,
        "description": "Match the resume against the user's job description: explained score, each requirement matched or missing with evidence. Use when a job description was given.",
        "parameters": _schema(),
    },
    "match_resume_to_role": {
        "run": match_resume_to_role,
        "description": "Match the resume against a predefined job role (no job description needed): explained score and missing skills.",
        "parameters": _schema({"role_name": {"type": "string", "description": "A role name, e.g. 'Backend Developer'"}}, ["role_name"]),
    },
    "suggest_best_role": {
        "run": suggest_best_role,
        "description": "Quickly score the resume against every predefined role and return the best-fitting roles. Use when the user has no target role.",
        "parameters": _schema(),
    },
    "get_past_analyses": {
        "run": get_past_analyses,
        "description": "The user's recent job matches (job and score) from their history.",
        "parameters": _schema(),
    },
    "prioritize_skill_gaps": {
        "run": prioritize_skill_gaps,
        "description": "Missing and weakly shown skills for the matched job, most important first. Needs a job match first.",
        "parameters": _schema(),
    },
    "get_learning_resources": {
        "run": get_learning_resources,
        "description": "Free learning resources, time needed, steps and a practice project for the given skills.",
        "parameters": _schema({"skills": {"type": "array", "items": {"type": "string"}, "description": "Skill names, most important first (max 6)"}}, ["skills"]),
    },
    "suggest_resume_improvements": {
        "run": suggest_resume_improvements,
        "description": "Rewrite suggestions for the summary, weak project and experience bullets, aimed at the matched job. Validated: no invented skills or numbers. Needs a job match first.",
        "parameters": _schema(),
    },
    "recommend_ats_keywords": {
        "run": recommend_ats_keywords,
        "description": "ATS keywords for the matched job: which to add (only if true), which to move from the skills list into bullets, exact wording to use. Needs a job match first.",
        "parameters": _schema(),
    },
    "build_learning_roadmap": {
        "run": build_learning_roadmap,
        "description": "Personalised step-by-step learning roadmap from the skill gaps, with objectives, resources and how to show each skill. Needs a job match first.",
        "parameters": _schema(),
    },
    "recommend_projects": {
        "run": recommend_projects_tool,
        "description": "Portfolio project ideas that prove the missing skills without repeating existing projects. Needs a job match first.",
        "parameters": _schema(),
    },
    "recall_user_memory": {
        "run": recall_user_memory,
        "description": "Career facts remembered from the user's earlier sessions (target role, goals, skills, gaps).",
        "parameters": _schema(),
    },
    "save_user_memory": {
        "run": save_user_memory,
        "description": "Remember one career fact for future sessions. Allowed keys: " + ", ".join(memory.ALLOWED_KEYS),
        "parameters": _schema({"key": {"type": "string", "enum": list(memory.ALLOWED_KEYS)},
                               "value": {"type": "string", "description": "Short fact, max 400 characters"}},
                              ["key", "value"]),
    },
}


def schemas(names):
    """
    The tool definitions in the format the Groq / OpenAI API expects.
    """

    return [
        {"type": "function",
         "function": {"name": n, "description": TOOLS[n]["description"], "parameters": TOOLS[n]["parameters"]}}
        for n in names
    ]


def execute(ctx, name, arguments):
    """
    Runs a tool. Returns (ok, result_text, result).
    Errors are returned as text so the agent can read them and fix its next step.
    """

    if name not in TOOLS:
        return False, json.dumps({"error": f"Unknown tool '{name}'."}), None

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except ValueError:
            return False, json.dumps({"error": "Arguments were not valid JSON."}), None

    if not isinstance(arguments, dict):
        return False, json.dumps({"error": "Arguments must be a JSON object."}), None

    allowed = set(TOOLS[name]["parameters"]["properties"])
    required = set(TOOLS[name]["parameters"]["required"])

    arguments = {k: v for k, v in arguments.items() if k in allowed}

    missing = required - set(arguments)

    if missing:
        return False, json.dumps({"error": f"Missing argument(s): {', '.join(sorted(missing))}"}), None

    try:
        result = TOOLS[name]["run"](ctx, **arguments)
    except ToolError as e:
        return False, json.dumps({"error": str(e)}), None
    except Exception as e:
        print(f"Tool {name} failed:", repr(e))
        return False, json.dumps({"error": f"The tool failed: {type(e).__name__}. Try another approach."}), None

    text = json.dumps(result, ensure_ascii=False, default=str)

    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + '..."(truncated)"'

    return True, text, result
