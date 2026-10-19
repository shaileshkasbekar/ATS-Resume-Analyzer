from resume_parser.ai_client import ask_ai_for_json


# =========================================
# General AI Resume Analysis
# =========================================

def analyze_general_resume_with_ai(resume_text):

    prompt = f"""
You are an expert professional resume reviewer.

Analyze the following resume as a GENERAL resume.

This is NOT a job-specific ATS analysis.

Do not judge the resume against a particular job role.

Evaluate the overall quality of the resume.

RESUME:

{resume_text}


Evaluate:

1. Professional summary quality
2. Experience quality
3. Project quality
4. Use of action verbs
5. Quantifiable achievements
6. Clarity and readability
7. Professional presentation based on the text
8. Technical skills presentation
9. Overall resume quality
10. Important improvements


IMPORTANT:

Do not invent experience or skills.

Do not assume the candidate has experience
that is not explicitly demonstrated.

Base the analysis only on the resume.


Return ONLY valid JSON.

Use exactly this structure:

{{
    "overall_quality": 0,
    "summary_quality": 0,
    "experience_quality": 0,
    "project_quality": 0,
    "skills_quality": 0,
    "clarity_quality": 0,
    "strengths": [],
    "weaknesses": [],
    "recommendations": []
}}


All scores must be integers from 0 to 100.
"""


    # Returns None when the AI is unavailable or fails

    return ask_ai_for_json(
        "You are a professional resume review system. Return only valid JSON.",
        prompt
    )
