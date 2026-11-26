"""
Long-term career memory.

Agents forget everything between runs unless we store it. This module keeps
a small set of facts per user in the agent_memory table, for example:

    target_role   "Junior Backend Developer"
    career_goal   "Get a backend job at a startup"
    known_skills  "Python, Flask, MySQL, Docker"
    skill_gaps    "Linux, AWS"
    last_score    "81 (Junior Backend Developer)"

At the start of a run the facts are loaded and given to the planner and the
agents ("recall"). Agents may also save facts with the save_user_memory tool,
and the workflow saves the main results at the end ("remember").

Only the keys below can be stored, and values are short, so the LLM cannot
fill the memory with anything else.
"""

from models.repository import _execute, _query, has_table


ALLOWED_KEYS = {
    "target_role": "The job role the user is aiming for",
    "career_goal": "The user's career goal in their own words",
    "known_skills": "Skills the resume clearly shows",
    "skill_gaps": "Important skills the user is missing",
    "experience_level": "fresher, junior or experienced",
    "last_score": "The latest job match score and job",
    "learning_focus": "What the user decided to learn next",
    "preferences": "Preferences such as location, company type or remote work",
}

MAX_VALUE_CHARS = 400


def ready():

    try:
        return has_table("agent_memory")
    except Exception:
        return False


def recall(user_id):
    """
    All remembered facts for the user as {key: value}. Empty if none.
    """

    if not ready():
        return {}

    rows = _query(
        "SELECT mem_key, mem_value FROM agent_memory WHERE user_id = %s ORDER BY mem_key",
        (user_id,)
    )

    return {row["mem_key"]: row["mem_value"] for row in rows}


def remember(user_id, key, value, source="agent"):
    """
    Saves one fact. Returns (ok, message).
    """

    key = (key or "").strip().lower()
    value = " ".join(str(value or "").split())[:MAX_VALUE_CHARS]

    if key not in ALLOWED_KEYS:
        return False, f"Unknown memory key '{key}'. Allowed: {', '.join(ALLOWED_KEYS)}"

    if not value:
        return False, "Empty value; nothing saved."

    if not ready():
        return False, "Memory table not available (run database upgrade v7)."

    _execute(
        """INSERT INTO agent_memory (user_id, mem_key, mem_value, source)
           VALUES (%s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE mem_value = VALUES(mem_value), source = VALUES(source)""",
        (user_id, key, value, source[:50])
    )

    return True, f"Saved {key}."


def forget(user_id, key=None):

    if not ready():
        return

    if key:
        _execute("DELETE FROM agent_memory WHERE user_id = %s AND mem_key = %s", (user_id, key))
    else:
        _execute("DELETE FROM agent_memory WHERE user_id = %s", (user_id,))


def as_text(facts):
    """
    Memory formatted for a prompt.
    """

    if not facts:
        return "(nothing remembered yet)"

    return "\n".join(f"- {key}: {value}" for key, value in facts.items())
