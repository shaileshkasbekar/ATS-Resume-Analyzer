from flask import Blueprint, render_template, request, session, redirect, flash
from werkzeug.utils import secure_filename

import os
import json
import uuid
from datetime import datetime

from config import Config
from models.database import get_db_connection, table_columns
from models import repository
from security import login_required, rate_limit

from resume_parser.pdf_reader import extract_text_from_pdf, extract_text_from_pdf_bytes
from resume_parser.jd_analyzer import analyze_job_match, analyze_role_match, plan_skills
from resume_parser.job_requirements import extract_requirements
from resume_parser.job_matcher import run_job_match
from resume_parser.recommendation import build_learning_plan
from resume_parser.general_analyzer import analyze_resume
from resume_parser.improvement import KIND_LABELS
from routes import result_view


# =========================================
# Blueprint
# =========================================

job_match = Blueprint("job_match", __name__)


MIN_JD_LENGTH = 100
MAX_JD_LENGTH = 20000

MODES = ("paste", "file", "role", "saved")


# =========================================
# Helpers
# =========================================

def _job_roles():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT role_id, role_name FROM job_roles ORDER BY role_name")
    roles = cursor.fetchall()

    cursor.close()
    connection.close()

    return roles


def _role_skill_groups(role_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

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

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return rows


def read_job_description_file(upload):
    """
    Text of an uploaded .pdf or .txt job description.
    Returns (text, error message).
    """

    name = (upload.filename or "").lower()

    data = upload.read()

    if name.endswith(".pdf"):
        return extract_text_from_pdf_bytes(data), None

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace"), None

    return "", "The job description file must be a PDF or TXT file."


def save_resume_upload(upload):
    """
    Validates and saves an uploaded resume PDF in the private folder.
    Returns (filename, filepath, text, error).
    """

    if not upload or upload.filename == "":
        return None, None, "", "Please select a resume."

    if not upload.filename.lower().endswith(".pdf"):
        return None, None, "", "Only PDF resumes are allowed."

    # Check the file really is a PDF, not just named .pdf

    if upload.stream.read(5) != b"%PDF-":
        return None, None, "", "This file is not a valid PDF."

    upload.stream.seek(0)

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    filename = secure_filename(upload.filename) or "resume.pdf"

    filepath = os.path.join(Config.UPLOAD_FOLDER, f"{uuid.uuid4().hex[:8]}_{filename}")

    upload.save(filepath)

    text = extract_text_from_pdf(filepath)

    if not text.strip():

        os.remove(filepath)

        return None, None, "", (
            "Could not read text from this resume PDF. "
            "If it is a scanned image, please upload a text-based PDF."
        )

    return filename, filepath, text, None


def _render_form(prefill, status=200):

    user_id = session["user_id"]

    has_saved_jobs = repository.has_table("saved_jobs")

    return render_template(
        "job_match.html",
        job_roles=_job_roles(),
        versions=repository.list_versions(user_id) if repository.has_table("resume_versions") else [],
        saved_jobs=repository.list_saved_jobs(user_id) if has_saved_jobs else [],
        prefill=prefill,
        can_save_jobs=has_saved_jobs
    ), status


def _submitted_prefill():
    """
    What the user typed, so the form can be shown again after an error
    (uploaded files cannot be kept by the browser).
    """

    form = request.form

    def as_int(name):
        value = form.get(name, "")
        return int(value) if value.isdigit() else None

    return {
        "mode": form.get("mode") if form.get("mode") in MODES else "paste",
        "job_description": form.get("job_description", "")[:MAX_JD_LENGTH],
        "job_title": form.get("job_title", "")[:200],
        "company": form.get("company", "")[:200],
        "saved_job_id": as_int("saved_job_id"),
        "role_id": as_int("role_id"),
        "resume_version_id": as_int("resume_version_id"),
        "save_job": bool(form.get("save_job")),
    }


def _back(message):
    """
    Shows the form again with the error and the user's input kept.
    """

    flash(message, "danger")

    return _render_form(_submitted_prefill(), 400)


# =========================================
# Job Match page
# =========================================

@job_match.route("/job-match", methods=["GET", "POST"])
@login_required
@rate_limit("job_match", 15, 600, "/job-match")
def match_job():

    user_id = session["user_id"]

    has_versions = repository.has_table("resume_versions")
    has_saved_jobs = repository.has_table("saved_jobs")


    if request.method == "GET":

        prefill = {"mode": "paste", "job_description": "", "job_title": "", "company": "",
                   "saved_job_id": None, "role_id": None, "resume_version_id": None, "save_job": False}

        # Re-analyze a saved job: /job-match?job=<id>

        if has_saved_jobs and request.args.get("job", "").isdigit():
            prefill.update(mode="saved", saved_job_id=int(request.args["job"]))

        # Re-analyze a previous result: /job-match?from=<jd_result_id>

        elif request.args.get("from", "").isdigit():

            previous = repository.get_jd_result(user_id, int(request.args["from"]))

            if previous and (previous.get("source_type") or "paste") != "role":
                prefill.update(
                    job_description=previous.get("job_description") or "",
                    job_title=previous.get("job_title") or "",
                    company=previous.get("company_name") or ""
                )

        return _render_form(prefill)


    mode = request.form.get("mode", "paste")

    if mode not in MODES:
        return _back("Please choose how to provide the job.")

    job_title = request.form.get("job_title", "").strip()[:200]
    company = request.form.get("company", "").strip()[:200]


    # -----------------------------------------
    # The job: pasted text, uploaded file, saved job or a role
    # -----------------------------------------

    jd_text = ""
    role_id = None
    role_groups = []
    saved_job = None

    if mode == "paste":

        jd_text = request.form.get("job_description", "").strip()

    elif mode == "file":

        upload = request.files.get("jd_file")

        if not upload or upload.filename == "":
            return _back("Please select a job description file (PDF or TXT).")

        jd_text, error = read_job_description_file(upload)

        if error:
            return _back(error)

        jd_text = jd_text.strip()

    elif mode == "saved":

        job_id = request.form.get("saved_job_id", "")

        saved_job = repository.get_saved_job(user_id, int(job_id)) if job_id.isdigit() and has_saved_jobs else None

        if not saved_job:
            return _back("Please select one of your saved jobs.")

        jd_text = saved_job["description"]
        job_title = saved_job["title"] or ""
        company = saved_job["company"] or ""

    else:

        try:
            role_id = int(request.form.get("role_id", ""))
        except ValueError:
            return _back("Please select a job role.")

        role_groups = _role_skill_groups(role_id)

        if not role_groups:
            return _back("No skills are configured for this job role yet.")


    if mode != "role":

        if len(jd_text) < MIN_JD_LENGTH:
            return _back("The job description is too short. Please provide the full posting (at least a few lines).")

        jd_text = jd_text[:MAX_JD_LENGTH]


    # -----------------------------------------
    # Resume: a saved version or a new upload
    # -----------------------------------------

    version_id = None
    version_choice = request.form.get("resume_version_id", "")

    if version_choice.isdigit() and has_versions:

        version = repository.get_version(user_id, int(version_choice))

        if not version:
            return _back("Please select one of your resume versions.")

        version_id = version["version_id"]
        filename = version["file_name"]
        filepath = version["file_path"]
        text = version["resume_text"] or extract_text_from_pdf(filepath)

    else:

        filename, filepath, text, error = save_resume_upload(request.files.get("resume"))

        if error:
            return _back(error)


    # -----------------------------------------
    # Analyze
    # -----------------------------------------

    if mode == "role":

        result = analyze_role_match(text, role_groups[0]["role_name"], role_groups)

    elif saved_job and saved_job.get("requirements_data"):

        # Requirements were extracted when the job was saved

        requirements = saved_job["requirements_data"]
        requirements["job_title"] = job_title
        requirements["company"] = company

        result = run_job_match(text, requirements, jd_text)
        result.update(requirements=requirements, job_title=job_title, company=company, source_type="job_description")

    else:

        result = analyze_job_match(text, jd_text, job_title, company)


    if not result["ai_available"]:
        flash(
            "AI analysis is unavailable right now. The score uses rule-based "
            "matching only; AI-based parts were skipped.",
            "warning"
        )


    # -----------------------------------------
    # Save the job for later (optional)
    # -----------------------------------------

    saved_job_id = saved_job["job_id"] if saved_job else None

    if request.form.get("save_job") and mode in ("paste", "file") and has_saved_jobs:

        saved_job_id = repository.save_job(
            user_id, result["job_title"], result["company"], jd_text, result["requirements"]
        )

        flash("Job saved. You can reuse it from Saved Jobs.", "success")


    # -----------------------------------------
    # Save to history
    # -----------------------------------------

    jd_result_id = save_job_match(
        user_id, filename, filepath, result,
        jd_text or f"Predefined role: {result['job_title']}",
        mode, role_id, version_id=version_id, saved_job_id=saved_job_id,
        keep_file=version_id is not None
    )

    return render_job_match_result(result, filename, jd_result_id, resume_text=text)


def save_job_match(user_id, filename, filepath, result, jd_text, mode, role_id,
                   version_id=None, saved_job_id=None, keep_file=False):
    """
    Saves the resume and the result. Returns the new jd_result_id
    (or None). Newer columns are used only if they exist, so older
    databases keep working.
    """

    connection = get_db_connection()

    cursor = connection.cursor()

    try:

        columns = table_columns(cursor, "jd_results")

        if not columns:

            if not keep_file and os.path.exists(filepath):
                os.remove(filepath)

            flash(
                "Result not saved to history: run the database upgrade "
                "(database/upgrade_v3.sql) to enable this.",
                "warning"
            )

            return None

        resume_data = {"user_id": user_id, "file_name": filename, "file_path": filepath}

        if version_id and "version_id" in table_columns(cursor, "resumes"):
            resume_data["version_id"] = version_id

        cursor.execute(
            "INSERT INTO resumes (" + ", ".join(resume_data) + ") VALUES ("
            + ", ".join(["%s"] * len(resume_data)) + ")",
            tuple(resume_data.values())
        )

        component = {c["key"]: c for c in result["components"]}

        data = {
            "resume_id": cursor.lastrowid,
            "job_title": result["job_title"],
            "job_description": jd_text,
            "score": result["score"],
            "keyword_score": component["required_skills"]["score"],
            "ai_relevance": component["semantic_relevance"]["score"],
            "experience_match": component["experience"]["score"],
            "details": json.dumps(result),
        }

        optional = {
            "company_name": result["company"],
            "source_type": mode,
            "role_id": role_id,
            "scoring_version": result["scoring_version"],
            "requirements": json.dumps(result["requirements"]),
            "version_id": version_id,
            "saved_job_id": saved_job_id,
        }

        data.update({k: v for k, v in optional.items() if k in columns})

        cursor.execute(
            "INSERT INTO jd_results (" + ", ".join(data) + ") VALUES ("
            + ", ".join(["%s"] * len(data)) + ")",
            tuple(data.values())
        )

        jd_result_id = cursor.lastrowid

        connection.commit()

        return jd_result_id

    except Exception as e:

        connection.rollback()

        print("Database Error:", e)

        flash("Analysis finished, but it could not be saved to your history.", "warning")

        return None

    finally:

        cursor.close()

        connection.close()


def normalize_result(result):
    """
    Fills in defaults so any saved result renders, including ones
    saved by older scoring versions.
    """

    result = dict(result or {})

    result.setdefault("scoring_version", "jm-1.0")
    result.setdefault("ai_available", True)
    result.setdefault("score", 0)
    result.setdefault("job_title", "")
    result.setdefault("company", "")
    result.setdefault("source_type", "job_description")

    for key in ("components", "deductions", "mandatory", "preferred",
                "certifications", "relevant_projects", "strengths", "actions"):
        result.setdefault(key, [])

    result.setdefault("experience", {"required_years": None, "required_text": "", "candidate_years": None})
    result.setdefault("education", {"required_level": None, "resume_level": None, "met": None, "in_progress": False})
    result.setdefault("requirements", {})

    requirements = result["requirements"]

    for key in ("responsibilities", "soft_skills", "education", "certifications_preferred"):
        requirements.setdefault(key, [])

    return result


def render_job_match_result(result, filename, jd_result_id=None, resume_text="", analyzed_at=None):
    """
    Shared by the new result and the saved one in history.
    Only re-arranges the saved result for display (see result_view.py).
    """

    result = normalize_result(result)

    missing, importance = plan_skills(result)

    career_tools = jd_result_id is not None and repository.has_table("generated_content")

    suggestions = []
    has_roadmap = False

    if career_tools:

        user_id = session["user_id"]

        suggestions = repository._query(
            """
            SELECT * FROM resume_suggestions
            WHERE user_id = %s AND jd_result_id = %s AND status != 'rejected'
            ORDER BY FIELD(status, 'pending', 'accepted'), suggestion_id
            """,
            (user_id, jd_result_id)
        )

        has_roadmap = bool(repository._query(
            "SELECT 1 FROM roadmap_items WHERE user_id = %s AND jd_result_id = %s LIMIT 1",
            (user_id, jd_result_id), one=True
        ))

    # Resume quality from the existing rule-based checker (no AI, no new scoring)

    quality = analyze_resume(resume_text) if resume_text.strip() else None

    return render_template(
        "job_match_result.html",
        result=result,
        filename=filename,
        jd_result_id=jd_result_id,
        analyzed_at=analyzed_at or datetime.now(),
        career_tools=career_tools,
        quality=quality,
        interpretation=result_view.interpretation(result),
        priorities=result_view.priority_actions(result, jd_result_id, career_tools, has_roadmap),
        groups=result_view.skill_groups(result),
        evidence=result_view.evidence_rows(result),
        suggestions=suggestions,
        kind_labels=KIND_LABELS,
        has_roadmap=has_roadmap,
        learning_plan=build_learning_plan(missing, importance)
    )


# =========================================
# Requirements preview (before running the analysis)
# =========================================

@job_match.route("/job-match/preview", methods=["POST"])
@login_required
@rate_limit("job_preview", 30, 600)
def preview_requirements():
    """
    JSON {"job_description": "..."} -> the requirements the rule-based parser
    finds. Fast and free (no AI); the full analysis also uses AI.
    """

    text = str((request.get_json(silent=True) or {}).get("job_description") or "").strip()

    if len(text) < MIN_JD_LENGTH:
        return {"error": "Paste at least a few lines of the job description first."}, 400

    found = extract_requirements(text[:MAX_JD_LENGTH], use_ai=False)

    level_names = {0: "Diploma", 1: "Bachelor's degree", 2: "Master's degree", 3: "PhD"}

    return {
        "mandatory": [item["name"] for item in found["mandatory_skills"]],
        "preferred": [item["name"] for item in found["preferred_skills"]],
        "experience_years": found["experience"]["min_years"],
        "education": level_names.get(found["education_required_level"]),
        "certifications": found["certifications_required"],
        "soft_skills": found["soft_skills"],
        "responsibilities": len(found["responsibilities"]),
    }
