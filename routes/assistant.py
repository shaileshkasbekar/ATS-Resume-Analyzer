"""
Phase 2: AI resume improvement assistant + job-specific resume optimization.
"""

import os
import uuid

from flask import Blueprint, Response, flash, redirect, render_template, request, session

from config import Config
from models import repository
from models.repository import _execute, _query
from pdf_export import html_to_pdf
from resume_parser.improvement import KIND_LABELS, generate_suggestions
from resume_parser.pdf_reader import extract_text_from_pdf
from resume_parser.resume_builder import TEMPLATES, build_resume, doc_to_text
from resume_parser.version_compare import compare_versions
from security import login_required, rate_limit


assistant = Blueprint("assistant", __name__)


STATUSES = ("pending", "accepted", "rejected")


def _load(jd_result_id):

    row = repository.get_jd_result(session["user_id"], jd_result_id)

    if not row:
        return None, None

    return row, repository.resume_text_for(row)


def _suggestions(jd_result_id, status=None):

    sql = "SELECT * FROM resume_suggestions WHERE user_id = %s AND jd_result_id = %s"
    params = [session["user_id"], jd_result_id]

    if status:
        sql += " AND status = %s"
        params.append(status)

    return _query(sql + " ORDER BY suggestion_id", tuple(params))


def _feature_ready():

    if not repository.has_table("resume_suggestions"):
        flash("Run the database upgrade (database/upgrade_v5.sql) to use the improvement assistant.", "warning")
        return False

    return True


# =========================================
# Improvement assistant
# =========================================

@assistant.route("/assistant/<int:jd_result_id>")
@login_required
def view(jd_result_id):

    if not _feature_ready():
        return redirect(f"/history/jd/{jd_result_id}")

    row, text = _load(jd_result_id)

    if not row:
        return redirect("/history")

    suggestions = _suggestions(jd_result_id)

    return render_template(
        "assistant.html",
        row=row,
        result=row["result"],
        suggestions=suggestions,
        kind_labels=KIND_LABELS,
        resume_missing=not text.strip(),
        counts={s: sum(1 for x in suggestions if x["status"] == s) for s in STATUSES}
    )


@assistant.route("/assistant/<int:jd_result_id>/generate", methods=["POST"])
@login_required
@rate_limit("assistant", 6, 600)
def generate(jd_result_id):

    if not _feature_ready():
        return redirect(f"/history/jd/{jd_result_id}")

    row, text = _load(jd_result_id)

    if not row:
        return redirect("/history")

    if not text.strip():
        flash("The resume file for this analysis is no longer available.", "danger")
        return redirect(f"/assistant/{jd_result_id}")

    suggestions, used_ai = generate_suggestions(text, row["result"])

    if not used_ai:
        flash("AI is unavailable, so only basic suggestions were generated.", "warning")

    # Replace pending suggestions; keep the ones the user already accepted or rejected

    _execute(
        "DELETE FROM resume_suggestions WHERE user_id = %s AND jd_result_id = %s AND status = 'pending'",
        (session["user_id"], jd_result_id)
    )

    for s in suggestions:
        _execute(
            """
            INSERT INTO resume_suggestions
            (user_id, jd_result_id, kind, original, improved, reason, requirement, evidence, needs_metric)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (session["user_id"], jd_result_id, s["kind"], s["original"], s["improved"],
             s["reason"], s["requirement"], s["evidence"], s["needs_metric"])
        )

    flash(f"{len(suggestions)} suggestions ready. Accept or reject each one.", "success")

    # Generated from the job match result page: go back there

    if request.form.get("next") == "result":
        return redirect(f"/history/jd/{jd_result_id}#suggestions")

    return redirect(f"/assistant/{jd_result_id}")


@assistant.route("/assistant/suggestion/<int:suggestion_id>", methods=["POST"])
@login_required
def update_suggestion(suggestion_id):
    """
    JSON: {"status": "accepted" | "rejected" | "pending", "improved": "..."}
    """

    data = request.get_json(silent=True) or {}

    status = data.get("status")

    if status not in STATUSES:
        return {"error": "Invalid status"}, 400

    improved = data.get("improved")

    if improved is not None:

        improved = str(improved).strip()

        if not improved or len(improved) > 1000:
            return {"error": "The improved text must be 1-1000 characters."}, 400

        _, count = _execute(
            "UPDATE resume_suggestions SET status = %s, improved = %s WHERE suggestion_id = %s AND user_id = %s",
            (status, improved, suggestion_id, session["user_id"])
        )

    else:

        _, count = _execute(
            "UPDATE resume_suggestions SET status = %s WHERE suggestion_id = %s AND user_id = %s",
            (status, suggestion_id, session["user_id"])
        )

    if not count and not _query(
        "SELECT 1 FROM resume_suggestions WHERE suggestion_id = %s AND user_id = %s",
        (suggestion_id, session["user_id"]), one=True
    ):
        return {"error": "Not found"}, 404

    return {"ok": True, "status": status}


# =========================================
# Optimized resume
# =========================================

def _optimized(jd_result_id, template):

    row, text = _load(jd_result_id)

    if not row or not text.strip():
        return None, None

    accepted = [
        {"kind": s["kind"], "original": s["original"] or "", "improved": s["improved"]}
        for s in _suggestions(jd_result_id, "accepted")
    ]

    return row, build_resume(text, accepted, template)


@assistant.route("/optimize/<int:jd_result_id>")
@login_required
def optimize(jd_result_id):

    if not _feature_ready():
        return redirect(f"/history/jd/{jd_result_id}")

    template = request.args.get("template", "modern")

    row, doc = _optimized(jd_result_id, template)

    if not row:
        flash("The resume for this analysis is not available.", "danger")
        return redirect("/history")

    # Before / after the accepted changes, scored against the same job
    # requirements by the same rule-based engine (no AI, so the only
    # difference is the accepted text)

    progress = None

    requirements = row["result"].get("requirements")

    if requirements and requirements.get("mandatory_skills") is not None and doc["applied_count"] > 0:

        # Baseline = the same resume rebuilt WITHOUT the accepted changes,
        # so layout differences cannot change the score

        baseline = build_resume(repository.resume_text_for(row), [], doc["template"])

        progress = compare_versions(doc_to_text(baseline), doc_to_text(doc), requirements)["job"]

    return render_template(
        "optimize.html",
        row=row,
        doc=doc,
        templates=TEMPLATES,
        progress=progress,
        accepted_count=len(_suggestions(jd_result_id, "accepted")),
        can_save_version=repository.has_table("resume_versions")
    )


def _pdf_for(doc):

    html = render_template("resume_doc.html", doc=doc)

    return html_to_pdf(html, doc["css"])


def _download_name(row, suffix):

    base = "".join(c if c.isalnum() else "_" for c in (row.get("job_title") or "resume"))[:40]

    return f"{base}_{suffix}.pdf"


@assistant.route("/optimize/<int:jd_result_id>/download")
@login_required
def download_optimized(jd_result_id):

    row, doc = _optimized(jd_result_id, request.args.get("template", "modern"))

    if not row:
        return redirect("/history")

    return Response(
        _pdf_for(doc),
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_download_name(row, "optimized_resume")}"'}
    )


@assistant.route("/optimize/<int:jd_result_id>/save", methods=["POST"])
@login_required
def save_optimized(jd_result_id):
    """
    Saves the optimized resume as a NEW resume version (the original stays).
    """

    template = request.form.get("template", "modern")

    row, doc = _optimized(jd_result_id, template)

    if not row or not repository.has_table("resume_versions"):
        return redirect("/history")

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    file_name = _download_name(row, f"optimized_{template}")

    path = os.path.join(Config.UPLOAD_FOLDER, f"{uuid.uuid4().hex[:8]}_{file_name}")

    with open(path, "wb") as file:
        file.write(_pdf_for(doc))

    label = f"Optimized for {row.get('job_title') or 'job'} ({TEMPLATES[doc['template']]['label']})"[:100]

    repository.add_version(session["user_id"], label, file_name, path, extract_text_from_pdf(path))

    flash("Saved as a new resume version. Your original resume was not changed.", "success")

    return redirect("/resumes")
