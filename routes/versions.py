"""
Phase 3: resume version management and comparison.
"""

from flask import Blueprint, flash, redirect, render_template, request, session

from models import repository
from models.repository import _query
from resume_parser.scoring_config import SCORING_VERSION
from resume_parser.version_compare import compare_versions
from routes.job_match import save_resume_upload
from security import login_required


versions = Blueprint("versions", __name__)


def _ready():

    if not repository.has_table("resume_versions"):
        flash("Run the database upgrade (database/upgrade_v5.sql) to use resume versions.", "warning")
        return False

    return True


def score_history(user_id):
    """
    Job match scores over time per saved job, for the versions chart.
    """

    if "saved_job_id" not in repository.columns_of("jd_results"):
        return []

    rows = _query(
        """
        SELECT jd.saved_job_id, sj.title, sj.company, jd.score, jd.created_at, rv.label
        FROM jd_results jd
        JOIN resumes r ON r.resume_id = jd.resume_id
        JOIN saved_jobs sj ON sj.job_id = jd.saved_job_id AND sj.user_id = r.user_id
        LEFT JOIN resume_versions rv ON rv.version_id = jd.version_id
        WHERE r.user_id = %s
        ORDER BY jd.created_at, jd.jd_result_id
        """,
        (user_id,)
    )

    series = {}

    for row in rows:

        job = series.setdefault(row["saved_job_id"], {
            "job": (row["title"] or "Job") + (f" · {row['company']}" if row["company"] else ""),
            "points": []
        })

        job["points"].append({
            "label": row["label"] or "Uploaded file",
            "date": row["created_at"].strftime("%d %b %H:%M") if row["created_at"] else "",
            "score": float(row["score"] or 0)
        })

    return [s for s in series.values() if len(s["points"]) >= 1]


@versions.route("/resumes", methods=["GET", "POST"])
@login_required
def list_versions():

    if not _ready():
        return redirect("/dashboard")

    user_id = session["user_id"]

    if request.method == "POST":

        label = request.form.get("label", "").strip()[:100]

        if not label:
            flash("Please give this version a label, e.g. \"v2 - added Docker project\".", "danger")
            return redirect("/resumes")

        filename, filepath, text, error = save_resume_upload(request.files.get("resume"))

        if error:
            flash(error, "danger")
            return redirect("/resumes")

        repository.add_version(user_id, label, filename, filepath, text)

        flash(f"Saved \"{label}\". Earlier versions are kept.", "success")

        return redirect("/resumes")

    return render_template(
        "versions.html",
        versions=repository.list_versions(user_id),
        saved_jobs=repository.list_saved_jobs(user_id) if repository.has_table("saved_jobs") else [],
        history=score_history(user_id)
    )


@versions.route("/resumes/<int:version_id>/delete", methods=["POST"])
@login_required
def delete(version_id):

    if repository.delete_version(session["user_id"], version_id):
        flash("Version deleted. Past analyses that used it are kept.", "success")

    return redirect("/resumes")


@versions.route("/resumes/compare")
@login_required
def compare():

    if not _ready():
        return redirect("/dashboard")

    user_id = session["user_id"]

    a_id, b_id = request.args.get("a", ""), request.args.get("b", "")

    a = repository.get_version(user_id, int(a_id)) if a_id.isdigit() else None
    b = repository.get_version(user_id, int(b_id)) if b_id.isdigit() else None

    if not a or not b:
        flash("Choose two of your resume versions to compare.", "danger")
        return redirect("/resumes")

    job = None
    job_id = request.args.get("job", "")

    if job_id.isdigit() and repository.has_table("saved_jobs"):
        job = repository.get_saved_job(user_id, int(job_id))

    requirements = job["requirements_data"] if job else None

    return render_template(
        "version_compare.html",
        a=a,
        b=b,
        job=job,
        c=compare_versions(a["resume_text"] or "", b["resume_text"] or "", requirements),
        scoring_version=SCORING_VERSION,
        versions=repository.list_versions(user_id),
        saved_jobs=repository.list_saved_jobs(user_id) if repository.has_table("saved_jobs") else []
    )
