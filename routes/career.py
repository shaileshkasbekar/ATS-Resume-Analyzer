"""
Phase 3: learning roadmap, project recommendations, mock interview.
All built from a saved job match result and owned by the user.
"""

import json
from datetime import datetime

from flask import Blueprint, Response, flash, redirect, render_template, request, session

from models import repository
from models.repository import _execute, _query, loads
from pdf_export import html_to_pdf
from resume_parser.career import (
    CATEGORY_LABELS,
    FEEDBACK_CRITERIA,
    answer_feedback,
    build_roadmap,
    interview_questions,
    recommend_projects
)
from security import login_required, rate_limit


career = Blueprint("career", __name__)


def _ready(table):

    if not repository.has_table(table):
        flash("Run the database upgrade (database/upgrade_v5.sql) to use this feature.", "warning")
        return False

    return True


def _load(jd_result_id):

    row = repository.get_jd_result(session["user_id"], jd_result_id)

    if not row:
        return None, ""

    return row, repository.resume_text_for(row)


# =========================================
# Learning roadmap
# =========================================

def roadmap_items(user_id):

    rows = _query(
        """
        SELECT ri.*, jd.job_title
        FROM roadmap_items ri
        JOIN jd_results jd ON jd.jd_result_id = ri.jd_result_id
        WHERE ri.user_id = %s
        ORDER BY ri.jd_result_id DESC, FIELD(ri.priority, 'high', 'medium', 'low'), ri.item_id
        """,
        (user_id,)
    )

    for row in rows:
        row["objectives"] = loads(row["objectives"], [])
        row["exercises"] = loads(row["exercises"], [])

    return rows


def roadmap_progress(user_id):
    """
    (done, total) over all roadmap items of the user.
    """

    if not repository.has_table("roadmap_items"):
        return 0, 0

    row = _query(
        "SELECT SUM(status = 'done') AS done, COUNT(*) AS total FROM roadmap_items WHERE user_id = %s",
        (user_id,),
        one=True
    )

    return int(row["done"] or 0), int(row["total"] or 0)


@career.route("/roadmap")
@login_required
def roadmap():

    if not _ready("roadmap_items"):
        return redirect("/dashboard")

    items = roadmap_items(session["user_id"])

    # Tasks grouped by priority (most important first)

    priorities = [
        {"key": "high", "title": "Required skills to learn", "hint": "The job requires these and your resume does not show them."},
        {"key": "medium", "title": "Required skills to show better", "hint": "You list these, but no project or job shows them."},
        {"key": "low", "title": "Preferred skills", "hint": "Nice to have. Work on these after the required ones."},
    ]

    for group in priorities:
        group["items"] = [i for i in items if i["priority"] == group["key"]]
        group["done"] = sum(1 for i in group["items"] if i["status"] == "done")

    # One entry per job, for "reanalyze" and "remove"

    jobs = {}

    for item in items:

        job = jobs.setdefault(item["jd_result_id"], {
            "jd_result_id": item["jd_result_id"],
            "job_title": item["job_title"] or "Job",
            "done": 0,
            "total": 0
        })

        job["total"] += 1
        job["done"] += item["status"] == "done"

    done, total = roadmap_progress(session["user_id"])

    return render_template(
        "roadmap.html",
        priorities=[g for g in priorities if g["items"]],
        jobs=list(jobs.values()),
        done=done,
        total=total
    )


@career.route("/roadmap/create/<int:jd_result_id>", methods=["POST"])
@login_required
@rate_limit("roadmap", 10, 600)
def create_roadmap(jd_result_id):

    if not _ready("roadmap_items"):
        return redirect(f"/history/jd/{jd_result_id}")

    row, text = _load(jd_result_id)

    if not row:
        return redirect("/history")

    items, used_ai = build_roadmap(row["result"], text)

    if not items:
        flash("No skill gaps were found for this job, so there is nothing to add to your roadmap.", "success")
        return redirect(f"/history/jd/{jd_result_id}")

    for item in items:
        _execute(
            """
            INSERT IGNORE INTO roadmap_items
            (user_id, jd_result_id, skill, priority, why, objectives, exercises,
             project_extension, demonstrate, resource_name, resource_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (session["user_id"], jd_result_id, item["skill"], item["priority"], item["why"],
             json.dumps(item["objectives"]), json.dumps(item["exercises"]), item["project_extension"],
             item["demonstrate"], item["resource_name"], item["resource_url"])
        )

    flash(f"Added {len(items)} skills to your learning roadmap." + ("" if used_ai else " (AI unavailable: standard plan used.)"), "success")

    return redirect("/roadmap")


@career.route("/roadmap/item/<int:item_id>", methods=["POST"])
@login_required
def toggle_item(item_id):
    """
    JSON {"done": true|false}
    """

    done = bool((request.get_json(silent=True) or {}).get("done"))

    _, count = _execute(
        """
        UPDATE roadmap_items
        SET status = %s, completed_at = IF(%s, CURRENT_TIMESTAMP, NULL)
        WHERE item_id = %s AND user_id = %s
        """,
        ("done" if done else "todo", done, item_id, session["user_id"])
    )

    if not count and not _query("SELECT 1 FROM roadmap_items WHERE item_id = %s AND user_id = %s",
                                (item_id, session["user_id"]), one=True):
        return {"error": "Not found"}, 404

    completed, total = roadmap_progress(session["user_id"])

    return {"ok": True, "done": completed, "total": total}


@career.route("/roadmap/<int:jd_result_id>/delete", methods=["POST"])
@login_required
def delete_roadmap(jd_result_id):

    _execute("DELETE FROM roadmap_items WHERE jd_result_id = %s AND user_id = %s", (jd_result_id, session["user_id"]))

    flash("Roadmap removed.", "success")

    return redirect("/roadmap")


@career.route("/roadmap.pdf")
@login_required
def roadmap_pdf():

    if not repository.has_table("roadmap_items"):
        return redirect("/dashboard")

    html = render_template(
        "reports/roadmap_report.html",
        items=roadmap_items(session["user_id"]),
        generated=datetime.now().strftime("%d %b %Y")
    )

    return Response(html_to_pdf(html), mimetype="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="learning_roadmap.pdf"'})


# =========================================
# Project recommendations
# =========================================

@career.route("/projects/<int:jd_result_id>", methods=["GET", "POST"])
@login_required
@rate_limit("projects", 6, 600)
def projects(jd_result_id):

    if not _ready("generated_content"):
        return redirect(f"/history/jd/{jd_result_id}")

    row, text = _load(jd_result_id)

    if not row:
        return redirect("/history")

    content = repository.get_generated(session["user_id"], jd_result_id, "projects")

    if request.method == "POST":

        ideas, used_ai = recommend_projects(row["result"], text)

        content = {"ideas": ideas, "ai": used_ai}

        repository.save_generated(session["user_id"], jd_result_id, "projects", content)

        if not used_ai:
            flash("AI unavailable: showing standard project ideas.", "warning")

        return redirect(f"/projects/{jd_result_id}")

    return render_template("projects.html", row=row, content=content)


# =========================================
# Mock interview
# =========================================

def _answers(jd_result_id):

    rows = _query(
        "SELECT * FROM interview_answers WHERE user_id = %s AND jd_result_id = %s ORDER BY answer_id",
        (session["user_id"], jd_result_id)
    )

    latest = {}

    for r in rows:
        r["feedback"] = loads(r["feedback"], {})
        latest[r["question_index"]] = r

    return latest


@career.route("/interview/<int:jd_result_id>", methods=["GET", "POST"])
@login_required
@rate_limit("interview_generate", 6, 600)
def interview(jd_result_id):

    if not _ready("interview_answers"):
        return redirect(f"/history/jd/{jd_result_id}")

    row, text = _load(jd_result_id)

    if not row:
        return redirect("/history")

    content = repository.get_generated(session["user_id"], jd_result_id, "interview")

    if request.method == "POST":

        questions, used_ai = interview_questions(row["result"], text)

        repository.save_generated(session["user_id"], jd_result_id, "interview", {"questions": questions, "ai": used_ai})

        if not used_ai:
            flash("AI unavailable: showing standard practice questions.", "warning")

        return redirect(f"/interview/{jd_result_id}")

    return render_template(
        "interview.html",
        row=row,
        content=content,
        answers=_answers(jd_result_id),
        labels=CATEGORY_LABELS,
        criteria=FEEDBACK_CRITERIA
    )


@career.route("/interview/<int:jd_result_id>/answer", methods=["POST"])
@login_required
@rate_limit("interview_answer", 20, 600)
def submit_answer(jd_result_id):
    """
    JSON {"index": n, "answer": "..."} -> feedback
    """

    data = request.get_json(silent=True) or {}

    answer = str(data.get("answer") or "").strip()

    if not 10 <= len(answer) <= 4000:
        return {"error": "Please write an answer of at least a sentence (max 4000 characters)."}, 400

    row, text = _load(jd_result_id)

    content = repository.get_generated(session["user_id"], jd_result_id, "interview") if row else None

    try:
        index = int(data.get("index"))
        question = content["questions"][index]
    except (TypeError, ValueError, IndexError, KeyError):
        return {"error": "Question not found"}, 404

    feedback = answer_feedback(question["question"], answer, text, row.get("job_title") or "")

    _execute(
        """
        INSERT INTO interview_answers (user_id, jd_result_id, question_index, question, answer, feedback)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (session["user_id"], jd_result_id, index, question["question"], answer, json.dumps(feedback))
    )

    return {"ok": True, "feedback": feedback}
