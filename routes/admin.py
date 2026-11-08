"""
Admin page: manage job roles, skill groups and skills from the browser.

Admins are the users whose email is listed in ADMIN_EMAILS in .env
(comma-separated). Everyone else gets "not found".
"""

import os
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session

from models.repository import _execute, _query
from resume_parser.skill_extractor import register_skills
from security import login_required


admin = Blueprint("admin", __name__)

GROUP_TYPES = ("common", "technology")
IMPORTANCE = ("core", "supporting", "optional")


def admin_emails():

    return {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}


def is_admin():

    if "user_id" not in session or not admin_emails():
        return False

    user = _query("SELECT email FROM users WHERE user_id = %s", (session["user_id"],), one=True)

    return bool(user) and user["email"].lower() in admin_emails()


def admin_required(view):

    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not is_admin():
            abort(404)
        return view(*args, **kwargs)

    return wrapper


def _back(message, kind="danger"):

    flash(message, kind)

    return redirect("/admin")


@admin.route("/admin")
@admin_required
def index():

    roles = _query("SELECT role_id, role_name, description FROM job_roles ORDER BY role_name")

    groups = _query("SELECT group_id, role_id, group_name, group_type FROM role_skill_groups ORDER BY group_type, group_name")

    skills = _query("SELECT id, group_id, skill_name, importance, weight FROM job_role_skills ORDER BY FIELD(importance, 'core', 'supporting', 'optional'), skill_name")

    usage = {r["role_id"]: r["n"] for r in _query(
        """
        SELECT role_id, COUNT(*) AS n FROM (
            SELECT role_id FROM resume_results
            UNION ALL SELECT role_id FROM jd_results WHERE role_id IS NOT NULL
        ) used GROUP BY role_id
        """
    )} if "role_id" in _columns("jd_results") else {}

    for role in roles:
        role["groups"] = [g for g in groups if g["role_id"] == role["role_id"]]
        role["uses"] = usage.get(role["role_id"], 0)
        for group in role["groups"]:
            group["skills"] = [s for s in skills if s["group_id"] == group["group_id"]]

    return render_template("admin.html", roles=roles, group_types=GROUP_TYPES, importance=IMPORTANCE)


def _columns(table):

    from models.repository import columns_of

    return columns_of(table)


@admin.route("/admin/roles", methods=["POST"])
@admin_required
def add_role():

    name = request.form.get("role_name", "").strip()[:100]
    description = request.form.get("description", "").strip()[:1000]

    if len(name) < 2:
        return _back("Please enter a role name.")

    if _query("SELECT 1 AS x FROM job_roles WHERE role_name = %s", (name,), one=True):
        return _back("A role with this name already exists.")

    _execute("INSERT INTO job_roles (role_name, description) VALUES (%s, %s)", (name, description))

    return _back(f"Role \"{name}\" added. Now add its skill groups.", "success")


@admin.route("/admin/roles/<int:role_id>/delete", methods=["POST"])
@admin_required
def delete_role(role_id):

    # Deleting a role would also delete users' saved results for it

    used = _query("SELECT COUNT(*) AS n FROM resume_results WHERE role_id = %s", (role_id,), one=True)["n"]

    if "role_id" in _columns("jd_results"):
        used += _query("SELECT COUNT(*) AS n FROM jd_results WHERE role_id = %s", (role_id,), one=True)["n"]

    if used:
        return _back(f"This role is used by {used} saved analyses, so it cannot be deleted (that would delete users' history).")

    _execute("DELETE FROM job_roles WHERE role_id = %s", (role_id,))

    return _back("Role deleted.", "success")


@admin.route("/admin/groups", methods=["POST"])
@admin_required
def add_group():

    role_id = request.form.get("role_id", "")
    name = request.form.get("group_name", "").strip()[:100]
    group_type = request.form.get("group_type", "")

    if not role_id.isdigit() or not _query("SELECT 1 AS x FROM job_roles WHERE role_id = %s", (int(role_id),), one=True):
        return _back("Please choose a role.")

    if len(name) < 2 or group_type not in GROUP_TYPES:
        return _back("Please enter a group name and type.")

    if _query("SELECT 1 AS x FROM role_skill_groups WHERE role_id = %s AND group_name = %s", (int(role_id), name), one=True):
        return _back("This role already has a group with that name.")

    _execute("INSERT INTO role_skill_groups (role_id, group_name, group_type) VALUES (%s, %s, %s)",
             (int(role_id), name, group_type))

    return _back(f"Group \"{name}\" added.", "success")


@admin.route("/admin/groups/<int:group_id>/delete", methods=["POST"])
@admin_required
def delete_group(group_id):

    _execute("DELETE FROM role_skill_groups WHERE group_id = %s", (group_id,))

    return _back("Group and its skills deleted.", "success")


def _weight(value):

    try:
        weight = round(float(value), 2)
    except (TypeError, ValueError):
        return None

    return weight if 0.5 <= weight <= 10 else None


@admin.route("/admin/skills", methods=["POST"])
@admin_required
def add_skill():

    group_id = request.form.get("group_id", "")
    name = request.form.get("skill_name", "").strip()[:100]
    importance = request.form.get("importance", "")
    weight = _weight(request.form.get("weight"))

    group = _query("SELECT group_id, role_id FROM role_skill_groups WHERE group_id = %s",
                   (int(group_id),), one=True) if group_id.isdigit() else None

    if not group:
        return _back("Please choose a group.")

    if len(name) < 1 or importance not in IMPORTANCE or weight is None:
        return _back("Please enter a skill name, importance and a weight between 0.5 and 10.")

    if _query("SELECT 1 AS x FROM job_role_skills WHERE group_id = %s AND skill_name = %s", (group["group_id"], name), one=True):
        return _back("This group already has that skill.")

    _execute(
        "INSERT INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES (%s, %s, %s, %s, %s)",
        (group["role_id"], group["group_id"], name, importance, weight)
    )

    # Recognise the new skill in resumes and job descriptions right away

    register_skills([name])

    return _back(f"Skill \"{name}\" added.", "success")


@admin.route("/admin/skills/<int:skill_id>", methods=["POST"])
@admin_required
def update_skill(skill_id):

    if request.form.get("action") == "delete":
        _execute("DELETE FROM job_role_skills WHERE id = %s", (skill_id,))
        return _back("Skill removed.", "success")

    importance = request.form.get("importance", "")
    weight = _weight(request.form.get("weight"))

    if importance not in IMPORTANCE or weight is None:
        return _back("Importance must be core, supporting or optional, and the weight between 0.5 and 10.")

    _execute("UPDATE job_role_skills SET importance = %s, weight = %s WHERE id = %s", (importance, weight, skill_id))

    return _back("Skill updated.", "success")


def load_registered_skills():
    """
    Called at start-up: every role skill in the database is recognised.
    """

    try:
        register_skills(r["skill_name"] for r in _query("SELECT DISTINCT skill_name FROM job_role_skills"))
    except Exception as e:
        print("Could not load role skills:", e)
