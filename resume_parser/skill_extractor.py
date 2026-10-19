import re


def extract_skills(text, extra_skills=None):
    """
    Finds skills in the resume text.

    extra_skills: skill names from the database (for example
    the selected job role's skills), so every skill a role
    needs can be detected even if it is not in the list below.
    """

    skills_database = [

        # Programming Languages
        "Python",
        "Java",
        "C",
        "C++",
        "C#",
        "JavaScript",
        "TypeScript",
        "PHP",

        # Frontend
        "HTML",
        "CSS",
        "Bootstrap",
        "React",
        "Angular",
        "Vue",

        # Backend
        "Flask",
        "Django",
        "Node.js",
        "Express",

        # Database
        "SQL",
        "MySQL",
        "MongoDB",
        "Oracle",
        "PostgreSQL",

        # Cloud & DevOps
        "AWS",
        "Azure",
        "Google Cloud",
        "Docker",
        "Kubernetes",
        "Git",
        "GitHub",
        "Linux",

        # Concepts
        "DBMS",
        "OOP",
        "Operating System",
        "Computer Networks",
        "Data Structures",
        "Algorithms",

        # AI / ML
        "Machine Learning",
        "Deep Learning",
        "Artificial Intelligence",
        "TensorFlow",
        "PyTorch",
        "NLP",
        "OpenCV",

        # Tools
        "VS Code",
        "Figma",
        "Postman",
        "Firebase",
        "MySQL Workbench",
        "XAMPP",

        # Frameworks + APIs
        "FastAPI",
        "NestJS",
        "Spring Boot",
        "Hibernate",
        "JDBC",
        ".NET",
        "ASP.NET Core",
        "Entity Framework",
        "REST API",
        "GraphQL",
        "Authentication",
        "Responsive Design",
        "Tailwind CSS",
        "Next.js",
        "Redux",

        # Data
        "Statistics",
        "Pandas",
        "NumPy",
        "Excel",
        "Power BI",
        "Tableau",
        "Matplotlib",
        "Scikit-learn",

        # Testing / DevOps
        "Jest",
        "JUnit",
        "Pytest",
        "CI/CD",
        "Jenkins"

    ]

    for skill in extra_skills or []:

        if skill and skill.lower() not in (s.lower() for s in skills_database):

            skills_database.append(skill)

    found_skills = []

    text = text.lower()

    for skill in skills_database:

        names = [skill] + SKILL_ALIASES.get(skill, [])

        if any(_contains_word(text, name) for name in names):

            found_skills.append(skill)

    return found_skills


# Other ways a skill is commonly written in resumes

SKILL_ALIASES = {
    "JavaScript": ["JS", "ES6"],
    "TypeScript": ["TS"],
    "React": ["ReactJS", "React.js"],
    "Angular": ["AngularJS"],
    "Vue": ["VueJS", "Vue.js"],
    "Node.js": ["NodeJS"],
    "Express": ["ExpressJS", "Express.js"],
    "PostgreSQL": ["Postgres"],
    "MongoDB": ["Mongo"],
    "Google Cloud": ["GCP"],
    "Kubernetes": ["K8s"],
    "OOP": ["OOPs", "Object Oriented Programming"],
    "DBMS": ["Database Management System"],
    "Operating System": ["Operating Systems", "OS"],
    "Data Structures": ["DSA"],
    "Machine Learning": ["ML"],
    "Deep Learning": ["DL"],
    "Artificial Intelligence": ["AI"],
    "NLP": ["Natural Language Processing"],
    "VS Code": ["VSCode", "Visual Studio Code"],
    "REST API": ["REST APIs", "RESTful", "RESTful API", "RESTful APIs", "REST-API"],
    "Authentication": ["JWT", "OAuth", "OAuth2", "Auth0"],
    "FastAPI": ["Fast API"],
    "NestJS": ["Nest.js"],
    "Spring Boot": ["SpringBoot", "Spring Framework"],
    "Hibernate": ["JPA"],
    ".NET": ["dotnet", "ASP.NET", ".NET Core"],
    "ASP.NET Core": ["ASP.NET MVC", "ASP.NET Web API"],
    "Entity Framework": ["EF Core"],
    "Responsive Design": ["Responsive Web Design", "Responsive"],
    "Tailwind CSS": ["Tailwind", "TailwindCSS"],
    "Next.js": ["NextJS"],
    "Power BI": ["PowerBI"],
    "Excel": ["MS Excel", "Microsoft Excel"],
    "Statistics": ["Statistical Analysis", "Hypothesis Testing"],
    "Scikit-learn": ["sklearn", "scikit learn"],
    "CI/CD": ["CI CD", "GitHub Actions"],
}


def _contains_word(text, name):
    """
    Match a skill as a whole word, so "Java" does not
    match "JavaScript", "SQL" does not match "MySQL"
    and "C" does not match "C++".
    """

    pattern = (
        r"(?<![\w+#.])"
        + re.escape(name.lower())
        + r"(?![\w+#]|\.\w)"
    )

    return re.search(pattern, text) is not None