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

        # Backend architecture / messaging
        "Microservices",
        "Kafka",
        "RabbitMQ",
        "Redis",
        "Elasticsearch",
        "Maven",
        "Gradle",
        "Laravel",
        "Ruby on Rails",
        "Swift",

        # Process
        "Agile",
        "Scrum",
        "Unit Testing",

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
    "CI/CD": ["CI CD", "GitHub Actions", "GitLab CI"],

    # DevOps
    "Shell Scripting": ["Bash", "Shell Script", "Bash Scripting", "PowerShell"],
    "Networking": ["TCP/IP", "DNS", "Computer Networking"],

    # Android
    "Android SDK": ["Android Studio", "Android Development", "Android"],
    "Jetpack Compose": ["Jetpack"],
    "Coroutines": ["Kotlin Coroutines"],

    # ML / Data
    "Jupyter": ["Jupyter Notebook", "JupyterLab"],
    "XGBoost": ["LightGBM"],

    # Testing
    "Manual Testing": ["Functional Testing", "Regression Testing", "Black Box Testing"],
    "Test Cases": ["Test Case", "Test Scenarios", "Test Plan", "Test Plans"],
    "SDLC": ["STLC", "Software Development Life Cycle"],
    "Bug Tracking": ["Jira", "Bugzilla", "Defect Tracking", "Bug Reporting"],
    "API Testing": ["Rest Assured", "RestAssured"],

    # Backend architecture
    "Microservices": ["Microservice", "Microservice Architecture"],
    "Kafka": ["Apache Kafka"],
    "Unit Testing": ["Unit Tests", "Unit Test"],
    "Agile": ["Agile Methodology", "Agile Development"],
    "Ruby on Rails": ["Rails"],
    "AWS": ["Amazon Web Services"],
    "Google Cloud": ["GCP", "Google Cloud Platform"],
    "Azure": ["Microsoft Azure"],
}


def canonical_skill(name):
    """
    Maps another name of a skill to its main name:
    "ReactJS" -> "React", "Postgres" -> "PostgreSQL".
    Unknown names are returned unchanged.
    """

    key = name.strip().lower()

    for canonical, aliases in SKILL_ALIASES.items():

        if key == canonical.lower() or key in (a.lower() for a in aliases):
            return canonical

    return name.strip()


def is_known_skill(name):
    """
    True if the name is a skill we know (main name or other name).
    """

    key = name.strip().lower()

    return any(
        key == canonical.lower() or key in (a.lower() for a in aliases)
        for canonical, aliases in SKILL_ALIASES.items()
    )


def skill_in_text(text, skill):
    """
    True if the skill (or one of its other names)
    appears in the text as a whole word.
    """

    text = text.lower()

    names = [skill] + SKILL_ALIASES.get(skill, [])

    # Aliases are stored by canonical name, so also look up
    # case-insensitively (database skills may differ in case)

    for canonical, aliases in SKILL_ALIASES.items():

        if canonical.lower() == skill.lower():
            names += aliases

    return any(_contains_word(text, name) for name in names)


def find_skill_evidence(text, skills):
    """
    For each skill, checks whether it is actually used in the
    Experience / Projects sections or only listed somewhere else.

    Returns {"python": "used", "docker": "listed", ...}

    If the resume has no Experience or Projects section,
    every skill counts as "used" (we cannot judge, so no penalty).
    """

    # Imported here to avoid a circular import

    from resume_parser.sections import split_sections

    sections = split_sections(text)

    work_text = (
        sections.get("experience", "")
        + "\n"
        + sections.get("projects", "")
    )

    evidence = {}

    for skill in skills:

        # Using a framework proves the language too,
        # e.g. Spring Boot in a project -> Java is used

        proof = [skill] + IMPLIED_BY.get(skill.lower(), [])

        if not work_text.strip() or any(skill_in_text(work_text, name) for name in proof):
            evidence[skill.lower()] = "used"
        else:
            evidence[skill.lower()] = "listed"

    return evidence


# Skills whose use in a project also proves the key skill

IMPLIED_BY = {
    "java": ["Spring Boot", "Hibernate", "JDBC", "Maven", "JUnit"],
    "python": ["Django", "Flask", "FastAPI", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Scikit-learn"],
    "javascript": ["React", "Node.js", "Express", "Angular", "Vue", "Next.js", "TypeScript"],
    "typescript": ["Angular", "NestJS"],
    "node.js": ["Express", "NestJS"],
    "react": ["Next.js", "Redux"],
    "html": ["React", "Angular", "Vue"],
    "css": ["Tailwind CSS", "Bootstrap"],
    "sql": ["MySQL", "PostgreSQL", "SQLite", "Oracle"],
    "c#": [".NET", "ASP.NET Core", "Entity Framework"],
    ".net": ["ASP.NET Core", "Entity Framework"],
    "git": ["GitHub"],
    "machine learning": ["Scikit-learn", "TensorFlow", "PyTorch", "Deep Learning"],
    "deep learning": ["TensorFlow", "PyTorch", "Keras"],
    "kotlin": ["Jetpack Compose"],
    "dart": ["Flutter"],
    "rest api": ["FastAPI", "Express", "Spring Boot"],
}


def skill_names(skill):
    """
    The skill's main name plus all its other names.
    """

    names = [skill]

    for canonical, aliases in SKILL_ALIASES.items():

        if canonical.lower() == skill.lower():
            names += aliases

    return names


def find_skill_span(text, skill):
    """
    (start, end) of the first place the skill or one of its other
    names appears in the text, or None.
    """

    text = text.lower()

    best = None

    for name in skill_names(skill):

        match = re.search(_word_pattern(name), text)

        if match and (best is None or match.start() < best[0]):
            best = (match.start(), match.end())

    return best


def _word_pattern(name):

    return (
        r"(?<![\w+#.])"
        + re.escape(name.lower())
        + r"(?![\w+#]|\.\w)"
    )


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