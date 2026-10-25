"""
Downloadable PDF reports for every analysis type.
Only the owner of a record can download its report.
"""

from datetime import datetime

from flask import Blueprint, Response, redirect, render_template, session

from models import repository
from models.repository import _query, loads
from pdf_export import html_to_pdf
from routes.job_match import normalize_result
from security import login_required


reports = Blueprint("reports", __name__)


def _pdf_response(html, name):

    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60] or "report"

    return Response(
        html_to_pdf(html),
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pdf"'}
    )


def _split(value):
    """
    Lists saved as JSON or (older rows) as comma-separated text.
    """

    data = loads(value, None)

    if isinstance(data, list):
        return data

    return [v.strip() for v in (value or "").split(",") if v.strip()]


@reports.route("/report/jd/<int:result_id>.pdf")
@login_required
def job_match_report(result_id):

    row = repository.get_jd_result(session["user_id"], result_id)

    if not row:
        return redirect("/history")

    result = normalize_result(row["result"])

    result["job_title"] = row.get("job_title") or result["job_title"]
    result["company"] = row.get("company_name") or result["company"]

    html = render_template(
        "reports/job_match_report.html",
        r=result,
        file_name=row["file_name"],
        generated=datetime.now().strftime("%d %b %Y")
    )

    return _pdf_response(html, f"job_match_{result['job_title'] or result_id}")


@reports.route("/report/ats/<int:result_id>.pdf")
@login_required
def ats_report(result_id):

    row = _query(
        """
        SELECT rr.*, r.file_name, jr.role_name
        FROM resume_results rr
        JOIN resumes r ON r.resume_id = rr.resume_id
        JOIN job_roles jr ON jr.role_id = rr.role_id
        WHERE rr.result_id = %s AND r.user_id = %s
        """,
        (result_id, session["user_id"]),
        one=True
    )

    if not row:
        return redirect("/history")

    html = render_template(
        "reports/ats_report.html",
        row=row,
        matched=_split(row.get("matched_skills")),
        missing=_split(row.get("missing_skills")),
        recommended=_split(row.get("recommended_skills")),
        strengths=loads(row.get("strengths"), []),
        weaknesses=loads(row.get("weaknesses"), []),
        ai_recommendations=loads(row.get("ai_recommendations"), []),
        generated=datetime.now().strftime("%d %b %Y")
    )

    return _pdf_response(html, f"ats_report_{row['role_name']}")


@reports.route("/report/general/<int:result_id>.pdf")
@login_required
def general_report(result_id):

    row = _query(
        """
        SELECT g.*, r.file_name
        FROM general_results g
        JOIN resumes r ON r.resume_id = g.resume_id
        WHERE g.general_result_id = %s AND r.user_id = %s
        """,
        (result_id, session["user_id"]),
        one=True
    )

    if not row:
        return redirect("/history")

    html = render_template(
        "reports/general_report.html",
        row=row,
        sections=loads(row.get("sections"), {}),
        skills=loads(row.get("skills"), []),
        recommendations=loads(row.get("recommendations"), []),
        strengths=loads(row.get("ai_strengths"), []),
        weaknesses=loads(row.get("ai_weaknesses"), []),
        issues=loads(row.get("issues"), {}),
        generated=datetime.now().strftime("%d %b %Y")
    )

    return _pdf_response(html, "resume_quality_report")
