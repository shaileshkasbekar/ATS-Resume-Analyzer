import re

from resume_parser.skill_extractor import extract_skills
from resume_parser.sections import SECTIONS, is_heading


# --------------------------------
# Strong action verbs for bullets
# --------------------------------

ACTION_VERBS = {
    "achieved", "analyzed", "architected", "automated", "built",
    "collaborated", "configured", "created", "debugged", "delivered",
    "deployed", "designed", "developed", "engineered", "enhanced",
    "established", "implemented", "improved", "increased", "integrated",
    "launched", "led", "maintained", "managed", "migrated",
    "optimized", "organized", "published", "redesigned", "reduced",
    "refactored", "researched", "resolved", "scaled", "secured",
    "simplified", "streamlined", "tested", "trained", "won",
    "wrote", "coordinated", "mentored", "boosted", "accelerated"
}


# --------------------------------
# Weak phrases that hide impact
# --------------------------------

WEAK_PHRASES = [
    "responsible for",
    "worked on",
    "helped with",
    "helped in",
    "involved in",
    "duties included",
    "tasked with",
    "participated in"
]


BULLET_CHARS = "•-*▪●◦–·>✓■□➢"


def _content_checks(lines, text_lower):
    """
    Checks the writing quality of the resume.
    """

    # Numbers that show impact: 40%, 10k users, 3x faster, 500+ ...

    quantified = re.findall(
        r"\b\d[\d,.]*\s*(%|\+|x\b|k\b|percent|users|customers|students|"
        r"members|clients|ms\b|seconds|hours|days|times|lakh|crore|million)",
        text_lower
    )

    # Action verbs at the start of a line / bullet

    verbs_used = set()

    for line in lines:

        words = line.strip().lstrip(BULLET_CHARS).strip().split()

        if words:

            first = re.sub(r"[^a-z]", "", words[0].lower())

            if first in ACTION_VERBS:
                verbs_used.add(first)

    weak_found = [
        phrase for phrase in WEAK_PHRASES
        if phrase in text_lower
    ]

    pronouns = len(re.findall(r"\b(i|me|my|myself)\b", text_lower))

    return {
        "quantified": len(quantified),
        "action_verbs": sorted(verbs_used),
        "weak_phrases": weak_found,
        "pronouns": pronouns
    }


def analyze_resume(text):

    result = {}

    text_lower = text.lower()

    lines = [line for line in text.splitlines() if line.strip()]


    # --------------------------------
    # Detect Skills
    # --------------------------------

    detected_skills = extract_skills(text)

    result["skills"] = detected_skills


    # --------------------------------
    # Contact Information
    # --------------------------------

    email_present = bool(
        re.search(
            r"[\w\.-]+@[\w\.-]+\.\w+",
            text
        )
    )

    # Any 10 to 13 digit number, allowing spaces,
    # dashes and brackets: +91 98765 43210, (987) 654-3210

    phone_present = any(
        10 <= len(re.sub(r"\D", "", match)) <= 13
        for match in re.findall(r"\+?\(?\d[\d\s\-()]{8,16}\d", text)
    )

    result["email"] = email_present
    result["phone"] = phone_present


    # --------------------------------
    # Resume Sections (by heading)
    # --------------------------------

    section_result = {}

    for section, keywords in SECTIONS.items():

        section_result[section] = any(
            is_heading(line, keywords)
            for line in lines
        )

    result["sections"] = section_result


    # --------------------------------
    # Word Count
    # --------------------------------

    word_count = len(text.split())

    result["word_count"] = word_count


    # --------------------------------
    # LinkedIn / GitHub
    # --------------------------------

    linkedin_present = bool(re.search(r"\blinkedin\b", text_lower))

    github_present = bool(re.search(r"\bgithub\b", text_lower))

    result["linkedin"] = linkedin_present
    result["github"] = github_present


    # --------------------------------
    # Writing quality
    # --------------------------------

    content = _content_checks(lines, text_lower)

    result["content"] = content


    # --------------------------------
    # Calculate General Resume Score
    # (maximum 100)
    # --------------------------------

    score = 0

    # Contact information: 15

    if email_present:
        score += 8

    if phone_present:
        score += 7

    # Main sections: 38

    if section_result["skills"]:
        score += 10

    if section_result["education"]:
        score += 8

    if section_result["experience"]:
        score += 8

    if section_result["projects"]:
        score += 8

    if section_result["summary"]:
        score += 4

    # Extra sections: 6

    if section_result["certifications"]:
        score += 3

    if section_result["achievements"]:
        score += 3

    # Technical skills: 8

    if len(detected_skills) >= 8:
        score += 8
    elif len(detected_skills) >= 5:
        score += 6
    elif len(detected_skills) >= 3:
        score += 3

    # Online profiles: 6

    if linkedin_present:
        score += 3

    if github_present:
        score += 3

    # Resume length: 7

    if 300 <= word_count <= 800:
        score += 7
    elif 200 <= word_count < 300 or 800 < word_count <= 1000:
        score += 4

    # Writing quality: 20

    if content["quantified"] >= 3:
        score += 8
    elif content["quantified"] >= 1:
        score += 4

    if len(content["action_verbs"]) >= 5:
        score += 6
    elif len(content["action_verbs"]) >= 2:
        score += 3

    if not content["weak_phrases"]:
        score += 3

    if content["pronouns"] <= 2:
        score += 3

    result["score"] = min(score, 100)


    # --------------------------------
    # Recommendations
    # --------------------------------

    recommendations = []

    if not email_present:
        recommendations.append("Add a professional email address.")

    if not phone_present:
        recommendations.append("Add a phone number.")

    if not section_result["summary"]:
        recommendations.append("Add a short professional summary or career objective.")

    if not section_result["skills"]:
        recommendations.append("Add a dedicated Technical Skills section.")

    if not section_result["education"]:
        recommendations.append("Add an Education section.")

    if not section_result["experience"]:
        recommendations.append("Add an Experience or Internship section.")

    if not section_result["projects"]:
        recommendations.append("Add a Projects section to demonstrate practical experience.")

    if not section_result["certifications"]:
        recommendations.append("Consider adding relevant certifications.")

    if not section_result["achievements"]:
        recommendations.append("Consider adding achievements, awards, or measurable accomplishments.")

    if len(detected_skills) < 5:
        recommendations.append("Add more relevant technical skills.")

    if not linkedin_present:
        recommendations.append("Add your LinkedIn profile.")

    if not github_present:
        recommendations.append("Add your GitHub profile if you have technical projects.")

    if word_count < 200:
        recommendations.append("Your resume is quite short. Add more relevant details.")
    elif word_count > 1000:
        recommendations.append("Your resume is lengthy. Consider removing unnecessary information.")

    if content["quantified"] < 3:
        recommendations.append(
            "Add numbers to show impact, e.g. \"Reduced page load time by 40%\" "
            "or \"Used by 500+ students\"."
        )

    if len(content["action_verbs"]) < 5:
        recommendations.append(
            "Start bullet points with strong action verbs like Developed, "
            "Built, Designed, Optimized or Led."
        )

    if content["weak_phrases"]:
        recommendations.append(
            "Replace weak phrases (" + ", ".join(f'"{p}"' for p in content["weak_phrases"])
            + ") with what you actually did and the result."
        )

    if content["pronouns"] > 2:
        recommendations.append(
            "Avoid personal pronouns like \"I\", \"me\" and \"my\" in your resume."
        )

    result["recommendations"] = recommendations

    return result
