from flask import Blueprint, render_template, request, session, redirect
from models.database import get_db_connection, table_columns
import json

from resume_parser.recommendation import build_learning_plan
from routes.job_match import render_job_match_result
from models import repository


history = Blueprint("history", __name__)


# =========================================
# HISTORY PAGE
# =========================================

PAGE_SIZE = 15

SORTS = {
    "date_desc": "upload_date DESC, analysis_id DESC",
    "date_asc": "upload_date ASC, analysis_id ASC",
    "score_desc": "score DESC, upload_date DESC",
    "score_asc": "score ASC, upload_date DESC",
}

TYPES = {
    "ats": "ATS Analysis",
    "general": "General Analysis",
    "jd": "Job Match",
}


def _history_union(cursor, user_id):
    """
    All analyses of the user as one query (ATS, general, job match).
    """

    query = """
    SELECT resumes.resume_id, resume_results.result_id AS analysis_id, resumes.file_name,
           job_roles.role_name, resume_results.ats_score AS score, resumes.upload_date,
           'ATS Analysis' AS analysis_type
    FROM resumes
    JOIN resume_results ON resumes.resume_id = resume_results.resume_id
    JOIN job_roles ON resume_results.role_id = job_roles.role_id
    WHERE resumes.user_id = %s

    UNION ALL

    SELECT resumes.resume_id, general_results.general_result_id AS analysis_id, resumes.file_name,
           'General Resume' AS role_name, general_results.score AS score, resumes.upload_date,
           'General Analysis' AS analysis_type
    FROM resumes
    JOIN general_results ON resumes.resume_id = general_results.resume_id
    WHERE resumes.user_id = %s
    """

    params = [user_id, user_id]

    # Job matches (only after the database upgrade)

    jd_columns = table_columns(cursor, "jd_results")

    if jd_columns:

        # "Job title · Company" when the company column exists (upgrade v4)

        job_label = (
            "NULLIF(CONCAT_WS(' · ', NULLIF(jd_results.job_title, ''), NULLIF(jd_results.company_name, '')), '')"
            if "company_name" in jd_columns else "NULLIF(jd_results.job_title, '')"
        )

        query += """
        UNION ALL

        SELECT resumes.resume_id, jd_results.jd_result_id AS analysis_id, resumes.file_name,
               COALESCE(""" + job_label + """, 'Job description') AS role_name,
               jd_results.score AS score, resumes.upload_date, 'Job Match' AS analysis_type
        FROM resumes
        JOIN jd_results ON resumes.resume_id = jd_results.resume_id
        WHERE resumes.user_id = %s
        """

        params.append(user_id)

    return query, params


@history.route("/history")
def view_history():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    # Filters from the query string (validated against fixed lists)

    search = request.args.get("q", "").strip()[:100]
    kind = request.args.get("type", "")
    role = request.args.get("role", "").strip()[:200]
    sort = request.args.get("sort", "date_desc")

    sort = sort if sort in SORTS else "date_desc"
    kind = kind if kind in TYPES else ""

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    union, params = _history_union(cursor, user_id)

    where = []
    filter_params = []

    if search:
        where.append("(file_name LIKE %s OR role_name LIKE %s)")
        filter_params += [f"%{search}%", f"%{search}%"]

    if kind:
        where.append("analysis_type = %s")
        filter_params.append(TYPES[kind])

    if role:
        where.append("role_name = %s")
        filter_params.append(role)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    cursor.execute(f"SELECT COUNT(*) AS n FROM ({union}) h{where_sql}", tuple(params + filter_params))

    total = cursor.fetchone()["n"]

    pages = max(1, -(-total // PAGE_SIZE))
    page = min(page, pages)

    cursor.execute(
        f"SELECT * FROM ({union}) h{where_sql} ORDER BY {SORTS[sort]} LIMIT %s OFFSET %s",
        tuple(params + filter_params + [PAGE_SIZE, (page - 1) * PAGE_SIZE])
    )

    history_data = cursor.fetchall()

    cursor.execute(f"SELECT DISTINCT role_name FROM ({union}) h ORDER BY role_name", tuple(params))

    roles = [r["role_name"] for r in cursor.fetchall() if r["role_name"]]

    cursor.close()
    connection.close()

    return render_template(
        "history.html",
        history_data=history_data,
        total=total,
        page=page,
        pages=pages,
        filters={"q": search, "type": kind, "role": role, "sort": sort},
        roles=roles,
        has_versions=repository.has_table("resume_versions")
    )


# =========================================
# VIEW GENERAL RESULT
# =========================================

@history.route("/history/general/<int:result_id>")
def view_general_result(result_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """

    SELECT
        general_results.*,
        resumes.file_name

    FROM general_results

    JOIN resumes
        ON general_results.resume_id = resumes.resume_id

    WHERE general_results.general_result_id = %s
    AND resumes.user_id = %s

    """

    cursor.execute(
        query,
        (
            result_id,
            session["user_id"]
        )
    )

    data = cursor.fetchone()

    cursor.close()
    connection.close()

    if not data:
        return "General analysis not found."


    # =========================================
    # CONVERT DATABASE DATA
    # =========================================

    result = {

        "score": data["score"],

        "email": data["email_detected"],

        "phone": data["phone_detected"],

        "word_count": data["word_count"],

        "skills": json.loads(
            data["skills"]
        )
        if data["skills"]
        else [],

        "sections": json.loads(
            data["sections"]
        )
        if data["sections"]
        else {},

        "recommendations": json.loads(
            data["recommendations"]
        )
        if data["recommendations"]
        else [],

        "linkedin": bool(
            data["linkedin_detected"]
        ),

        "github": bool(
            data["github_detected"]
        )
    }


    # =========================================
    # AI GENERAL ANALYSIS DATA
    # =========================================

    result["ai_quality"] = data.get(
        "ai_quality",
        0
    )

    result["summary_quality"] = data.get(
        "summary_quality",
        0
    )

    result["experience_quality"] = data.get(
        "experience_quality",
        0
    )

    result["project_quality"] = data.get(
        "project_quality",
        0
    )

    result["skills_quality"] = data.get(
        "skills_quality",
        0
    )

    result["clarity_quality"] = data.get(
        "clarity_quality",
        0
    )


    # =========================================
    # AI STRENGTHS
    # =========================================

    if data.get("ai_strengths"):

        try:

            result["ai_strengths"] = json.loads(
                data["ai_strengths"]
            )

        except Exception:

            result["ai_strengths"] = []

    else:

        result["ai_strengths"] = []


    # =========================================
    # AI WEAKNESSES
    # =========================================

    if data.get("ai_weaknesses"):

        try:

            result["ai_weaknesses"] = json.loads(
                data["ai_weaknesses"]
            )

        except Exception:

            result["ai_weaknesses"] = []

    else:

        result["ai_weaknesses"] = []


    # =========================================
    # AI RECOMMENDATIONS
    # =========================================

    if data.get("ai_recommendations"):

        try:

            result["ai_recommendations"] = json.loads(
                data["ai_recommendations"]
            )

        except Exception:

            result["ai_recommendations"] = []

    else:

        result["ai_recommendations"] = []



    # Saved by database upgrade v5 (older rows have none)



    try:


        result["issues"] = json.loads(data.get("issues") or "{}")


    except ValueError:


        result["issues"] = {}



    result["experience_level"] = data.get("experience_level") or ""



    return render_template(

        "general_result.html",

        report_url=f"/report/general/{result_id}.pdf",

        result=result,

        filename=data["file_name"]

    )


# =========================================
# VIEW ATS RESULT
# =========================================

@history.route("/history/ats/<int:result_id>")
def view_ats_result(result_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # =========================================
    # GET SAVED ATS RESULT
    # =========================================

    query = """

    SELECT
        resume_results.*,
        resumes.file_name,
        resumes.file_path,
        job_roles.role_name

    FROM resume_results

    JOIN resumes
        ON resume_results.resume_id = resumes.resume_id

    JOIN job_roles
        ON resume_results.role_id = job_roles.role_id

    WHERE resume_results.result_id = %s
    AND resumes.user_id = %s

    """

    cursor.execute(
        query,
        (
            result_id,
            session["user_id"]
        )
    )

    data = cursor.fetchone()


    if not data:

        cursor.close()
        connection.close()

        return "ATS analysis not found."


    # =========================================
    # GET ROLE SKILL GROUPS
    # =========================================

    role_query = """

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
        role_query,
        (data["role_id"],)
    )

    role_skill_groups = cursor.fetchall()


    cursor.close()
    connection.close()


    # =========================================
    # MATCHED SKILLS
    # =========================================

    matched_skills = []

    if data.get("matched_skills"):

        matched_skills = [

            skill.strip()

            for skill in
            data["matched_skills"].split(",")

            if skill.strip()

        ]


    # =========================================
    # MISSING SKILLS
    # =========================================

    missing_skills = []

    if data.get("missing_skills"):

        missing_skills = [

            skill.strip()

            for skill in
            data["missing_skills"].split(",")

            if skill.strip()

        ]


    # =========================================
    # RECOMMENDED SKILLS
    # =========================================

    recommended_skills = []

    if data.get("recommended_skills"):

        # New results are saved as JSON,
        # older ones as comma-separated text

        try:

            recommended_skills = json.loads(
                data["recommended_skills"]
            )

        except ValueError:

            recommended_skills = [
                skill.strip()
                for skill in
                data["recommended_skills"].split(",")
                if skill.strip()
            ]


    # =========================================
    # SKILL EVIDENCE (saved after the upgrade)
    # =========================================

    skill_evidence = {}

    if data.get("skill_evidence"):

        try:

            skill_evidence = json.loads(
                data["skill_evidence"]
            )

        except ValueError:

            skill_evidence = {}


    # =========================================
    # REBUILD GROUP RESULTS
    # =========================================

    from resume_parser.ats_score import calculate_ats_score


    # Use saved matched skills to rebuild
    # the group display.

    resume_skills = [

        skill.strip().lower()

        for skill in matched_skills

        if skill.strip()

    ]


    try:

        (

            rebuilt_score,

            rebuilt_matched,

            rebuilt_missing,

            rebuilt_recommended,

            group_results,

            rebuilt_path

        ) = calculate_ats_score(

            resume_skills,

            role_skill_groups,

            skill_evidence

        )


    except Exception as e:

        print(
            "History ATS reconstruction error:",
            e
        )

        group_results = {}


    # =========================================
    # SEMANTIC MATCHES
    # =========================================

    semantic_matches = []

    if data.get("semantic_matches"):

        try:

            semantic_matches = json.loads(
                data["semantic_matches"]
            )

        except Exception:

            semantic_matches = []


    # =========================================
    # STRENGTHS
    # =========================================

    strengths = []

    if data.get("strengths"):

        try:

            strengths = json.loads(
                data["strengths"]
            )

        except Exception:

            strengths = []


    # =========================================
    # WEAKNESSES
    # =========================================

    weaknesses = []

    if data.get("weaknesses"):

        try:

            weaknesses = json.loads(
                data["weaknesses"]
            )

        except Exception:

            weaknesses = []


    # =========================================
    # AI RECOMMENDATIONS
    # =========================================

    ai_recommendations = []

    if data.get("ai_recommendations"):

        try:

            ai_recommendations = json.loads(
                data["ai_recommendations"]
            )

        except Exception:

            ai_recommendations = []


    # =========================================
    # TECHNOLOGY PATH
    # =========================================

    detected_path = data.get(
        "technology_path"
    )


    # =========================================
    # AI SCORES
    # =========================================

    ai_relevance = data.get(
        "ai_relevance",
        0
    )

    experience_relevance = data.get(
        "experience_relevance",
        0
    )

    project_relevance = data.get(
        "project_relevance",
        0
    )


    # =========================================
    # RENDER ATS RESULT
    # =========================================

    return render_template(

        "result.html",

        report_url=f"/report/ats/{result_id}.pdf",

        ats_score=data["ats_score"],

        matched_skills=matched_skills,

        missing_skills=missing_skills,

        recommended_skills=recommended_skills,

        detected_path=detected_path,

        group_results=group_results,

        ai_relevance=ai_relevance,

        experience_relevance=experience_relevance,

        project_relevance=project_relevance,

        semantic_matches=semantic_matches,

        strengths=strengths,

        weaknesses=weaknesses,

        ai_recommendations=ai_recommendations,

        filename=data["file_name"],

        skill_evidence=skill_evidence,

        learning_plan=build_learning_plan(
            missing_skills,
            role_skill_groups
        )

    )


# =========================================
# DELETE GENERAL RESULT
# =========================================

@history.route(
    "/history/delete/general/<int:result_id>",
    methods=["POST"]
)
def delete_general_result(result_id):

    if "user_id" not in session:
        return redirect("/login")


    connection = get_db_connection()
    cursor = connection.cursor()


    query = """

        DELETE general_results

        FROM general_results

        JOIN resumes
            ON general_results.resume_id =
               resumes.resume_id

        WHERE general_results.general_result_id = %s

        AND resumes.user_id = %s

    """


    cursor.execute(
        query,
        (
            result_id,
            session["user_id"]
        )
    )


    connection.commit()

    cursor.close()
    connection.close()


    return redirect("/history")


# =========================================
# DELETE ATS RESULT
# =========================================

@history.route(
    "/history/delete/ats/<int:result_id>",
    methods=["POST"]
)
def delete_ats_result(result_id):

    if "user_id" not in session:
        return redirect("/login")


    connection = get_db_connection()
    cursor = connection.cursor()


    query = """

        DELETE resume_results

        FROM resume_results

        JOIN resumes
            ON resume_results.resume_id =
               resumes.resume_id

        WHERE resume_results.result_id = %s

        AND resumes.user_id = %s

    """


    cursor.execute(
        query,
        (
            result_id,
            session["user_id"]
        )
    )


    connection.commit()

    cursor.close()
    connection.close()


    return redirect("/history")

# =========================================
# VIEW JOB MATCH RESULT
# =========================================

@history.route("/history/jd/<int:result_id>")
def view_jd_result(result_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT jd_results.*, resumes.file_name
        FROM jd_results
        JOIN resumes
            ON jd_results.resume_id = resumes.resume_id
        WHERE jd_results.jd_result_id = %s
        AND resumes.user_id = %s
        """,
        (result_id, session["user_id"])
    )

    data = cursor.fetchone()

    cursor.close()
    connection.close()

    if not data:
        return redirect("/history")

    try:
        result = json.loads(data["details"] or "{}")
    except ValueError:
        result = {}

    # Column values win over the JSON copy

    result["job_title"] = data.get("job_title") or result.get("job_title", "")
    result["company"] = data.get("company_name") or result.get("company", "")

    resume_text = repository.resume_text_for(repository.get_jd_result(session["user_id"], result_id) or {})

    return render_job_match_result(result, data["file_name"], result_id,
                                   resume_text=resume_text, analyzed_at=data.get("created_at"))


# =========================================
# DELETE JOB MATCH RESULT
# =========================================

@history.route(
    "/history/delete/jd/<int:result_id>",
    methods=["POST"]
)
def delete_jd_result(result_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE jd_results
        FROM jd_results
        JOIN resumes
            ON jd_results.resume_id = resumes.resume_id
        WHERE jd_results.jd_result_id = %s
        AND resumes.user_id = %s
        """,
        (result_id, session["user_id"])
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/history")
