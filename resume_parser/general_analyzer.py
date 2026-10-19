import re

from resume_parser.skill_extractor import extract_skills


def analyze_resume(text):

    result = {}

    # --------------------------------
    # Convert text to lowercase
    # --------------------------------

    text_lower = text.lower()


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
            r'[\w\.-]+@[\w\.-]+\.\w+',
            text
        )
    )

    phone_present = bool(
        re.search(
            r'(\+91[\s-]?)?[6-9]\d{9}',
            text
        )
    )

    result["email"] = email_present
    result["phone"] = phone_present


    # --------------------------------
    # Resume Sections
    # --------------------------------

    sections = {

        "education": [
            "education",
            "academic qualification",
            "qualification",
            "academic background"
        ],

        "experience": [
            "experience",
            "work experience",
            "professional experience",
            "employment"
        ],

        "projects": [
            "projects",
            "project",
            "academic projects",
            "personal projects"
        ],

        "skills": [
            "skills",
            "technical skills",
            "skills & technologies",
            "technical skills & technologies"
        ],

        "summary": [
            "summary",
            "professional summary",
            "profile",
            "career objective",
            "objective"
        ],

        "certifications": [
            "certifications",
            "certification",
            "certificates"
        ],

        "achievements": [
            "achievements",
            "accomplishments",
            "awards"
        ]
    }


    section_result = {}


    for section, keywords in sections.items():

        found = False

        for keyword in keywords:

            if keyword in text_lower:
                found = True
                break

        section_result[section] = found


    result["sections"] = section_result


    # --------------------------------
    # Word Count
    # --------------------------------

    words = text.split()

    word_count = len(words)

    result["word_count"] = word_count


    # --------------------------------
    # LinkedIn / GitHub
    # --------------------------------

    linkedin_present = bool(
        re.search(
            r'\blinkedin\b',
            text_lower
        )
    )

    github_present = bool(
        re.search(
            r'\bgithub\b',
            text_lower
        )
    )

    result["linkedin"] = linkedin_present
    result["github"] = github_present


    # --------------------------------
    # Calculate General Resume Score
    # --------------------------------

    score = 0


    # Contact Information
    # Maximum: 20

    if email_present:
        score += 10

    if phone_present:
        score += 10


    # Important Resume Sections
    # Maximum: 45

    if section_result["summary"]:
        score += 5

    if section_result["skills"]:
        score += 10

    if section_result["education"]:
        score += 10

    if section_result["experience"]:
        score += 10

    if section_result["projects"]:
        score += 10


    # Additional Sections
    # Maximum: 10

    if section_result["certifications"]:
        score += 5

    if section_result["achievements"]:
        score += 5


    # Technical Skills
    # Maximum: 10

    if len(detected_skills) >= 5:

        score += 10

    elif len(detected_skills) >= 3:

        score += 5


    # Online Profiles
    # Maximum: 5

    if linkedin_present or github_present:

        score += 5


    # Resume Length
    # Maximum: 10

    if 300 <= word_count <= 800:

        score += 10

    elif 200 <= word_count < 300:

        score += 5

    elif 800 < word_count <= 1000:

        score += 5


    result["score"] = min(score, 100)


    # --------------------------------
    # Recommendations
    # --------------------------------

    recommendations = []


    if not email_present:

        recommendations.append(
            "Add a professional email address."
        )


    if not phone_present:

        recommendations.append(
            "Add a phone number."
        )


    if not section_result["summary"]:

        recommendations.append(
            "Add a short professional summary or career objective."
        )


    if not section_result["skills"]:

        recommendations.append(
            "Add a dedicated Technical Skills section."
        )


    if not section_result["education"]:

        recommendations.append(
            "Add an Education section."
        )


    if not section_result["experience"]:

        recommendations.append(
            "Add an Experience section."
        )


    if not section_result["projects"]:

        recommendations.append(
            "Add a Projects section to demonstrate practical experience."
        )


    if not section_result["certifications"]:

        recommendations.append(
            "Consider adding relevant certifications."
        )


    if not section_result["achievements"]:

        recommendations.append(
            "Consider adding achievements, awards, or measurable accomplishments."
        )


    if len(detected_skills) < 3:

        recommendations.append(
            "Add more relevant technical skills."
        )


    if not linkedin_present:

        recommendations.append(
            "Add your LinkedIn profile."
        )


    if not github_present:

        recommendations.append(
            "Add your GitHub profile if you have technical projects."
        )


    if word_count < 200:

        recommendations.append(
            "Your resume is quite short. Add more relevant details."
        )

    elif word_count > 1000:

        recommendations.append(
            "Your resume is lengthy. Consider removing unnecessary information."
        )


    result["recommendations"] = recommendations


    return result