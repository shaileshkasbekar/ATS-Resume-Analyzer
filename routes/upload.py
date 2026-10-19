from flask import Blueprint, render_template, request, session, redirect, flash
from werkzeug.utils import secure_filename

import os
import json
import uuid

from config import Config
from models.database import get_db_connection, table_columns

from resume_parser.pdf_reader import extract_text_from_pdf
from resume_parser.skill_extractor import extract_skills, find_skill_evidence
from resume_parser.ats_score import calculate_ats_score
from resume_parser.ai_analyzer import analyze_resume_with_ai
from resume_parser.ai_client import get_score
from resume_parser.recommendation import build_learning_plan


# =========================================
# Blueprint
# =========================================

upload = Blueprint("upload", __name__)


# =========================================
# Upload Resume
# =========================================

@upload.route("/upload", methods=["GET", "POST"])
def upload_resume():

    # -----------------------------------------
    # Check Login
    # -----------------------------------------

    if "user_id" not in session:

        return redirect("/login")


    # =========================================
    # POST REQUEST
    # =========================================

    if request.method == "POST":

        # -----------------------------------------
        # Get selected role
        # -----------------------------------------

        role_id = request.form.get("role_id")


        if not role_id:

            flash("Please select a job role.", "danger")

            return redirect("/upload")


        # -----------------------------------------
        # Get uploaded resume
        # -----------------------------------------

        resume = request.files.get("resume")


        if not resume or resume.filename == "":

            flash("Please select a resume.", "danger")

            return redirect("/upload")


        # -----------------------------------------
        # Validate PDF
        # -----------------------------------------

        if not resume.filename.lower().endswith(".pdf"):

            flash("Only PDF files are allowed.", "danger")

            return redirect("/upload")


        # -----------------------------------------
        # Secure filename
        # -----------------------------------------

        filename = secure_filename(
            resume.filename
        ) or "resume.pdf"


        # -----------------------------------------
        # Create filepath
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

            return redirect("/upload")


        # =========================================
        # GET ROLE + GROUPS + SKILLS
        # =========================================

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        query = """
        SELECT
            jr.role_id,
            jr.role_name,
            rsg.group_id,
            rsg.group_name,
            rsg.group_type,
            jrs.skill_name,
            jrs.importance,
            jrs.weight

        FROM job_roles jr

        JOIN role_skill_groups rsg
            ON jr.role_id = rsg.role_id

        JOIN job_role_skills jrs
            ON rsg.group_id = jrs.group_id

        WHERE jr.role_id = %s

        ORDER BY
            rsg.group_id,
            jrs.id
        """


        cursor.execute(
            query,
            (role_id,)
        )


        role_skill_groups = cursor.fetchall()


        cursor.close()
        connection.close()


        # -----------------------------------------
        # Check role configuration
        # -----------------------------------------

        if not role_skill_groups:

            os.remove(filepath)

            flash(
                "No skills are configured for this job role yet.",
                "danger"
            )

            return redirect("/upload")


        # =========================================
        # EXTRACT RESUME SKILLS
        # =========================================

        # The role's own skills are passed in, so every
        # skill stored in the database can be detected

        skills = extract_skills(
            text,
            [
                skill_data["skill_name"]
                for skill_data in role_skill_groups
            ]
        )


        # Normalize skills

        skills = [
            skill.strip().lower()
            for skill in skills
        ]


        print("\n==============================")
        print("RESUME SKILLS")
        print("==============================")


        for skill in skills:

            print(skill)


        # -----------------------------------------
        # Get role name
        # -----------------------------------------

        role_name = role_skill_groups[0][
            "role_name"
        ]


        print("\n==============================")
        print("SELECTED ROLE")
        print("==============================")

        print(role_name)


        # =========================================
        # PRINT ROLE STRUCTURE
        # =========================================

        print("\n==============================")
        print("ROLE SKILL STRUCTURE")
        print("==============================")


        for skill_data in role_skill_groups:

            print(
                skill_data["group_name"],
                "→",
                skill_data["skill_name"],
                "→",
                skill_data["importance"],
                "→",
                skill_data["weight"]
            )


        # =========================================
        # SKILL EVIDENCE
        # =========================================

        # "used" = appears in projects / experience,
        # "listed" = only in the skills list

        skill_evidence = find_skill_evidence(
            text,
            skills
        )


        # =========================================
        # RULE-BASED ATS ENGINE
        # =========================================

        (
            rule_score,
            matched_skills,
            missing_skills,
            recommended_skills,
            group_results,
            detected_path
        ) = calculate_ats_score(
            skills,
            role_skill_groups,
            skill_evidence
        )


        rule_score = round(
            rule_score,
            2
        )


        print("\n==============================")
        print("RULE-BASED RESULT")
        print("==============================")


        print(
            "Rule Score:",
            rule_score
        )


        print(
            "Detected Path:",
            detected_path
        )


        # =========================================
        # AI ANALYSIS
        # =========================================

        print("\n==============================")
        print("RUNNING AI ANALYSIS")
        print("==============================")


        ai_result = analyze_resume_with_ai(
            text,
            role_name,
            role_skill_groups
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


        # =========================================
        # GET AI RESULTS
        # =========================================

        technology_path = (
            ai_result.get("technology_path")
            or detected_path
            or ""
        )


        ai_relevance = get_score(
            ai_result,
            "overall_relevance"
        )


        experience_relevance = get_score(
            ai_result,
            "experience_relevance"
        )


        project_relevance = get_score(
            ai_result,
            "project_relevance"
        )


        semantic_matches = ai_result.get(
            "semantic_matches",
            []
        )


        strengths = ai_result.get(
            "strengths",
            []
        )


        weaknesses = ai_result.get(
            "weaknesses",
            []
        )


        ai_recommendations = ai_result.get(
            "recommendations",
            []
        )


        ai_matched_skills = ai_result.get(
            "matched_skills",
            []
        )


        ai_missing_skills = ai_result.get(
            "missing_important_skills",
            []
        )


        # =========================================
        # COMBINE RULE + AI MATCHES
        # =========================================

        # Start with rule-based matches

        final_matched_skills = list(
            matched_skills
        )


        # Add AI detected skills

        for skill in ai_matched_skills:

            if skill not in final_matched_skills:

                final_matched_skills.append(
                    skill
                )


        # Add semantic matches to matched skills
        # only when they are not already present

        for match in semantic_matches:

            if match not in final_matched_skills:

                final_matched_skills.append(
                    match
                )


        # =========================================
        # DETERMINE FINAL MISSING SKILLS
        # =========================================

        final_missing_skills = list(
            missing_skills
        )


        # AI missing skills should supplement
        # the rule-based missing skills.

        for skill in ai_missing_skills:

            if skill not in final_missing_skills:

                final_missing_skills.append(
                    skill
                )


        # =========================================
        # REMOVE ALTERNATIVE TECHNOLOGY SKILLS
        # =========================================

        # Only common skills and detected-path
        # skills should be considered important.

        allowed_missing_skills = set()


        for skill_data in role_skill_groups:

            group_name = skill_data[
                "group_name"
            ]

            group_type = skill_data[
                "group_type"
            ]


            # Common requirements

            if group_type == "common":

                allowed_missing_skills.add(
                    skill_data[
                        "skill_name"
                    ].strip().lower()
                )


            # Detected technology path

            elif (
                group_type == "technology"
                and (
                    group_name.lower()
                    ==
                    technology_path.lower()
                )
            ):

                allowed_missing_skills.add(
                    skill_data[
                        "skill_name"
                    ].strip().lower()
                )


        # -----------------------------------------
        # Filter missing skills
        # -----------------------------------------

        filtered_missing_skills = []


        for skill in final_missing_skills:

            if (
                skill.strip().lower()
                in allowed_missing_skills
            ):

                if skill not in filtered_missing_skills:

                    filtered_missing_skills.append(
                        skill
                    )


        final_missing_skills = (
            filtered_missing_skills
        )


        # =========================================
        # CREATE RECOMMENDATIONS
        # =========================================

        final_recommendations = []


        # Rule-based recommendations

        for recommendation in recommended_skills:

            if recommendation not in final_recommendations:

                final_recommendations.append(
                    recommendation
                )


        # AI recommendations

        for recommendation in ai_recommendations:

            if recommendation not in final_recommendations:

                final_recommendations.append(
                    recommendation
                )


        # =========================================
        # CALCULATE HYBRID ATS SCORE
        # =========================================

        """
        Final ATS Score:

        Rule-based skill matching      40%
        AI semantic relevance          25%
        Experience relevance           15%
        Project relevance              10%
        Technology path confidence      10%

        Total = 100%
        """


        # Technology path confidence: how strongly the
        # resume matches its detected technology path.
        # Roles without technology paths use the rule score.

        has_technology_groups = any(
            group["group_type"] == "technology"
            for group in group_results.values()
        )

        if detected_path:

            technology_path_score = group_results[
                detected_path
            ]["path_strength"]

        elif has_technology_groups:

            technology_path_score = 0

        else:

            technology_path_score = rule_score


        # -----------------------------------------
        # Hybrid score
        # -----------------------------------------

        final_score = (

            (rule_score * 0.40)

            +

            (ai_relevance * 0.25)

            +

            (experience_relevance * 0.15)

            +

            (project_relevance * 0.10)

            +

            (technology_path_score * 0.10)

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
        # PRINT FINAL RESULT
        # =========================================

        print("\n==============================")
        print("FINAL HYBRID ATS RESULT")
        print("==============================")


        print(
            "Final ATS Score:",
            final_score
        )


        print(
            "Rule Score:",
            rule_score
        )


        print(
            "AI Relevance:",
            ai_relevance
        )


        print(
            "Experience:",
            experience_relevance
        )


        print(
            "Projects:",
            project_relevance
        )


        print(
            "Technology Path:",
            technology_path
        )


        print(
            "\nMatched Skills:"
        )


        for skill in final_matched_skills:

            print(
                "✓",
                skill
            )


        print(
            "\nMissing Skills:"
        )


        for skill in final_missing_skills:

            print(
                "•",
                skill
            )


        print(
            "\nAI Recommendations:"
        )


        for recommendation in final_recommendations:

            print(
                "→",
                recommendation
            )


        # =========================================
        # CONVERT DATA FOR DATABASE
        # =========================================

        matched_skills_text = ", ".join(
            final_matched_skills
        )


        missing_skills_text = ", ".join(
            final_missing_skills
        )


        # Saved as JSON because recommendations
        # can contain commas

        recommended_skills_text = json.dumps(
            final_recommendations
        )


        semantic_matches_text = json.dumps(
            semantic_matches
        )


        strengths_text = json.dumps(
            strengths
        )


        weaknesses_text = json.dumps(
            weaknesses
        )


        ai_recommendations_text = json.dumps(
            ai_recommendations
        )


        # =========================================
        # SAVE TO DATABASE
        # =========================================

        user_id = session[
            "user_id"
        ]


        connection = get_db_connection()

        cursor = connection.cursor()


        try:

            # -----------------------------------------
            # Save Resume
            # -----------------------------------------

            resume_query = """
            INSERT INTO resumes
            (
                user_id,
                file_name,
                file_path
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """


            cursor.execute(
                resume_query,
                (
                    user_id,
                    filename,
                    filepath
                )
            )


            resume_id = cursor.lastrowid


            # -----------------------------------------
            # Save Hybrid ATS Result
            # -----------------------------------------

            result_data = {
                "resume_id": resume_id,
                "role_id": role_id,
                "ats_score": final_score,
                "matched_skills": matched_skills_text,
                "missing_skills": missing_skills_text,
                "recommended_skills": recommended_skills_text,
                "technology_path": technology_path,
                "ai_relevance": ai_relevance,
                "experience_relevance": experience_relevance,
                "project_relevance": project_relevance,
                "semantic_matches": semantic_matches_text,
                "strengths": strengths_text,
                "weaknesses": weaknesses_text,
                "ai_recommendations": ai_recommendations_text
            }


            # Saved only after the database upgrade
            # adds the skill_evidence column

            if "skill_evidence" in table_columns(cursor, "resume_results"):

                result_data["skill_evidence"] = json.dumps(
                    skill_evidence
                )


            result_query = (
                "INSERT INTO resume_results ("
                + ", ".join(result_data)
                + ") VALUES ("
                + ", ".join(["%s"] * len(result_data))
                + ")"
            )


            cursor.execute(
                result_query,
                tuple(result_data.values())
            )


            # -----------------------------------------
            # Commit
            # -----------------------------------------

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
        # SHOW RESULT
        # =========================================

        return render_template(
            "result.html",

            ats_score=final_score,

            matched_skills=final_matched_skills,

            missing_skills=final_missing_skills,

            recommended_skills=final_recommendations,

            detected_path=technology_path,

            group_results=group_results,

            ai_relevance=ai_relevance,

            experience_relevance=experience_relevance,

            project_relevance=project_relevance,

            semantic_matches=semantic_matches,

            strengths=strengths,

            weaknesses=weaknesses,

            ai_recommendations=ai_recommendations,

            filename=filename,

            skill_evidence=skill_evidence,

            learning_plan=build_learning_plan(
                final_missing_skills,
                role_skill_groups
            )
        )


    # =========================================
    # GET REQUEST
    # =========================================

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True
    )


    query = """
    SELECT
        role_id,
        role_name

    FROM job_roles

    ORDER BY role_name
    """


    cursor.execute(query)


    job_roles = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "upload.html",
        job_roles=job_roles
    )