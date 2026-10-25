"""
UX pages that connect the existing features:

- Action Center: one place that summarises the user's latest saved findings
  (it only reads saved results; it never re-scores anything)
- Pick an analysis: entry point for tools that work on a job match
- Settings: profile name and password
"""

from flask import Blueprint, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from models import repository
from models.repository import _execute, _query, loads
from routes.auth import MIN_PASSWORD_LENGTH
from routes.career import roadmap_progress
from security import login_required, rate_limit


workspace = Blueprint("workspace", __name__)


# Tools that need a saved job match, and where they live

TOOLS = {
    "assistant": {"label": "Resume Improvement", "icon": "fa-wand-magic-sparkles", "url": "/assistant/{id}",
                  "intro": "Get rewrite suggestions for one of your job matches, then accept or reject each one."},
    "optimize": {"label": "Resume Builder", "icon": "fa-file-pen", "url": "/optimize/{id}",
                 "intro": "Build an ATS-friendly resume for one of your job matches, using the suggestions you accepted."},
    "projects": {"label": "Project Recommendations", "icon": "fa-lightbulb", "url": "/projects/{id}",
                 "intro": "Get portfolio project ideas that prove the skills a job asks for."},
    "interview": {"label": "Mock Interview", "icon": "fa-comments", "url": "/interview/{id}",
                  "intro": "Practise interview questions based on your resume and a job."},
}


def _has_v5():

    return repository.has_table("resume_suggestions")


# =========================================
# Pick an analysis
# =========================================

@workspace.route("/pick/<tool>")
@login_required
def pick(tool):

    if tool not in TOOLS:
        return redirect("/dashboard")

    analyses = repository.list_jd_results(session["user_id"], limit=30) if repository.has_table("jd_results") else []

    # Only one analysis: go straight to the tool

    if len(analyses) == 1 and _has_v5():
        return redirect(TOOLS[tool]["url"].format(id=analyses[0]["jd_result_id"]))

    return render_template("pick.html", tool=tool, info=TOOLS[tool], analyses=analyses, ready=_has_v5())


# =========================================
# Action Center
# =========================================

def _latest_general(user_id, offset=0):

    row = _query(
        f"""
        SELECT g.*, r.upload_date
        FROM general_results g JOIN resumes r ON r.resume_id = g.resume_id
        WHERE r.user_id = %s
        ORDER BY r.upload_date DESC, g.general_result_id DESC
        LIMIT 1 OFFSET {int(offset)}
        """,
        (user_id,),
        one=True
    )

    if row:
        row["issues_data"] = loads(row.get("issues"), {})
        row["recommendations_data"] = loads(row.get("recommendations"), [])

    return row


def _previous_same_job(user_id, row):
    """
    The analysis of the same job just before this one, for progress.
    """

    return _query(
        """
        SELECT jd.jd_result_id, jd.score, jd.created_at
        FROM jd_results jd JOIN resumes r ON r.resume_id = jd.resume_id
        WHERE r.user_id = %s AND jd.job_title = %s AND jd.jd_result_id < %s
        ORDER BY jd.jd_result_id DESC LIMIT 1
        """,
        (user_id, row["job_title"] or "", row["jd_result_id"]),
        one=True
    )


@workspace.route("/action-center")
@login_required
def action_center():

    user_id = session["user_id"]

    analyses = repository.list_jd_results(user_id, limit=20) if repository.has_table("jd_results") else []

    chosen = request.args.get("jd", "")

    current = None

    if chosen.isdigit():
        current = repository.get_jd_result(user_id, int(chosen))

    if not current and analyses:
        current = repository.get_jd_result(user_id, analyses[0]["jd_result_id"])

    data = {"analyses": analyses, "current": current}

    if current:

        result = current["result"]

        mandatory = result.get("mandatory", [])

        data["missing_required"] = [m for m in mandatory if m.get("status") == "missing"]
        data["weak_required"] = [m for m in mandatory if m.get("status") == "matched" and m.get("evidence") in ("listed", "mentioned")]
        data["missing_preferred"] = [m for m in result.get("preferred", []) if m.get("status") == "missing"]
        data["previous"] = _previous_same_job(user_id, current)

        if _has_v5():

            counts = _query(
                """
                SELECT status, COUNT(*) AS n FROM resume_suggestions
                WHERE user_id = %s AND jd_result_id = %s GROUP BY status
                """,
                (user_id, current["jd_result_id"])
            )

            data["suggestions"] = {c["status"]: c["n"] for c in counts}

            data["roadmap_todo"] = _query(
                """
                SELECT item_id, skill, priority FROM roadmap_items
                WHERE user_id = %s AND jd_result_id = %s AND status != 'done'
                ORDER BY FIELD(priority, 'high', 'medium', 'low'), item_id LIMIT 5
                """,
                (user_id, current["jd_result_id"])
            )

            data["has_roadmap"] = bool(_query(
                "SELECT 1 FROM roadmap_items WHERE user_id = %s AND jd_result_id = %s LIMIT 1",
                (user_id, current["jd_result_id"]), one=True
            ))

            questions = repository.get_generated(user_id, current["jd_result_id"], "interview")

            answers = _query(
                "SELECT question_index, feedback FROM interview_answers WHERE user_id = %s AND jd_result_id = %s",
                (user_id, current["jd_result_id"])
            )

            # Average score per feedback criterion over the latest answer to each question

            latest = {}
            for a in answers:
                latest[a["question_index"]] = loads(a["feedback"], {})

            totals = {}
            for feedback in latest.values():
                for key, value in (feedback.get("scores") or {}).items():
                    if value is not None:
                        totals.setdefault(key, []).append(value)

            averages = {k: round(sum(v) / len(v)) for k, v in totals.items()}

            data["interview"] = {
                "questions": len((questions or {}).get("questions", [])),
                "answered": len(latest),
                "weakest": min(averages, key=averages.get) if averages else None,
                "averages": averages,
            }

    data["general"] = _latest_general(user_id)
    data["general_previous"] = _latest_general(user_id, 1)

    done, total = roadmap_progress(user_id)

    data["roadmap_done"], data["roadmap_total"] = done, total

    return render_template("action_center.html", **data, v5=_has_v5())


# =========================================
# Settings
# =========================================

@workspace.route("/settings")
@login_required
def settings():

    user = _query("SELECT full_name, email, created_at FROM users WHERE user_id = %s", (session["user_id"],), one=True)

    return render_template("settings.html", user=user)


@workspace.route("/settings/profile", methods=["POST"])
@login_required
def update_profile():

    name = request.form.get("fullname", "").strip()

    if not 2 <= len(name) <= 100:
        flash("Please enter your full name (2-100 characters).", "danger")
        return redirect("/settings")

    _execute("UPDATE users SET full_name = %s WHERE user_id = %s", (name, session["user_id"]))

    session["fullname"] = name

    flash("Profile updated.", "success")

    return redirect("/settings")


@workspace.route("/settings/password", methods=["POST"])
@login_required
@rate_limit("password_change", 5, 600, "/settings")
def change_password():

    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    user = _query("SELECT password FROM users WHERE user_id = %s", (session["user_id"],), one=True)

    if not user or not check_password_hash(user["password"], current):
        flash("Your current password is not correct.", "danger")
        return redirect("/settings")

    if len(new) < MIN_PASSWORD_LENGTH:
        flash(f"The new password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
        return redirect("/settings")

    if new != confirm:
        flash("The new passwords do not match.", "danger")
        return redirect("/settings")

    _execute("UPDATE users SET password = %s WHERE user_id = %s", (generate_password_hash(new), session["user_id"]))

    flash("Password changed.", "success")

    return redirect("/settings")
