"""
Job Match Score settings.

Change the numbers here to tune the score. When the formula
changes, bump SCORING_VERSION so saved results stay
interpretable (each saved result stores the version it used).
"""

SCORING_VERSION = "jm-2.0"


# Component weights. Components that do not apply to a job
# (e.g. no degree or certification asked for) are left out and
# the remaining weights are scaled up to 100.

COMPONENT_WEIGHTS = {
    "required_skills": 40,
    "preferred_skills": 10,
    "semantic_relevance": 15,
    "experience": 15,
    "projects": 10,
    "qualifications": 10,
}

COMPONENT_LABELS = {
    "required_skills": "Required skills",
    "preferred_skills": "Preferred skills",
    "semantic_relevance": "Overall relevance (AI)",
    "experience": "Relevant experience",
    "projects": "Project relevance",
    "qualifications": "Qualifications",
}


# How a requirement was matched

MATCH_TYPE_CREDIT = {
    "exact": 1.0,       # same name in the resume
    "alias": 1.0,       # other name: JS -> JavaScript
    "semantic": 0.6,    # AI found equivalent evidence (quote verified)
}


# Where the evidence was found

EVIDENCE_CREDIT = {
    "experience": 1.0,  # used in work experience / internship
    "project": 1.0,     # used in a project
    "listed": 0.7,      # only in the skills list
    "mentioned": 0.6,   # only mentioned elsewhere (e.g. summary)
    "unknown": 0.85,    # resume sections could not be detected
}

EVIDENCE_LABELS = {
    "experience": "Work experience",
    "project": "Project",
    "listed": "Skills list only",
    "mentioned": "Mentioned only",
    "unknown": "Found (section unknown)",
}

MATCH_TYPE_LABELS = {
    "exact": "Exact match",
    "alias": "Alias match",
    "semantic": "Semantic match",
    "missing": "Missing",
}


# Education levels used to check degree requirements

EDUCATION_LEVELS = {
    "diploma": 0,
    "bachelor": 1,
    "master": 2,
    "phd": 3,
}
