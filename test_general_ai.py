from resume_parser.general_ai_analyzer import (
    analyze_general_resume_with_ai
)


resume_text = """
John Doe

Software Developer

Email: john@example.com
Phone: 9876543210

SUMMARY

Software developer with experience in Java,
Spring Boot and REST API development.

EXPERIENCE

Software Developer

Developed REST APIs using Spring Boot.
Worked with MySQL databases.
Used Git and Docker.

PROJECTS

Online Banking Application

Developed an online banking application using
Java, Spring Boot, REST API and MySQL.

SKILLS

Java
Spring Boot
REST API
MySQL
Git
Docker

EDUCATION

Bachelor of Computer Engineering
"""


result = analyze_general_resume_with_ai(
    resume_text
)


print("\n==============================")
print("GENERAL AI RESUME ANALYSIS")
print("==============================\n")


if result:

    print("Overall Quality:")
    print(result["overall_quality"])


    print("\nSummary Quality:")
    print(result["summary_quality"])


    print("\nExperience Quality:")
    print(result["experience_quality"])


    print("\nProject Quality:")
    print(result["project_quality"])


    print("\nSkills Quality:")
    print(result["skills_quality"])


    print("\nClarity Quality:")
    print(result["clarity_quality"])


    print("\nStrengths:")

    for item in result["strengths"]:
        print("✓", item)


    print("\nWeaknesses:")

    for item in result["weaknesses"]:
        print("•", item)


    print("\nRecommendations:")

    for item in result["recommendations"]:
        print("→", item)


else:

    print("AI analysis failed.")