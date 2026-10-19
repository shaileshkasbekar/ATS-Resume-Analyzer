from flask import Blueprint, render_template, session, redirect
from models.database import get_db_connection

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/dashboard")
def dashboard_page():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    user_id = session["user_id"]

    try:

        # --------------------------------
        # Total Resumes
        # --------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total_resumes
            FROM resumes
            WHERE user_id = %s
            """,
            (user_id,)
        )

        total_resumes = cursor.fetchone()["total_resumes"]


        # --------------------------------
        # ATS Analysis Statistics
        # --------------------------------

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_ats,
                AVG(rr.ats_score) AS average_ats,
                MAX(rr.ats_score) AS highest_ats
            FROM resume_results rr
            JOIN resumes r
                ON rr.resume_id = r.resume_id
            WHERE r.user_id = %s
            """,
            (user_id,)
        )

        ats_data = cursor.fetchone()


        # --------------------------------
        # General Analysis Statistics
        # --------------------------------

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_general,
                AVG(gr.score) AS average_general,
                MAX(gr.score) AS highest_general
            FROM general_results gr
            JOIN resumes r
                ON gr.resume_id = r.resume_id
            WHERE r.user_id = %s
            """,
            (user_id,)
        )

        general_data = cursor.fetchone()


    finally:

        cursor.close()
        connection.close()


    # --------------------------------
    # Dashboard Data
    # --------------------------------

    return render_template(
        "dashboard.html",

        fullname=session["fullname"],

        total_resumes=total_resumes,

        total_ats=ats_data["total_ats"],
        average_ats=ats_data["average_ats"] or 0,
        highest_ats=ats_data["highest_ats"] or 0,

        total_general=general_data["total_general"],
        average_general=general_data["average_general"] or 0,
        highest_general=general_data["highest_general"] or 0
    )