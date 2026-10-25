"""
Dashboard: all numbers come from the user's own database records.
"""

import json
from collections import Counter

from flask import Blueprint, render_template, session

from models import repository
from models.repository import _query
from routes.career import roadmap_progress
from security import login_required


dashboard = Blueprint("dashboard", __name__)


def _number(value):

    return float(value) if value is not None else 0.0


def _split(value):

    try:
        data = json.loads(value)
        if isinstance(data, list):
            return data
    except (TypeError, ValueError):
        pass

    return [v.strip() for v in (value or "").split(",") if v.strip()]


def next_step(user_id, jd_row):
    """
    The user's most useful next step for their latest job match,
    worked out from saved data (suggestions, roadmap, interview).
    """

    jd_id = jd_row["jd_result_id"]
    title = jd_row["job_title"] or "your latest job match"

    if not repository.has_table("resume_suggestions"):
        return {"text": f"Review your result for {title}.", "label": "Open result", "url": f"/history/jd/{jd_id}"}

    counts = {
        r["status"]: r["n"] for r in _query(
            "SELECT status, COUNT(*) AS n FROM resume_suggestions WHERE user_id = %s AND jd_result_id = %s GROUP BY status",
            (user_id, jd_id)
        )
    }

    if not counts:
        return {"text": f"Get rewrite suggestions to improve your resume for {title}.",
                "label": "Improve resume", "url": f"/assistant/{jd_id}"}

    if counts.get("pending"):
        return {"text": f"You have {counts['pending']} suggestion(s) waiting for review for {title}.",
                "label": "Review suggestions", "url": f"/assistant/{jd_id}"}

    todo = _query(
        """
        SELECT skill FROM roadmap_items WHERE user_id = %s AND jd_result_id = %s AND status != 'done'
        ORDER BY FIELD(priority, 'high', 'medium', 'low'), item_id LIMIT 1
        """,
        (user_id, jd_id), one=True
    )

    if counts.get("accepted") and not todo:
        return {"text": f"Build a tailored resume for {title} with your {counts['accepted']} accepted change(s).",
                "label": "Build resume", "url": f"/optimize/{jd_id}"}

    if todo:
        return {"text": f"Next learning task for {title}: {todo['skill']}.",
                "label": "Open roadmap", "url": "/roadmap"}

    answered = _query(
        "SELECT COUNT(DISTINCT question_index) AS n FROM interview_answers WHERE user_id = %s AND jd_result_id = %s",
        (user_id, jd_id), one=True
    )["n"]

    if not answered:
        return {"text": f"Practise interview questions for {title}.",
                "label": "Mock interview", "url": f"/interview/{jd_id}"}

    return {"text": f"Updated your resume? Run {title} again to see your progress.",
            "label": "Reanalyze", "url": f"/job-match?from={jd_id}"}


@dashboard.route("/dashboard")
@login_required
def dashboard_page():

    user_id = session["user_id"]

    has_jd = repository.has_table("jd_results")
    has_versions = repository.has_table("resume_versions")

    # ---------------- Totals ----------------

    total_resumes = _query("SELECT COUNT(*) AS n FROM resumes WHERE user_id = %s", (user_id,), one=True)["n"]

    ats = _query(
        """
        SELECT COUNT(*) AS n, AVG(rr.ats_score) AS avg, MAX(rr.ats_score) AS best
        FROM resume_results rr JOIN resumes r ON rr.resume_id = r.resume_id
        WHERE r.user_id = %s
        """,
        (user_id,), one=True
    )

    general = _query(
        """
        SELECT COUNT(*) AS n, AVG(g.score) AS avg, MAX(g.score) AS best
        FROM general_results g JOIN resumes r ON g.resume_id = r.resume_id
        WHERE r.user_id = %s
        """,
        (user_id,), one=True
    )

    jd = {"n": 0, "avg": None, "best": None}
    jd_rows = []

    if has_jd:

        jd = _query(
            """
            SELECT COUNT(*) AS n, AVG(jd.score) AS avg, MAX(jd.score) AS best
            FROM jd_results jd JOIN resumes r ON jd.resume_id = r.resume_id
            WHERE r.user_id = %s
            """,
            (user_id,), one=True
        )

        jd_rows = _query(
            """
            SELECT jd.jd_result_id, jd.job_title, jd.score, jd.details, jd.created_at
            FROM jd_results jd JOIN resumes r ON jd.resume_id = r.resume_id
            WHERE r.user_id = %s
            ORDER BY jd.created_at, jd.jd_result_id
            """,
            (user_id,)
        )

    # ---------------- Score history charts ----------------

    recent_jd = jd_rows[-12:]

    jd_chart = {
        "labels": [f"#{i + 1} · {r['created_at'].strftime('%d %b')}" for i, r in enumerate(recent_jd)],
        "titles": [r["job_title"] or "Job" for r in recent_jd],
        "datasets": [{"label": "Job match score", "data": [round(_number(r["score"]), 1) for r in recent_jd]}],
        "max": 100,
    }

    general_rows = _query(
        """
        SELECT g.score, r.upload_date FROM general_results g
        JOIN resumes r ON g.resume_id = r.resume_id
        WHERE r.user_id = %s ORDER BY r.upload_date, g.general_result_id
        """,
        (user_id,)
    )[-12:]

    general_chart = {
        "labels": [r["upload_date"].strftime("%d %b") if r["upload_date"] else "" for r in general_rows],
        "datasets": [{"label": "Resume quality score", "data": [round(_number(r["score"]), 1) for r in general_rows]}],
        "max": 100,
    }

    # ---------------- Frequently missing skills ----------------

    missing = Counter()

    demonstrated = {"shown": 0, "listed": 0, "missing": 0}

    for row in jd_rows:

        try:
            details = json.loads(row["details"] or "{}")
        except ValueError:
            continue

        for m in details.get("mandatory", []):

            if m.get("status") == "missing":
                missing[m.get("requirement", "")] += 1
                demonstrated["missing"] += 1
            elif m.get("evidence") in ("experience", "project"):
                demonstrated["shown"] += 1
            else:
                demonstrated["listed"] += 1

    for row in _query(
        """
        SELECT rr.missing_skills FROM resume_results rr
        JOIN resumes r ON rr.resume_id = r.resume_id WHERE r.user_id = %s
        """,
        (user_id,)
    ):
        for skill in _split(row["missing_skills"]):
            missing[skill] += 1

    top_missing = [(k, v) for k, v in missing.most_common(8) if k]

    missing_chart = {
        "labels": [k for k, _ in top_missing],
        "datasets": [{"label": "Times missing", "data": [v for _, v in top_missing]}],
        "horizontal": True,
    }

    # ---------------- Recent items ----------------

    recent = []

    for row in _query(
        """
        SELECT rr.result_id AS id, jr.role_name AS title, rr.ats_score AS score, r.upload_date AS date
        FROM resume_results rr JOIN resumes r ON rr.resume_id = r.resume_id
        JOIN job_roles jr ON jr.role_id = rr.role_id
        WHERE r.user_id = %s ORDER BY r.upload_date DESC LIMIT 5
        """,
        (user_id,)
    ):
        recent.append({**row, "kind": "ats", "type": "ATS role"})

    for row in _query(
        """
        SELECT g.general_result_id AS id, 'General check' AS title, g.score, r.upload_date AS date
        FROM general_results g JOIN resumes r ON g.resume_id = r.resume_id
        WHERE r.user_id = %s ORDER BY r.upload_date DESC LIMIT 5
        """,
        (user_id,)
    ):
        recent.append({**row, "kind": "general", "type": "General"})

    for row in reversed(jd_rows[-5:]):
        recent.append({"id": row["jd_result_id"], "title": row["job_title"] or "Job", "score": row["score"],
                       "date": row["created_at"], "kind": "jd", "type": "Job match"})

    recent.sort(key=lambda r: r["date"] or 0, reverse=True)

    done, total = roadmap_progress(user_id)

    latest_jd = jd_rows[-1] if jd_rows else None

    saved_jobs = repository.list_saved_jobs(user_id)[:4] if repository.has_table("saved_jobs") else []

    return render_template(
        "dashboard.html",
        fullname=session.get("fullname", ""),
        total_resumes=total_resumes,
        total_versions=len(repository.list_versions(user_id)) if has_versions else 0,
        total_ats=ats["n"],
        average_ats=_number(ats["avg"]),
        highest_ats=_number(ats["best"]),
        total_general=general["n"],
        average_general=_number(general["avg"]),
        highest_general=_number(general["best"]),
        total_jd=jd["n"],
        average_jd=_number(jd["avg"]),
        highest_jd=_number(jd["best"]),
        jd_chart=jd_chart,
        general_chart=general_chart,
        missing_chart=missing_chart,
        demonstrated=demonstrated,
        recent=recent[:6],
        recent_versions=repository.list_versions(user_id)[:3] if has_versions else [],
        roadmap_done=done,
        roadmap_total=total,
        latest_jd=latest_jd,
        continue_step=next_step(user_id, latest_jd) if latest_jd else None,
        saved_jobs=saved_jobs,
    )
