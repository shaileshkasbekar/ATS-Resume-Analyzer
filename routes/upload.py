"""
ATS Role Check: check a resume against a predefined job role.

Uses the same engine as Job Match (role mode), so a role check and a job
match give consistent, explainable scores. Older role-check results saved
by the previous engine stay viewable in History (routes/history.py).
"""

from flask import Blueprint, render_template, redirect

from models.database import get_db_connection
from security import login_required


upload = Blueprint("upload", __name__)


@upload.route("/upload", methods=["GET", "POST"])
@login_required
def upload_resume():

    from flask import request

    # Old forms and links that post here are handled by Job Match.
    # 307 keeps the method and the uploaded file.

    if request.method == "POST":
        return redirect("/job-match", code=307)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT role_id, role_name FROM job_roles ORDER BY role_name")
    job_roles = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("upload.html", job_roles=job_roles)
