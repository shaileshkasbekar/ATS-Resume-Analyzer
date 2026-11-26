"""
The five specialist agents.

Each agent is the same loop (agents/llm.py) with a different:
- role and instructions (system prompt)
- set of tools it is allowed to use
- fallback tool order, used only when the AI is unavailable

Giving each agent only the tools it needs keeps its choices focused and
makes the trace easy to follow.
"""

COMMON_RULES = """
Rules:
- Use tools to get facts. Never guess scores, skills or matches; they come only from tool results.
- Report ONLY what the tool results show. Do not add general advice or name technologies, tools or
  skills that do not appear in the tool results (no "employers also want X").
- Never claim the candidate has a skill or experience that the tool results do not show.
- If a tool returns an error, read it and fix your next step (for example, run a job match first).
- Stop calling tools as soon as you have what you need.
- Final answer: plain text, short (max 120 words), with "- " bullets. No markdown: no **, no #, no tables.
"""


SPECIALISTS = {

    "resume_analysis": {
        "title": "Resume Analysis Agent",
        "icon": "fa-file-lines",
        "purpose": "Reads the resume: skills, experience, qualifications, and evaluates the profile.",
        "tools": ["get_resume_profile", "check_resume_quality", "recall_user_memory"],
        "prompt": """You are the Resume Analysis Agent of an ATS resume tool for students.
Your job: understand the candidate's profile - skills (and whether they are proven in projects/work
or only listed), experience level, qualifications - and evaluate its strengths and weaknesses.
Use get_resume_profile first. Use check_resume_quality when the goal is about resume quality or
the overall profile.
Your answer describes only the candidate's profile (skills proven vs only listed, level,
qualifications, quality issues). Do not judge the fit for a specific job and do not list missing job skills: the Job Matching and
Skill Gap agents do that with the real job requirements.""",
    },

    "job_matching": {
        "title": "Job Matching Agent",
        "icon": "fa-handshake",
        "purpose": "Compares the resume with the job description or role and calculates the match score.",
        "tools": ["extract_job_requirements", "match_resume_to_job", "match_resume_to_role",
                  "suggest_best_role", "list_job_roles", "recall_user_memory", "get_past_analyses",
                  "save_user_memory"],
        "prompt": """You are the Job Matching Agent.
Your job: compare the resume with the target job and report the job-specific match score, the
matched requirements and the missing ones.
Decide the target like this:
1. If a job description was given, call match_resume_to_job.
2. Otherwise, if the user's goal or memory names a role, call match_resume_to_role with it
   (call list_job_roles if you are unsure of the exact name).
3. Otherwise call suggest_best_role, then match_resume_to_role with the best role.
If the goal states preferences (location, remote work, company type), save them with
save_user_memory (key preferences). The target role is saved automatically.""",
    },

    "skill_gap": {
        "title": "Skill Gap Analysis Agent",
        "icon": "fa-chart-simple",
        "purpose": "Finds the important missing skills, prioritises them and recommends learning resources.",
        "tools": ["prioritize_skill_gaps", "get_learning_resources", "match_resume_to_job",
                  "match_resume_to_role", "suggest_best_role"],
        "prompt": """You are the Skill Gap Analysis Agent.
Your job: find which important skills the candidate is missing for the target job, rank them
(required before preferred; missing before only-listed) and recommend learning resources.
Call prioritize_skill_gaps. If it says there is no job match yet, run the match first.
Then call get_learning_resources with the top skills (most important first).""",
    },

    "resume_improvement": {
        "title": "Resume Improvement Agent",
        "icon": "fa-wand-magic-sparkles",
        "purpose": "Suggests better resume content, improves weak project descriptions and recommends ATS keywords.",
        "tools": ["suggest_resume_improvements", "recommend_ats_keywords", "get_resume_profile",
                  "match_resume_to_job", "match_resume_to_role", "suggest_best_role"],
        "prompt": """You are the Resume Improvement Agent.
Your job: improve the resume content for the target job - better summary, stronger project and
experience bullets, and the right ATS keywords - without inventing anything.
Call suggest_resume_improvements and recommend_ats_keywords (run a job match first if a tool says so).
In your answer, point out the most useful 2-3 rewrites and keywords. Remind the user to add a keyword
only if it is true.""",
    },

    "career_roadmap": {
        "title": "Career Roadmap Agent",
        "icon": "fa-route",
        "purpose": "Builds a personalised learning roadmap, project ideas and next career steps.",
        "tools": ["build_learning_roadmap", "recommend_projects", "prioritize_skill_gaps",
                  "recall_user_memory", "match_resume_to_job",
                  "match_resume_to_role", "suggest_best_role"],
        "prompt": """You are the Career Roadmap Agent.
Your job: turn the skill gaps into a personalised plan - an ordered learning roadmap, portfolio
projects that prove the missing skills, and concrete next career steps.
Call build_learning_roadmap and recommend_projects (run a job match first if a tool says so).""",
    },
}

ORDER = ["resume_analysis", "job_matching", "skill_gap", "resume_improvement", "career_roadmap"]

# Agents that need a job match. The planner puts job_matching before them.
NEEDS_MATCH = {"skill_gap", "resume_improvement", "career_roadmap"}


for _spec in SPECIALISTS.values():
    _spec["prompt"] = _spec["prompt"].strip() + "\n" + COMMON_RULES


def fallback_plan(agent, ctx, remembered):
    """
    Tool order used when the AI is unavailable: [(tool, arguments), ...].
    """

    if agent == "resume_analysis":
        return [("get_resume_profile", {}), ("check_resume_quality", {})]

    if agent == "job_matching":
        if ctx.jd_text.strip():
            return [("match_resume_to_job", {})]
        if remembered.get("target_role"):
            return [("match_resume_to_role", {"role_name": remembered["target_role"]})]
        return [("suggest_best_role", {})]

    if agent == "skill_gap":
        return [("prioritize_skill_gaps", {})]

    if agent == "resume_improvement":
        return [("suggest_resume_improvements", {}), ("recommend_ats_keywords", {})]

    if agent == "career_roadmap":
        return [("build_learning_roadmap", {}), ("recommend_projects", {})]

    return []
