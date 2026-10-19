from resume_parser.ai_analyzer import analyze_resume_with_ai


# -----------------------------------------
# Sample Resume
# -----------------------------------------

resume_text = """
I am a backend developer with experience in Java and Spring Boot.

I have developed REST APIs using Spring Boot and worked with
MySQL databases. I have used Git and Docker for development
and deployment.

Projects:
Developed an online banking application using Java, Spring Boot,
REST API and MySQL.
"""


# -----------------------------------------
# Selected Role
# -----------------------------------------

role_name = "Backend Developer"


# -----------------------------------------
# Role Skill Groups
# -----------------------------------------

role_skill_groups = [

    # Common Backend
    {
        "group_name": "Common Backend",
        "group_type": "common",
        "skill_name": "REST API",
        "importance": "core",
        "weight": 5.00
    },

    {
        "group_name": "Common Backend",
        "group_type": "common",
        "skill_name": "SQL",
        "importance": "core",
        "weight": 4.00
    },

    {
        "group_name": "Common Backend",
        "group_type": "common",
        "skill_name": "Git",
        "importance": "supporting",
        "weight": 2.00
    },

    {
        "group_name": "Common Backend",
        "group_type": "common",
        "skill_name": "Authentication",
        "importance": "supporting",
        "weight": 2.00
    },

    {
        "group_name": "Common Backend",
        "group_type": "common",
        "skill_name": "Docker",
        "importance": "optional",
        "weight": 1.00
    },


    # Python Backend
    {
        "group_name": "Python Backend",
        "group_type": "technology",
        "skill_name": "Python",
        "importance": "core",
        "weight": 5.00
    },

    {
        "group_name": "Python Backend",
        "group_type": "technology",
        "skill_name": "Flask",
        "importance": "supporting",
        "weight": 3.00
    },

    {
        "group_name": "Python Backend",
        "group_type": "technology",
        "skill_name": "Django",
        "importance": "supporting",
        "weight": 3.00
    },

    {
        "group_name": "Python Backend",
        "group_type": "technology",
        "skill_name": "FastAPI",
        "importance": "supporting",
        "weight": 3.00
    },


    # Node.js Backend
    {
        "group_name": "Node.js Backend",
        "group_type": "technology",
        "skill_name": "Node.js",
        "importance": "core",
        "weight": 5.00
    },

    {
        "group_name": "Node.js Backend",
        "group_type": "technology",
        "skill_name": "Express",
        "importance": "supporting",
        "weight": 3.00
    },

    {
        "group_name": "Node.js Backend",
        "group_type": "technology",
        "skill_name": "NestJS",
        "importance": "supporting",
        "weight": 3.00
    },

    {
        "group_name": "Node.js Backend",
        "group_type": "technology",
        "skill_name": "JavaScript",
        "importance": "supporting",
        "weight": 3.00
    },

    {
        "group_name": "Node.js Backend",
        "group_type": "technology",
        "skill_name": "TypeScript",
        "importance": "supporting",
        "weight": 2.00
    },


    # Java Backend
    {
        "group_name": "Java Backend",
        "group_type": "technology",
        "skill_name": "Java",
        "importance": "core",
        "weight": 5.00
    },

    {
        "group_name": "Java Backend",
        "group_type": "technology",
        "skill_name": "Spring Boot",
        "importance": "supporting",
        "weight": 4.00
    },

    {
        "group_name": "Java Backend",
        "group_type": "technology",
        "skill_name": "Hibernate",
        "importance": "supporting",
        "weight": 3.00
    },

    {
        "group_name": "Java Backend",
        "group_type": "technology",
        "skill_name": "JDBC",
        "importance": "supporting",
        "weight": 2.00
    },


    # .NET Backend
    {
        "group_name": ".NET Backend",
        "group_type": "technology",
        "skill_name": "C#",
        "importance": "core",
        "weight": 5.00
    },

    {
        "group_name": ".NET Backend",
        "group_type": "technology",
        "skill_name": ".NET",
        "importance": "core",
        "weight": 4.00
    },

    {
        "group_name": ".NET Backend",
        "group_type": "technology",
        "skill_name": "ASP.NET Core",
        "importance": "supporting",
        "weight": 4.00
    },

    {
        "group_name": ".NET Backend",
        "group_type": "technology",
        "skill_name": "Entity Framework",
        "importance": "supporting",
        "weight": 3.00
    }
]


# -----------------------------------------
# Run AI Analysis
# -----------------------------------------

result = analyze_resume_with_ai(
    resume_text,
    role_name,
    role_skill_groups
)


# -----------------------------------------
# Display Result
# -----------------------------------------

print("\n==============================")
print("AI RESUME ANALYSIS")
print("==============================\n")


if result:

    print("Technology Path:")
    print(result["technology_path"])


    print("\nOverall Relevance:")
    print(result["overall_relevance"])


    print("\nMatched Skills:")

    for skill in result["matched_skills"]:
        print("✓", skill)


    print("\nSemantic Matches:")

    for match in result["semantic_matches"]:
        print("✓", match)


    print("\nMissing Important Skills:")

    for skill in result["missing_important_skills"]:
        print("•", skill)


    print("\nExperience Relevance:")
    print(result["experience_relevance"])


    print("\nProject Relevance:")
    print(result["project_relevance"])


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