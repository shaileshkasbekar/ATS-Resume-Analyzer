from flask import Blueprint, render_template, request, session, redirect, flash
from werkzeug.utils import secure_filename

import os
import json
import uuid

from config import Config
from models.database import get_db_connection, table_columns

from resume_parser.pdf_reader import extract_text_from_pdf
from resume_parser.jd_analyzer import analyze_job_match, plan_skills
from resume_parser.recommendation import build_learning_plan


# =========================================
# Blueprint
# =========================================

job_match = Blueprint("job_match", __name__)


MIN_JD_LENGTH = 100


# =========================================
# Job Description Match
# =========================================

@job_match.route("/job-match", methods=["GET", "POST"])
def match_job():

    if "user_id" not in session:

        return redirect("/login")


    if request.method == "GET":

        return render_template("job_match.html")


    # -----------------------------------------
    # Validate input
    # -----------------------------------------

    job_title = request.form.get("job_title", "").strip()

    jd_text = request.form.get("job_description", "").strip()

    resume = request.files.get("resume")


    if len(jd_text) < MIN_JD_LENGTH:

        flash("Please paste the full job description (at least a few lines).", "danger")

        return redirect("/job-match")


    if not resume or resume.filename == "":

        flash("Please select a resume.", "danger")

        return redirect("/job-match")


    if not resume.filename.lower().endswith(".pdf"):

        flash("Only PDF files are allowed.", "danger")

        return redirect("/job-match")


    # -----------------------------------------
    # Save PDF and read text
    # -----------------------------------------

    filename = secure_filename(resume.filename) or "resume.pdf"

    filepath = os.path.join(
        Config.UPLOAD_FOLDER,
        f"{uuid.uuid4().hex[:8]}_{filename}"
    )

    resume.save(filepath)

    text = extract_text_from_pdf(filepath)


    if not text.strip():

        os.remove(filepath)

        flash(
            "Could not read text from this PDF. "
            "If it is a scanned image, please upload a text-based PDF.",
            "danger"
        )

        return redirect("/job-match")


    # -----------------------------------------
    # Analyze
    # -----------------------------------------

    result = analyze_job_match(text, jd_text, job_title)


    if not result["ai_available"]:

        flash(
            "AI analysis is unavailable right now. "
            "Showing the keyword match only.",
            "warning"
        )


    # -----------------------------------------
    # Save to history
    # -----------------------------------------

    connection = get_db_connection()

    cursor = connection.cursor()


    try:

        if not table_columns(cursor, "jd_results"):

            os.remove(filepath)

            flash(
                "Result not saved to history: run the database upgrade "
                "(database/upgrade_v3.sql) to enable this.",
                "warning"
            )

        else:

            cursor.execute(
                "INSERT INTO resumes (user_id, file_name, file_path) VALUES (%s, %s, %s)",
                (session["user_id"], filename, filepath)
            )

            resume_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO jd_results
                (resume_id, job_title, job_description, score,
                 keyword_score, ai_relevance, experience_match, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    resume_id,
                    result["job_title"],
                    jd_text,
                    result["score"],
                    result["keyword_score"],
                    result["ai_relevance"],
                    result["experience_match"],
                    json.dumps(result["details"])
                )
            )

            connection.commit()

    except Exception as e:

        connection.rollback()

        print("Database Error:", e)

        flash("Analysis finished, but it could not be saved to your history.", "warning")

    finally:

        cursor.close()

        connection.close()


    return render_job_match_result(result, filename)


def render_job_match_result(result, filename):
    """
    Shared by the new result and the saved one in history.
    """

    missing, importance = plan_skills(result["details"])

    return render_template(
        "job_match_result.html",
        result=result,
        details=result["details"],
        filename=filename,
        learning_plan=build_learning_plan(missing, importance)
    )
