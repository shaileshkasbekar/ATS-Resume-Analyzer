"""
More hand-labelled evaluation cases: newer roles (testing, Android, ML,
cloud, data) and more traps (C vs C++, PyTorch vs TensorFlow, skills only
mentioned in the summary, no skills section).
"""

MORE_CASES = [

    {
        "name": "QA tester - Selenium path and tool aliases",
        "job": """Software Tester
Requirements:
- Manual Testing and writing Test Cases
- Selenium with Java or Python
- Bug Tracking
Nice to have:
- API Testing, Jenkins""",
        "resume": """Kavya Iyer
EXPERIENCE
QA Intern, TestLab | Jan 2025 - Jun 2025
- Wrote test scenarios and did regression testing for a banking web app
- Automated login tests with Selenium and Python; logged defects in Jira
SKILLS
Selenium, Python, Postman, Jira""",
        "mandatory": ["manual testing", "test cases", "selenium", "java|python", "bug tracking"],
        "preferred": ["api testing", "jenkins"],
        "matched": {"manual testing": "experience", "test cases": "experience", "selenium": "experience",
                    "java|python": "experience", "bug tracking": "experience"},
        "missing": ["api testing", "jenkins"],
    },

    {
        "name": "Android - Kotlin and Jetpack, not Flutter",
        "job": """Android Developer
Requirements:
- Kotlin and the Android SDK
- Jetpack Compose
- REST API and Git
Nice to have:
- Firebase""",
        "resume": """Rahul Verma
PROJECTS
Notes App | Kotlin, Jetpack Compose
- Built an Android notes app in Android Studio with Kotlin and Jetpack Compose
- Synced notes through a REST API
SKILLS
Kotlin, Git, Flutter""",
        "mandatory": ["kotlin", "android sdk", "jetpack compose", "rest api", "git"],
        "preferred": ["firebase"],
        "matched": {"kotlin": "project", "android sdk": "project", "jetpack compose": "project",
                    "rest api": "project", "git": "listed"},
        "missing": ["firebase"],
    },

    {
        "name": "ML engineer - PyTorch is not TensorFlow",
        "job": """Machine Learning Engineer
Requirements:
- Python, Machine Learning and TensorFlow
- SQL
Nice to have:
- Docker, MLflow""",
        "resume": """Sneha Kulkarni
PROJECTS
Image Classifier | Python, PyTorch
- Trained a CNN in PyTorch with Python on 10,000 images
- Explored the data with Pandas and NumPy
SKILLS
Python, PyTorch, Machine Learning, Docker""",
        "mandatory": ["python", "machine learning", "tensorflow", "sql"],
        "preferred": ["docker", "mlflow"],
        "matched": {"python": "project", "machine learning": "project", "docker": "listed"},
        "missing": ["tensorflow", "sql", "mlflow"],
    },

    {
        "name": "Cloud - Amazon Web Services alias and GCP",
        "job": """Cloud Engineer
Requirements:
- AWS or Azure
- Terraform, Linux and Docker
Nice to have:
- Google Cloud""",
        "resume": """Vikram Shah
EXPERIENCE
Cloud Intern, InfraCo | Jun 2025 - Dec 2025
- Provisioned Amazon Web Services EC2 servers with Terraform on Linux
- Ran services in Docker containers
SKILLS
Terraform, Linux, Docker, GCP""",
        "mandatory": ["aws|azure", "terraform", "linux", "docker"],
        "preferred": ["google cloud"],
        "matched": {"aws|azure": "experience", "terraform": "experience", "linux": "experience",
                    "docker": "experience", "google cloud": "listed"},
        "missing": [],
    },

    {
        "name": "C is not C++ and C# is separate",
        "job": """Embedded Developer
Requirements:
- C and Linux
- Git
Nice to have:
- C++""",
        "resume": """Imran Ali
PROJECTS
Game Engine | C++, C#
- Wrote a 2D game engine in C++ with a C# editor on Linux
SKILLS
C++, C#, Git""",
        "mandatory": ["c", "linux", "git"],
        "preferred": ["c++"],
        "matched": {"linux": "project", "git": "listed", "c++": "project"},
        "missing": ["c"],
    },

    {
        "name": "Fresher frontend - ReactJS and JS aliases",
        "job": """Frontend Intern
Requirements:
- JavaScript, React and CSS
- Git
Nice to have:
- Next.js, Tailwind CSS""",
        "resume": """Pooja Reddy
PROJECTS
Portfolio | ReactJS, Tailwind
- Built a portfolio in ReactJS and JS styled with Tailwind and CSS3
SKILLS
JavaScript, ReactJS, Git""",
        "mandatory": ["javascript", "react", "css", "git"],
        "preferred": ["next.js", "tailwind css"],
        "matched": {"javascript": "project", "react": "project", "css": "project", "git": "listed",
                    "tailwind css": "project"},
        "missing": ["next.js"],
    },

    {
        "name": "Data scientist - Scikit-learn alias",
        "job": """Data Scientist
Requirements:
- Python, Statistics and Machine Learning
- Pandas and Scikit-learn
Nice to have:
- Tableau""",
        "resume": """Ananya Das
PROJECTS
Churn Model | Python, sklearn, Pandas
- Built a churn model with sklearn and Pandas, using hypothesis testing to pick features
- Applied machine learning to 5,000 customer records
SKILLS
Python, Pandas, Power BI""",
        "mandatory": ["python", "statistics", "machine learning", "pandas", "scikit-learn"],
        "preferred": ["tableau"],
        "matched": {"python": "project", "statistics": "project", "machine learning": "project",
                    "pandas": "project", "scikit-learn": "project"},
        "missing": ["tableau"],
    },

    {
        "name": "Node backend - NodeJS and Express.js aliases",
        "job": """Node.js Developer
Requirements:
- Node.js, Express and MongoDB
- REST API and JWT authentication
Nice to have:
- Redis, Docker""",
        "resume": """Karan Mehta
EXPERIENCE
Backend Intern, ShopCo | Feb 2025 - Jul 2025
- Built REST APIs with NodeJS and Express.js on MongoDB
- Secured routes with JWT
SKILLS
Node.js, MongoDB, Redis""",
        "mandatory": ["node.js", "express", "mongodb", "rest api", "authentication"],
        "preferred": ["redis", "docker"],
        "matched": {"node.js": "experience", "express": "experience", "mongodb": "experience",
                    "rest api": "experience", "authentication": "experience", "redis": "listed"},
        "missing": ["docker"],
    },

    {
        "name": "Required skill only mentioned in summary",
        "job": """Python Developer
Requirements:
- Python and Django
- PostgreSQL""",
        "resume": """Meera Joshi
SUMMARY
Python developer interested in Django and backend work.
PROJECTS
Inventory API | Python, FastAPI, PostgreSQL
- Built an inventory API with FastAPI and PostgreSQL""",
        "mandatory": ["python", "django", "postgresql"],
        "preferred": [],
        "matched": {"python": "project", "django": "mentioned", "postgresql": "project"},
        "missing": [],
    },

    {
        "name": "Bullets without a skills section",
        "job": """DevOps Intern
Requirements:
- Docker and CI/CD
- Linux
Nice to have:
- Kubernetes""",
        "resume": """Rohan Patil
EXPERIENCE
Intern, BuildCo | Jan 2025 - May 2025
- Set up GitHub Actions pipelines and Docker images on Ubuntu Linux servers""",
        "mandatory": ["docker", "ci/cd", "linux"],
        "preferred": ["kubernetes"],
        "matched": {"docker": "experience", "ci/cd": "experience", "linux": "experience"},
        "missing": ["kubernetes"],
    },

    {
        "name": "Excel and Power BI aliases",
        "job": """Business Analyst
Requirements:
- Excel and Power BI
- SQL
Nice to have:
- Python""",
        "resume": """Sana Khan
EXPERIENCE
Analyst Intern, RetailCo | Jun 2025 - Sep 2025
- Built weekly sales reports in MS Excel and PowerBI dashboards from SQL queries
SKILLS
Excel, SQL""",
        "mandatory": ["excel", "power bi", "sql"],
        "preferred": ["python"],
        "matched": {"excel": "experience", "power bi": "experience", "sql": "experience"},
        "missing": ["python"],
    },

    {
        "name": "Spring Boot developer - JPA proves Hibernate",
        "job": """Java Backend Developer
Requirements:
- Java, Spring Boot and Hibernate
- MySQL or PostgreSQL
Nice to have:
- Kafka, JUnit""",
        "resume": """Aditi Rao
PROJECTS
Bank API | Spring Boot, Spring Data JPA, PostgreSQL
- Built a banking REST API with Spring Boot and Spring Data JPA on PostgreSQL
- Wrote JUnit tests for the transfer service
SKILLS
Java, Spring Boot""",
        "mandatory": ["java", "spring boot", "hibernate", "mysql|postgresql"],
        "preferred": ["kafka", "junit"],
        "matched": {"java": "project", "spring boot": "project", "hibernate": "project",
                    "mysql|postgresql": "project", "junit": "project"},
        "missing": ["kafka"],
    },
]
