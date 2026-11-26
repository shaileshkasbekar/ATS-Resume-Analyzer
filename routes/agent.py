"""
Career Agent pages (Agentic AI).

/agent                 goal + resume (+ optional job) form, memory, recent runs
/agent/run/<id>        the result: plan, each agent's work, artifacts, trace
                       (refreshes itself while the agents are still working)
/agent/memory/forget   delete remembered facts
/agent/run/<id>/delete

An agent run can take a minute (several AI calls), longer than a normal web
request should. So the run is started in a background thread and the run
page refreshes every few seconds, showing the live execution trace.
"""

import json
import os
import threading
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session

from agents import memory
from agents.graph import run_career_agent
from agents.specialists import ORDER, SPECIALISTS
from agents.tracking import Tracker
from models import repository
from models.repository import _execute, _query
from resume_parser.document_reader import extract_links
from routes.job_match import save_resume_upload
from security import login_required, rate_limit


agent = Blueprint("agent", __name__)


PRESETS = [
    "Analyse my resume and tell me my strengths and weaknesses.",
    "How well do I match this job, and which skills am I missing?",
    "Which job role suits my resume best?",
    "Improve my project descriptions and give me ATS keywords for this job.",
    "Make me a learning roadmap and project ideas to become job-ready.",
]

STALE_AFTER = timedelta(minutes=10)


def _ready():

    try:
        return repository.has_table("agent_runs") and repository.has_table("agent_memory")
    except Exception:
        return False


# =========================================================
# Inputs
# =========================================================

def _resume_from_form(user_id):
    """
    Returns (resume_text, links, error).
    """

    source = request.form.get("resume_source", "upload")

    if source.startswith("v:") and source[2:].isdigit():

        version = repository.get_version(user_id, int(source[2:]))

        if version and version.get("resume_text"):
            return version["resume_text"], [], None

        return "", [], "That resume version was not found."

    if source.startswith("jd:") and source[3:].isdigit():

        row = repository.get_jd_result(user_id, int(source[3:]))

        text = repository.resume_text_for(row) if row else ""

        if text.strip():
            return text, [], None

        return "", [], "The resume of that analysis is no longer available. Please upload it again."

    filename, filepath, text, error = save_resume_upload(request.files.get("resume"))

    if error:
        return "", [], error

    links = extract_links(filepath)

    # The agent only needs the text; the file is not kept
    try:
        os.remove(filepath)
    except OSError:
        pass

    return text, links, None


def _job_from_form(user_id):
    """
    Returns (jd_text, job_title).
    """

    saved = request.form.get("saved_job_id", "")

    if saved.isdigit():

        job = repository.get_saved_job(user_id, int(saved))

        if job:
            return job.get("description") or "", job.get("title") or ""

    return request.form.get("job_description", "").strip()[:20000], request.form.get("job_title", "").strip()[:200]


# =========================================================
# Background run
# =========================================================

def _run_in_background(tracker, user_id, goal, resume_text, jd_text, job_title, links):

    try:
        run_career_agent(user_id, goal, resume_text, jd_text, job_title, links=links, tracker=tracker)
    except Exception as e:
        print("Career agent thread failed:", repr(e))
        tracker.finish("failed", error="The agent stopped unexpectedly.")


# =========================================================
# Pages
# =========================================================

@agent.route("/agent", methods=["GET", "POST"])
@login_required
@rate_limit("agent_run", 5, 600)
def agent_home():

    user_id = session["user_id"]
    ready = _ready()

    if request.method == "POST":

        if not ready:
            flash("Run the database upgrade (database/upgrade_v7.sql) to use the Career Agent.", "warning")
            return redirect("/agent")

        goal = " ".join(request.form.get("goal", "").split())[:1000]

        if len(goal) < 5:
            flash("Tell the agent your goal in a few words.", "danger")
            return redirect("/agent")

        resume_text, links, error = _resume_from_form(user_id)

        if error:
            flash(error, "danger")
            return redirect("/agent?goal=" + goal[:300])

        jd_text, job_title = _job_from_form(user_id)

        tracker = Tracker(user_id, goal)

        if not tracker.run_id:
            flash("Could not start the agent. Please try again.", "danger")
            return redirect("/agent")

        args = (tracker, user_id, goal, resume_text, jd_text, job_title, links)

        if current_app.config.get("AGENT_SYNC"):
            _run_in_background(*args)
        else:
            threading.Thread(target=_run_in_background, args=args, daemon=True).start()

        return redirect(f"/agent/run/{tracker.run_id}")

    versions, analyses, saved_jobs, runs, remembered = [], [], [], [], {}

    if ready:
        versions = repository.list_versions(user_id) if repository.has_table("resume_versions") else []
        analyses = repository.list_jd_results(user_id, limit=8)
        saved_jobs = repository.list_saved_jobs(user_id) if repository.has_table("saved_jobs") else []
        runs = _query(
            "SELECT run_id, goal, status, started_at FROM agent_runs WHERE user_id = %s ORDER BY run_id DESC LIMIT 8",
            (user_id,)
        )
        remembered = memory.recall(user_id)

    return render_template(
        "agent.html",
        ready=ready,
        presets=PRESETS,
        goal=request.args.get("goal", "")[:1000],
        versions=versions,
        analyses=analyses,
        saved_jobs=saved_jobs,
        runs=runs,
        remembered=remembered,
        memory_labels=memory.ALLOWED_KEYS,
        specialists=[(name, SPECIALISTS[name]) for name in ORDER],
    )


@agent.route("/agent/run/<int:run_id>")
@login_required
def agent_run(run_id):

    if not _ready():
        return redirect("/agent")

    user_id = session["user_id"]

    run = _query("SELECT * FROM agent_runs WHERE run_id = %s AND user_id = %s", (run_id, user_id), one=True)

    if not run:
        abort(404)

    # A run that never finished (e.g. the server restarted) is shown as failed
    if run["status"] == "running" and run["started_at"] and datetime.now() - run["started_at"] > STALE_AFTER:
        _execute("UPDATE agent_runs SET status = 'failed', error = %s WHERE run_id = %s AND user_id = %s",
                 ("The run did not finish (timeout).", run_id, user_id))
        run["status"], run["error"] = "failed", "The run did not finish (timeout)."

    steps = _query(
        "SELECT step_no, agent, kind, name, input_data, output_data, ok, duration_ms "
        "FROM agent_steps WHERE run_id = %s ORDER BY step_no",
        (run_id,)
    )

    result = repository.loads(run.get("result"), {}) or {}

    plan = result.get("plan") or repository.loads(run.get("plan"), []) or []

    # While running, show the plan as soon as the planner has decided
    if not plan:
        for step in steps:
            if step["kind"] == "plan":
                plan = (repository.loads(step["output_data"], {}) or {}).get("agents", [])

    return render_template(
        "agent_run.html",
        run=run,
        running=run["status"] == "running",
        result=result,
        plan=plan,
        artifacts=result.get("artifacts", {}),
        steps=steps,
        specialists=SPECIALISTS,
        total_ms=sum(s["duration_ms"] or 0 for s in steps),
        pretty=_pretty,
    )


@agent.route("/agent/run/<int:run_id>/delete", methods=["POST"])
@login_required
def delete_run(run_id):

    if _ready():
        _execute("DELETE FROM agent_runs WHERE run_id = %s AND user_id = %s", (run_id, session["user_id"]))
        flash("Agent run deleted.", "success")

    return redirect("/agent")


@agent.route("/agent/memory/forget", methods=["POST"])
@login_required
def forget_memory():

    key = request.form.get("key") or None

    if key and key not in memory.ALLOWED_KEYS:
        abort(400)

    memory.forget(session["user_id"], key)

    flash("The agent forgot that." if key else "The agent's memory about you was cleared.", "success")

    return redirect("/agent")


def _pretty(text):
    """
    Trace input/output, formatted for reading.
    """

    try:
        return json.dumps(json.loads(text), indent=2, ensure_ascii=False)[:3000]
    except (TypeError, ValueError):
        return (text or "")[:3000]
