"""
Hand-labelled evaluation cases for the Job Match engine.

Each case has a job description, a resume and the CORRECT answers,
written by hand:

- mandatory / preferred: the requirements a careful reader finds in the job
  ("a|b" means one requirement that accepts either skill)
- matched / missing: whether the resume really shows each requirement
- evidence: where the strongest proof is (experience, project, listed, mentioned)

The cases are deliberately tricky (aliases, look-alike names, "or" choices,
"nice to have" inside a sentence, skills only listed). They are small and
synthetic: they measure the rule-based engine on known traps, not accuracy
on every real-world resume.
"""

CASES = [

    {
        "name": "Python backend fresher - aliases and alternatives",
        "job": """Junior Backend Developer
Requirements:
- Strong Python and Flask or Django
- Experience with MySQL or PostgreSQL
- REST API design, Git
Nice to have:
- Docker, AWS""",
        "resume": """Riya Sharma
PROJECTS
Expense API | Python, Flask, Postgres
- Built a RESTful API with Flask and Postgres used by 200 students
- Containerised the app with Docker
SKILLS
Python, Flask, Git, Postgres, Docker""",
        "mandatory": ["python", "flask|django", "mysql|postgresql", "rest api", "git"],
        "preferred": ["docker", "aws"],
        "matched": {"python": "project", "flask|django": "project", "mysql|postgresql": "project",
                    "rest api": "project", "git": "listed", "docker": "project"},
        "missing": ["aws"],
    },

    {
        "name": "Java vs JavaScript look-alike",
        "job": """Frontend Developer
Requirements:
- JavaScript, React, HTML, CSS
Nice to have:
- TypeScript""",
        "resume": """Arjun Patil
EXPERIENCE
Intern, WebCo | Jun 2025 - Aug 2025
- Built React pages in JavaScript with HTML5 and CSS3
SKILLS
Java, JavaScript, React""",
        "mandatory": ["javascript", "react", "html", "css"],
        "preferred": ["typescript"],
        "matched": {"javascript": "experience", "react": "experience", "html": "experience", "css": "experience"},
        "missing": ["typescript"],
    },

    {
        "name": "Flask is not Django",
        "job": """Django Developer
Requirements:
- Python and Django
- PostgreSQL""",
        "resume": """Sam Lee
PROJECTS
Blog | Python, Flask, MySQL
- Built a blog with Flask and MySQL""",
        "mandatory": ["python", "django", "postgresql"],
        "preferred": [],
        "matched": {"python": "project"},
        "missing": ["django", "postgresql"],
    },

    {
        "name": "Preferred marker inside one sentence",
        "job": "We need a Java developer with 3+ years of experience in Spring Boot and Hibernate. Kafka is a plus.",
        "resume": """Kiran Rao
EXPERIENCE
Software Engineer, PayCo | Jan 2021 - Dec 2024
- Built microservices with Spring Boot and Hibernate (JPA)
SKILLS
Java, Spring Boot, Kafka""",
        "mandatory": ["java", "spring boot", "hibernate"],
        "preferred": ["kafka"],
        "matched": {"java": "experience", "spring boot": "experience", "hibernate": "experience", "kafka": "listed"},
        "missing": [],
    },

    {
        "name": "DevOps with K8s alias and listed-only skills",
        "job": """DevOps Engineer
Requirements:
- Linux, Docker, Kubernetes
- CI/CD and Git
Nice to have:
- Terraform, Ansible""",
        "resume": """Neha Joshi
PROJECTS
Cluster Lab | K8s, Docker
- Deployed services on a K8s cluster with Docker and GitHub Actions
SKILLS
Linux, Git, Docker, Kubernetes, Terraform""",
        "mandatory": ["linux", "docker", "kubernetes", "ci/cd", "git"],
        "preferred": ["terraform", "ansible"],
        # Git counts as used in the project: GitHub Actions workflows run on a Git repository
        "matched": {"linux": "listed", "docker": "project", "kubernetes": "project", "ci/cd": "project",
                    "git": "project", "terraform": "listed"},
        "missing": ["ansible"],
    },

    {
        "name": "Data analyst - SQL is not MySQL in the job",
        "job": """Data Analyst
Requirements:
- SQL, Excel and Power BI
- Statistics
Nice to have:
- Python, Pandas""",
        "resume": """Priya Nair
PROJECTS
Sales Dashboard | Power BI, MySQL
- Built a Power BI dashboard from MySQL sales data
- Used Pandas in Python to clean 10,000 rows
SKILLS
Excel, MySQL, Power BI, Python, Pandas""",
        "mandatory": ["sql", "excel", "power bi", "statistics"],
        "preferred": ["python", "pandas"],
        "matched": {"excel": "listed", "power bi": "project", "python": "project", "pandas": "project"},
        "missing": ["sql", "statistics"],
    },

    {
        "name": "Such-as list is one requirement",
        "job": """Web Developer
Requirements:
- A modern framework such as React, Angular or Vue
- Node.js and Express
- MongoDB""",
        "resume": """Omar Khan
PROJECTS
Chat App | Vue.js, Node.js, Express, MongoDB
- Built a real-time chat with Vue.js, Node.js, Express and MongoDB""",
        "mandatory": ["react|angular|vue", "node.js", "express", "mongodb"],
        "preferred": [],
        "matched": {"react|angular|vue": "project", "node.js": "project", "express": "project", "mongodb": "project"},
        "missing": [],
    },

    {
        "name": "Framework proves the language",
        "job": """Backend Engineer
Requirements:
- Java, Spring Boot, MySQL
- Git""",
        "resume": """Anita Desai
PROJECTS
Shop API | Spring Boot, MySQL
- Built REST endpoints with Spring Boot and MySQL
SKILLS
Java, Git""",
        "mandatory": ["java", "spring boot", "mysql", "git"],
        "preferred": [],
        "matched": {"java": "project", "spring boot": "project", "mysql": "project", "git": "listed"},
        "missing": [],
    },
]


from evaluation.cases_more import MORE_CASES  # noqa: E402

CASES = CASES + MORE_CASES
