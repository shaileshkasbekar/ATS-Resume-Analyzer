"""
Job application tracker: where you applied, the status, dates, notes and
which resume version you sent. Every query is limited to the logged-in user.
"""

from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, session

from models import repository
from models.repository import _execute, _query
from security import login_required


applications = Blueprint("applications", __name__)


STATUSES = [
    ("saved", "To apply"),
    ("applied", "Applied"),
    ("interview", "Interview"),
    ("offer", "Offer"),
    ("rejected", "Rejected"),
]

STATUS_KEYS = {key for key, _ in STATUSES}


def _ready():

    if not repository.has_table("applications"):
        flash("Run the database upgrade (database/upgrade_v6.sql) to use the application tracker.", "warning")
        return False

    return True


def _date(value):

    value = (value or "").strip()

    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return False


def _own_id(table, column, value):
    """
    The id if it belongs to the user, else None (never link someone else's record).
    """

    if not str(value or "").isdigit() or not repository.has_table(table):
        return None

    row = _query(f"SELECT {column} FROM {table} WHERE {column} = %s AND user_id = %s",
                 (int(value), session["user_id"]), one=True)

    return row[column] if row else None


def _form_data():

    form = request.form

    data = {
        "company": form.get("company", "").strip()[:200],
        "job_title": form.get("job_title", "").strip()[:200],
        "status": form.get("status", "saved"),
        "applied_on": _date(form.get("applied_on")),
        "interview_on": _date(form.get("interview_on")),
        "job_url": form.get("job_url", "").strip()[:500],
        "notes": form.get("notes", "").strip()[:5000],
        "version_id": _own_id("resume_versions", "version_id", form.get("version_id")),
        "saved_job_id": _own_id("saved_jobs", "job_id", form.get("saved_job_id")),
    }

    errors = []

    if not data["company"] or not data["job_title"]:
        errors.append("Company and job title are required.")

    if data["status"] not in STATUS_KEYS:
        errors.append("Please choose a valid status.")

    if data["applied_on"] is False or data["interview_on"] is False:
        errors.append("Please enter dates as YYYY-MM-DD.")

    if data["job_url"] and not data["job_url"].lower().startswith(("http://", "https://")):
        errors.append("The job link must start with http:// or https://")

    return data, errors


def _choices():

    user_id = session["user_id"]

    return {
        "versions": repository.list_versions(user_id) if repository.has_table("resume_versions") else [],
        "saved_jobs": repository.list_saved_jobs(user_id) if repository.has_table("saved_jobs") else [],
        "statuses": STATUSES,
    }


@applications.route("/applications")
@login_required
def board():

    if not _ready():
        return redirect("/dashboard")

    rows = _query(
        """
        SELECT a.*, rv.label AS version_label
        FROM applications a
        LEFT JOIN resume_versions rv ON rv.version_id = a.version_id AND rv.user_id = a.user_id
        WHERE a.user_id = %s
        ORDER BY a.updated_at DESC, a.application_id DESC
        """,
        (session["user_id"],)
    ) if repository.has_table("resume_versions") else _query(
        "SELECT *, NULL AS version_label FROM applications WHERE user_id = %s ORDER BY updated_at DESC",
        (session["user_id"],)
    )

    columns = [
        {"key": key, "label": label, "items": [r for r in rows if r["status"] == key]}
        for key, label in STATUSES
    ]

    today = date.today()

    upcoming = sorted(
        [r for r in rows if r["interview_on"] and r["interview_on"] >= today and r["status"] == "interview"],
        key=lambda r: r["interview_on"]
    )

    return render_template("applications.html", columns=columns, total=len(rows), upcoming=upcoming,
                           statuses=STATUSES, today=today)


@applications.route("/applications/new", methods=["GET", "POST"])
@applications.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
@login_required
def edit(application_id=None):

    if not _ready():
        return redirect("/dashboard")

    user_id = session["user_id"]

    item = None

    if application_id:

        item = _query("SELECT * FROM applications WHERE application_id = %s AND user_id = %s",
                      (application_id, user_id), one=True)

        if not item:
            return redirect("/applications")

    if request.method == "POST":

        data, errors = _form_data()

        if errors:

            for error in errors:
                flash(error, "danger")

            draft = dict(item or {}, **{k: v for k, v in data.items() if v is not False})

            return render_template("application_form.html", item=draft, editing=bool(item), **_choices()), 400

        columns = list(data)

        if item:
            _execute(
                "UPDATE applications SET " + ", ".join(f"{c} = %s" for c in columns)
                + " WHERE application_id = %s AND user_id = %s",
                tuple(data.values()) + (application_id, user_id)
            )
            flash("Application updated.", "success")
        else:
            _execute(
                "INSERT INTO applications (user_id, " + ", ".join(columns) + ") VALUES (%s, "
                + ", ".join(["%s"] * len(columns)) + ")",
                (user_id,) + tuple(data.values())
            )
            flash("Application added.", "success")

        return redirect("/applications")

    # New application prefilled from a saved job: /applications/new?job=<id>

    if not item and request.args.get("job", "").isdigit() and repository.has_table("saved_jobs"):

        job = repository.get_saved_job(user_id, int(request.args["job"]))

        if job:
            item = {"company": job["company"] or "", "job_title": job["title"] or "", "saved_job_id": job["job_id"]}

            return render_template("application_form.html", item=item, editing=False, **_choices())

    return render_template("application_form.html", item=item or {}, editing=bool(item), **_choices())


@applications.route("/applications/<int:application_id>/status", methods=["POST"])
@login_required
def set_status(application_id):

    status = request.form.get("status", "")

    if status not in STATUS_KEYS:
        flash("Please choose a valid status.", "danger")
        return redirect("/applications")

    extra = ""
    params = [status]

    # Moving to "applied" without a date: use today

    if status == "applied":
        extra = ", applied_on = COALESCE(applied_on, %s)"
        params.append(date.today())

    _execute(
        f"UPDATE applications SET status = %s{extra} WHERE application_id = %s AND user_id = %s",
        tuple(params) + (application_id, session["user_id"])
    )

    return redirect("/applications")


@applications.route("/applications/<int:application_id>/delete", methods=["POST"])
@login_required
def delete(application_id):

    _, count = _execute("DELETE FROM applications WHERE application_id = %s AND user_id = %s",
                        (application_id, session["user_id"]))

    if count:
        flash("Application deleted.", "success")

    return redirect("/applications")
