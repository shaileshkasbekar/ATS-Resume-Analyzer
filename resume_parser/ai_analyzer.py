from resume_parser.ai_client import ask_ai_for_json, as_untrusted


# -----------------------------------------
# AI Resume Analysis
# -----------------------------------------

def analyze_resume_with_ai(
    resume_text,
    role_name,
    role_skill_groups
):

    # -----------------------------------------
    # Separate common and technology groups
    # -----------------------------------------

    common_requirements = []

    technology_paths = {}


    for skill_data in role_skill_groups:

        group_name = skill_data["group_name"]

        group_type = skill_data["group_type"]

        skill_name = skill_data["skill_name"]

        importance = skill_data["importance"]

        weight = skill_data["weight"]


        # -----------------------------------------
        # Common requirements
        # -----------------------------------------

        if group_type == "common":

            common_requirements.append(
                {
                    "skill": skill_name,
                    "importance": importance,
                    "weight": weight
                }
            )


        # -----------------------------------------
        # Technology paths
        # -----------------------------------------

        elif group_type == "technology":

            if group_name not in technology_paths:

                technology_paths[group_name] = []


            technology_paths[group_name].append(
                {
                    "skill": skill_name,
                    "importance": importance,
                    "weight": weight
                }
            )


    # -----------------------------------------
    # Convert common requirements to text
    # -----------------------------------------

    common_text = ""


    for item in common_requirements:

        common_text += (
            f"- {item['skill']} "
            f"({item['importance']}, "
            f"weight {item['weight']})\n"
        )


    # -----------------------------------------
    # Convert technology paths to text
    # -----------------------------------------

    technology_text = ""


    for path_name, skills in technology_paths.items():

        technology_text += f"\n{path_name}:\n"


        for skill in skills:

            technology_text += (
                f"- {skill['skill']} "
                f"({skill['importance']}, "
                f"weight {skill['weight']})\n"
            )


    # -----------------------------------------
    # AI Prompt
    # -----------------------------------------

    prompt = f"""
You are an expert ATS resume analyzer.

Analyze the candidate's resume for the selected job role.

JOB ROLE:
{role_name}


COMMON REQUIREMENTS:

{common_text}


AVAILABLE TECHNOLOGY PATHS:

{technology_text}


RESUME:

{as_untrusted("resume", resume_text)}


IMPORTANT SCORING RULES:

1. Common requirements apply to the overall role.

2. Technology paths are ALTERNATIVES.

3. Do NOT treat every technology path as mandatory.

4. If a candidate follows Java Backend, do NOT penalize
   them for not knowing Python Backend, Node.js Backend,
   or .NET Backend.

5. If a candidate follows Node.js Backend, do NOT penalize
   them for not knowing Java or Python.

6. Identify the strongest technology path based on evidence
   in the resume.

7. Consider exact skill matches.

8. Consider semantic equivalents.

9. Consider skills demonstrated through work experience.

10. Consider skills demonstrated through projects.

11. Do not consider a technology "missing" merely because
    it belongs to another alternative technology path.

12. Missing important skills should only come from:
    - common requirements
    - the detected technology path

13. A skill mentioned in a project or experience description
    should count as evidence even if it is not inside a
    dedicated Skills section.

14. Do not reward a skill merely because it is listed if
    the resume provides contradictory evidence.

15. Evaluate the actual candidate profile rather than
    simply counting keywords.


EXAMPLE:

If the candidate has:

Java
Spring Boot
REST API
MySQL
Git

and the available paths are:

Python Backend
Node.js Backend
Java Backend
.NET Backend

the candidate should be evaluated primarily as:

Java Backend

They should NOT receive missing-skill penalties for:

Python
Node.js
C#
.NET


Return ONLY valid JSON.

Use exactly this structure:

{{
    "technology_path": "",
    "overall_relevance": 0,
    "matched_skills": [],
    "semantic_matches": [],
    "missing_important_skills": [],
    "experience_relevance": 0,
    "project_relevance": 0,
    "strengths": [],
    "weaknesses": [],
    "recommendations": []
}}

Rules for scores:

- overall_relevance: integer from 0 to 100
- experience_relevance: integer from 0 to 100
- project_relevance: integer from 0 to 100

Do not include markdown.
Do not include explanations outside the JSON.
"""


    # Returns None when the AI is unavailable or fails

    return ask_ai_for_json(
        "You are a professional ATS resume analysis system. Return only valid JSON.",
        prompt
    )
