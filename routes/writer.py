"""
Writing tools (cover letter, LinkedIn) and read-only share links
for a job match result.
"""

import secrets

from flask import Blueprint, Response, flash, redirect, render_template, request, session

from models import repository
from models.repository import _execute, _query, loads
from resume_parser.writer import write_cover_letter, write_linkedin
from routes.job_match import normalize_result
from security import login_required, rate_limit


writer = Blueprint("writer", __name__)

KINDS = {"cover_letter": "Cover letter", "linkedin": "LinkedIn profile"}


def _load(jd_result_id):

    row = repository.get_jd_result(session["user_id"], jd_result_id)

    if not row:
        return None, ""

    return row, repository.resume_text_for(row)


def _result(row):

    result = normalize_result(row["result"])
    result["job_title"] = row.get("job_title") or result["job_title"]
    result["company"] = row.get("company_name") or result["company"]

    return result


# =========================================
# Writing tools
# =========================================

@writer.route("/write/<int:jd_result_id>")
@login_required
def view(jd_result_id):

    if not repository.has_table("generated_content"):
        flash("Run the database upgrade (database/upgrade_v5.sql) to use the writing tools.", "warning")
        return redirect(f"/history/jd/{jd_result_id}")

    row, text = _load(jd_result_id)

    if not row:
        return redirect("/history")

    user_id = session["user_id"]

    return render_template(
        "writer.html",
        row=row,
        letter=repository.get_generated(user_id, jd_result_id, "cover_letter"),
        linkedin=repository.get_generated(user_id, jd_result_id, "linkedin"),
        resume_missing=not text.strip()
    )


@writer.route("/write/<int:jd_result_id>/<kind>", methods=["POST"])
@login_required
@rate_limit("writer", 10, 600)
def generate(jd_result_id, kind):

    if kind not in KINDS:
        return redirect(f"/write/{jd_result_id}")

    row, text = _load(jd_result_id)

    if not row or not text.strip():
        flash("The resume for this analysis is not available.", "danger")
        return redirect("/history")

    result = _result(row)

    content = write_cover_letter(result, text) if kind == "cover_letter" else write_linkedin(result, text)

    repository.save_generated(session["user_id"], jd_result_id, kind, content)

    if not content["ai"]:
        flash("AI is unavailable, so a template was created. Fill in the [brackets] yourself.", "warning")
    elif content["removed"]:
        flash(f"{len(content['removed'])} sentence(s) were removed because they mentioned skills your resume does not show.", "warning")

    return redirect(f"/write/{jd_result_id}#{kind}")


@writer.route("/write/<int:jd_result_id>/<kind>/save", methods=["POST"])
@login_required
def save(jd_result_id, kind):
    """
    Saves the user's own edits.
    """

    row, _ = _load(jd_result_id)

    if kind not in KINDS or not row:
        return redirect("/history")

    content = repository.get_generated(session["user_id"], jd_result_id, kind) or {"ai": False, "removed": []}

    if kind == "cover_letter":
        content["text"] = request.form.get("text", "").strip()[:6000]
    else:
        content["headline"] = request.form.get("headline", "").strip()[:220]
        content["about"] = request.form.get("about", "").strip()[:2600]

    content["edited"] = True

    repository.save_generated(session["user_id"], jd_result_id, kind, content)

    flash("Saved your changes.", "success")

    return redirect(f"/write/{jd_result_id}#{kind}")


@writer.route("/write/<int:jd_result_id>/<kind>.txt")
@login_required
def download(jd_result_id, kind):

    row, _ = _load(jd_result_id)

    content = repository.get_generated(session["user_id"], jd_result_id, kind) if row and kind in KINDS else None

    if not content:
        return redirect(f"/write/{jd_result_id}")

    if kind == "cover_letter":
        body = content.get("text", "")
    else:
        body = f"Headline:\n{content.get('headline', '')}\n\nAbout:\n{content.get('about', '')}"

    return Response(body, mimetype="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{kind}.txt"'})


# =========================================
# Share links (read-only, owner can turn off)
# =========================================

def _share_ready():

    return "share_token" in repository.columns_of("jd_results")


@writer.route("/share/<int:jd_result_id>", methods=["POST"])
@login_required
def toggle_share(jd_result_id):

    if not _share_ready():
        flash("Run the database upgrade (database/upgrade_v6.sql) to use share links.", "warning")
        return redirect(f"/history/jd/{jd_result_id}")

    row = repository.get_jd_result(session["user_id"], jd_result_id)

    if not row:
        return redirect("/history")

    if request.form.get("action") == "off":

        _execute("UPDATE jd_results SET share_token = NULL WHERE jd_result_id = %s", (jd_result_id,))
        flash("Sharing turned off. The old link no longer works.", "success")

    else:

        token = row.get("share_token") or secrets.token_urlsafe(24)

        _execute("UPDATE jd_results SET share_token = %s WHERE jd_result_id = %s", (token, jd_result_id))
        flash("Share link created. Anyone with the link can view this report (read-only).", "success")

    return redirect(f"/history/jd/{jd_result_id}#share")


@writer.route("/shared/<token>")
def shared(token):
    """
    Public, read-only view. No login; shows the report only (no resume file,
    no editing, no other records of the owner).
    """

    if not _share_ready() or len(token) < 20:
        return render_template("error.html", code=404, message="This link does not exist or sharing was turned off."), 404

    row = _query("SELECT job_title, company_name, details, created_at FROM jd_results WHERE share_token = %s",
                 (token,), one=True)

    if not row:
        return render_template("error.html", code=404, message="This link does not exist or sharing was turned off."), 404

    result = normalize_result(loads(row["details"], {}))
    result["job_title"] = row.get("job_title") or result["job_title"]
    result["company"] = row.get("company_name") or result["company"]

    response = Response(render_template("shared_result.html", result=result, created_at=row["created_at"]))
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Referrer-Policy"] = "no-referrer"

    return response
