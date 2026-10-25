"""
Phase 3: saved job descriptions and multiple job comparison.
"""

from flask import Blueprint, flash, redirect, render_template, request, session

from models import repository
from resume_parser.job_requirements import extract_requirements
from resume_parser.multi_job import compare_jobs
from routes.job_match import MAX_JD_LENGTH, MIN_JD_LENGTH, _job_roles, _role_skill_groups
from security import login_required, rate_limit


jobs = Blueprint("jobs", __name__)


def _ready():

    if not repository.has_table("saved_jobs"):
        flash("Run the database upgrade (database/upgrade_v5.sql) to use saved jobs.", "warning")
        return False

    return True


@jobs.route("/jobs")
@login_required
def list_jobs():

    if not _ready():
        return redirect("/dashboard")

    return render_template(
        "jobs.html",
        jobs=repository.list_saved_jobs(session["user_id"]),
        versions=repository.list_versions(session["user_id"]) if repository.has_table("resume_versions") else []
    )


@jobs.route("/jobs/new", methods=["GET", "POST"])
@jobs.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
@rate_limit("save_job", 20, 600)
def edit_job(job_id=None):

    if not _ready():
        return redirect("/dashboard")

    user_id = session["user_id"]

    job = repository.get_saved_job(user_id, job_id) if job_id else None

    if job_id and not job:
        return redirect("/jobs")

    if request.method == "POST":

        title = request.form.get("title", "").strip()[:200]
        company = request.form.get("company", "").strip()[:200]
        description = request.form.get("description", "").strip()

        if len(description) < MIN_JD_LENGTH:

            flash("The job description is too short. Please paste the full posting.", "danger")

            # Show the form again with what the user typed

            typed = dict(job or {}, title=title, company=company, description=description)

            return render_template("job_form.html", job=typed if job else None, draft=typed), 400

        description = description[:MAX_JD_LENGTH]

        # Extract requirements once and store them, so the job can be
        # reused without extracting again

        requirements = extract_requirements(description, title, company)

        repository.save_job(
            user_id, title or requirements["job_title"], company or requirements["company"],
            description, requirements, job_id
        )

        flash("Job saved." if not job_id else "Job updated. Its requirements were extracted again.", "success")

        return redirect("/jobs")

    return render_template("job_form.html", job=job)


@jobs.route("/jobs/<int:job_id>")
@login_required
def view_job(job_id):

    if not _ready():
        return redirect("/dashboard")

    job = repository.get_saved_job(session["user_id"], job_id)

    if not job:
        return redirect("/jobs")

    return render_template("job_view.html", job=job, req=job["requirements_data"] or {})


@jobs.route("/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def delete_job(job_id):

    if repository.delete_saved_job(session["user_id"], job_id):
        flash("Job deleted. Past analyses for it are kept.", "success")

    return redirect("/jobs")


@jobs.route("/jobs/compare", methods=["POST"])
@login_required
@rate_limit("compare_jobs", 20, 600, "/jobs")
def compare():

    if not _ready():
        return redirect("/dashboard")

    user_id = session["user_id"]

    version_id = request.form.get("version_id", "")

    version = repository.get_version(user_id, int(version_id)) if version_id.isdigit() else None

    if not version:
        flash("Choose one of your resume versions.", "danger")
        return redirect("/jobs")

    selected = []

    for value in request.form.getlist("job_ids"):

        job = repository.get_saved_job(user_id, int(value)) if value.isdigit() else None

        if job and job["requirements_data"]:
            selected.append({
                "job_id": job["job_id"],
                "title": job["title"],
                "company": job["company"],
                "requirements": job["requirements_data"],
            })

    if len(selected) < 2:
        flash("Select at least two saved jobs to compare.", "danger")
        return redirect("/jobs")

    roles = {
        role["role_name"]: _role_skill_groups(role["role_id"])
        for role in _job_roles()
    }

    result = compare_jobs(version["resume_text"] or "", selected, {k: v for k, v in roles.items() if v})

    return render_template("job_compare.html", version=version, c=result)
