from flask import Blueprint, render_template, request, session, redirect, flash

from resume_parser.pdf_reader import extract_text_from_pdf
from resume_parser.general_analyzer import analyze_resume
from resume_parser.general_ai_analyzer import analyze_general_resume_with_ai
from resume_parser.ai_client import get_score

from werkzeug.utils import secure_filename

from models.database import get_db_connection
from config import Config

import os
import json
import uuid


# =========================================
# Blueprint
# =========================================

general_analyzer = Blueprint(
    "general_analyzer",
    __name__
)


# =========================================
# General Analyzer Route
# =========================================

@general_analyzer.route(
    "/general-analyzer",
    methods=["GET", "POST"]
)
def analyze():

    # =========================================
    # Check Login
    # =========================================

    if "user_id" not in session:

        return redirect("/login")


    # =========================================
    # POST REQUEST
    # =========================================

    if request.method == "POST":

        # -----------------------------------------
        # Get Resume
        # -----------------------------------------

        resume = request.files.get("resume")


        if not resume or resume.filename == "":

            flash("Please select a resume.", "danger")

            return redirect("/general-analyzer")


        # -----------------------------------------
        # Allow only PDF
        # -----------------------------------------

        if not resume.filename.lower().endswith(".pdf"):

            flash("Only PDF files are allowed.", "danger")

            return redirect("/general-analyzer")


        # -----------------------------------------
        # Secure filename
        # -----------------------------------------

        filename = secure_filename(
            resume.filename
        ) or "resume.pdf"


        # -----------------------------------------
        # Create file path
        # -----------------------------------------

        # Unique prefix so two uploads with the same
        # name never overwrite each other

        filepath = os.path.join(
            Config.UPLOAD_FOLDER,
            f"{uuid.uuid4().hex[:8]}_{filename}"
        )


        # -----------------------------------------
        # Save PDF
        # -----------------------------------------

        resume.save(filepath)


        # =========================================
        # EXTRACT TEXT
        # =========================================

        text = extract_text_from_pdf(
            filepath
        )


        if not text.strip():

            os.remove(filepath)

            flash(
                "Could not read text from this PDF. "
                "If it is a scanned image, please upload "
                "a text-based PDF.",
                "danger"
            )

            return redirect("/general-analyzer")


        # =========================================
        # RULE-BASED ANALYSIS
        # =========================================

        result = analyze_resume(
            text
        )


        # =========================================
        # AI GENERAL ANALYSIS
        # =========================================

        print("\n==============================")
        print("RUNNING GENERAL AI ANALYSIS")
        print("==============================")


        ai_result = analyze_general_resume_with_ai(
            text
        )


        # -----------------------------------------
        # Check AI result
        # -----------------------------------------

        # If the AI fails, continue with the
        # rule-based analysis only

        ai_available = bool(ai_result)


        if not ai_available:

            ai_result = {}

            flash(
                "AI analysis is unavailable right now. "
                "Showing the rule-based score only.",
                "warning"
            )


        print("\nAI RESULT:")

        print(
            ai_result
        )


        # =========================================
        # RULE-BASED SCORE
        # =========================================

        rule_score = float(
            result.get(
                "score",
                0
            )
        )


        # =========================================
        # AI SCORES
        # =========================================

        ai_quality = get_score(
            ai_result,
            "overall_quality"
        )


        summary_quality = get_score(
            ai_result,
            "summary_quality"
        )


        experience_quality = get_score(
            ai_result,
            "experience_quality"
        )


        project_quality = get_score(
            ai_result,
            "project_quality"
        )


        skills_quality = get_score(
            ai_result,
            "skills_quality"
        )


        clarity_quality = get_score(
            ai_result,
            "clarity_quality"
        )


        # =========================================
        # AI TEXT RESULTS
        # =========================================

        ai_strengths = ai_result.get(
            "strengths",
            []
        )


        ai_weaknesses = ai_result.get(
            "weaknesses",
            []
        )


        ai_recommendations = ai_result.get(
            "recommendations",
            []
        )


        # =========================================
        # FINAL HYBRID SCORE
        # =========================================
        #
        # Rule-based score = 50%
        # AI quality       = 50%
        #
        # =========================================

        final_score = (

            (rule_score * 0.50)

            +

            (ai_quality * 0.50)

        )


        # Without AI, use the rule-based score alone

        if not ai_available:

            final_score = rule_score


        final_score = round(
            min(
                max(
                    final_score,
                    0
                ),
                100
            ),
            2
        )


        # =========================================
        # PRINT SCORES
        # =========================================

        print("\n==============================")
        print("GENERAL RESUME RESULT")
        print("==============================")


        print(
            "Rule-based Score:",
            rule_score
        )


        print(
            "AI Quality:",
            ai_quality
        )


        print(
            "Final General Score:",
            final_score
        )


        print(
            "Summary Quality:",
            summary_quality
        )


        print(
            "Experience Quality:",
            experience_quality
        )


        print(
            "Project Quality:",
            project_quality
        )


        print(
            "Skills Quality:",
            skills_quality
        )


        print(
            "Clarity Quality:",
            clarity_quality
        )


        # =========================================
        # COMBINE RECOMMENDATIONS
        # =========================================

        general_recommendations = list(
            result.get(
                "recommendations",
                []
            )
        )


        for recommendation in ai_recommendations:

            if recommendation not in general_recommendations:

                general_recommendations.append(
                    recommendation
                )


        # =========================================
        # ADD AI DATA TO RESULT
        # =========================================

        result["score"] = final_score

        result["rule_score"] = rule_score

        result["ai_quality"] = ai_quality

        result["summary_quality"] = (
            summary_quality
        )

        result["experience_quality"] = (
            experience_quality
        )

        result["project_quality"] = (
            project_quality
        )

        result["skills_quality"] = (
            skills_quality
        )

        result["clarity_quality"] = (
            clarity_quality
        )

        result["ai_strengths"] = (
            ai_strengths
        )

        result["ai_weaknesses"] = (
            ai_weaknesses
        )

        result["ai_recommendations"] = (
            ai_recommendations
        )

        result["recommendations"] = (
            general_recommendations
        )


        # =========================================
        # DATABASE CONNECTION
        # =========================================

        connection = get_db_connection()

        cursor = connection.cursor()


        try:

            # =====================================
            # SAVE RESUME
            # =====================================

            resume_query = """
                INSERT INTO resumes
                (
                    user_id,
                    file_name,
                    file_path
                )
                VALUES (%s, %s, %s)
            """


            cursor.execute(
                resume_query,
                (
                    session["user_id"],
                    filename,
                    filepath
                )
            )


            resume_id = cursor.lastrowid


            # =====================================
            # SAVE GENERAL RESULT
            # =====================================

            general_query = """
                INSERT INTO general_results
                (
                    resume_id,
                    score,
                    email_detected,
                    phone_detected,
                    word_count,
                    skills,
                    sections,
                    recommendations,
                    linkedin_detected,
                    github_detected,

                    ai_quality,
                    summary_quality,
                    experience_quality,
                    project_quality,
                    skills_quality,
                    clarity_quality,

                    ai_strengths,
                    ai_weaknesses,
                    ai_recommendations
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,

                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,

                    %s,
                    %s,
                    %s
                )
            """


            cursor.execute(
                general_query,
                (
                    resume_id,

                    final_score,

                    result["email"],

                    result["phone"],

                    result["word_count"],

                    json.dumps(
                        result["skills"]
                    ),

                    json.dumps(
                        result["sections"]
                    ),

                    json.dumps(
                        general_recommendations
                    ),

                    result["linkedin"],

                    result["github"],


                    ai_quality,

                    summary_quality,

                    experience_quality,

                    project_quality,

                    skills_quality,

                    clarity_quality,


                    json.dumps(
                        ai_strengths
                    ),

                    json.dumps(
                        ai_weaknesses
                    ),

                    json.dumps(
                        ai_recommendations
                    )
                )
            )


            # =====================================
            # COMMIT
            # =====================================

            connection.commit()


        except Exception as e:

            connection.rollback()

            print(
                "Database Error:",
                e
            )

            flash(
                "Analysis finished, but it could not be "
                "saved to your history.",
                "warning"
            )


        finally:

            cursor.close()

            connection.close()


        # =========================================
        # SHOW RESULT PAGE
        # =========================================

        return render_template(
            "general_result.html",
            result=result,
            filename=filename
        )


    # =========================================
    # GET REQUEST
    # =========================================

    return render_template(
        "general_analyzer.html"
    )