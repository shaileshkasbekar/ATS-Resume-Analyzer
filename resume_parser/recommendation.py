"""
Learning plan for missing skills.

For each missing skill: what to learn, a free resource,
a project idea that proves the skill on a resume,
and a rough time estimate.
"""

from urllib.parse import quote_plus


# skill: (time, resource name, resource url, project idea, [steps])

LEARNING_PATHS = {

    # ---------------- Languages ----------------

    "python": ("3-4 weeks", "Official Python Tutorial", "https://docs.python.org/3/tutorial/",
               "A command-line expense tracker that saves data to a CSV file",
               ["Syntax, data types, lists and dictionaries", "Functions, modules and error handling", "Classes, file handling and virtual environments"]),

    "java": ("4-6 weeks", "Learn Java (dev.java)", "https://dev.java/learn/",
             "A library management system with classes for books, members and loans",
             ["Syntax, data types and control flow", "OOP: classes, inheritance, interfaces", "Collections, exceptions and streams"]),

    "javascript": ("3-4 weeks", "The Modern JavaScript Tutorial", "https://javascript.info/",
                   "An interactive to-do app with filters and local storage",
                   ["Variables, functions, arrays and objects", "DOM manipulation and events", "Promises, async/await and fetch"]),

    "typescript": ("1-2 weeks", "TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/intro.html",
                   "Convert one of your JavaScript projects to TypeScript",
                   ["Basic types and interfaces", "Generics and union types", "Using TypeScript with React or Node.js"]),

    "c#": ("4 weeks", "C# documentation (Microsoft Learn)", "https://learn.microsoft.com/en-us/dotnet/csharp/",
           "A console banking app with accounts and transactions",
           ["Syntax and types", "Classes, interfaces and LINQ", "Async programming"]),

    "kotlin": ("3 weeks", "Kotlin docs: Getting started", "https://kotlinlang.org/docs/getting-started.html",
               "A notes app for Android written fully in Kotlin",
               ["Syntax, null safety and data classes", "Collections and lambdas", "Coroutines basics"]),

    "dart": ("1-2 weeks", "Dart language tour", "https://dart.dev/language",
             "Small Dart programs before moving to Flutter",
             ["Syntax and types", "Classes and null safety", "Async with Futures and Streams"]),

    # ---------------- Web frontend ----------------

    "html": ("1 week", "MDN: HTML", "https://developer.mozilla.org/en-US/docs/Web/HTML",
             "A personal portfolio page",
             ["Page structure and semantic tags", "Forms and inputs", "Accessibility basics"]),

    "css": ("2 weeks", "MDN: CSS", "https://developer.mozilla.org/en-US/docs/Web/CSS",
            "Style your portfolio with a responsive layout",
            ["Selectors, box model and colors", "Flexbox and Grid", "Media queries for mobile"]),

    "responsive design": ("1 week", "web.dev: Learn Responsive Design", "https://web.dev/learn/design",
                          "Make an existing project work well on phone, tablet and desktop",
                          ["Mobile-first layouts", "Flexible images and units", "Media and container queries"]),

    "bootstrap": ("3-4 days", "Bootstrap docs", "https://getbootstrap.com/docs/5.3/getting-started/introduction/",
                  "A responsive landing page using Bootstrap components",
                  ["Grid system", "Components: navbar, cards, modals", "Utility classes"]),

    "tailwind css": ("1 week", "Tailwind CSS docs", "https://tailwindcss.com/docs",
                     "Rebuild a page of your project with Tailwind",
                     ["Utility-first styling", "Responsive and hover variants", "Custom theme configuration"]),

    "react": ("3-4 weeks", "react.dev: Learn React", "https://react.dev/learn",
              "A movie search app that calls a public API",
              ["Components, props and JSX", "State, effects and events", "Routing and fetching data from an API"]),

    "angular": ("4 weeks", "Angular tutorials", "https://angular.dev/tutorials",
                "A task manager with routing and forms",
                ["Components and templates", "Services and dependency injection", "Routing, forms and HTTP client"]),

    "vue": ("3 weeks", "Vue.js guide", "https://vuejs.org/guide/introduction.html",
            "A weather dashboard using a public API",
            ["Template syntax and reactivity", "Components and props", "Vue Router and Pinia"]),

    "next.js": ("2 weeks", "Next.js Learn", "https://nextjs.org/learn",
                "A blog with server-rendered pages",
                ["Pages and routing", "Data fetching and server components", "Deploying to Vercel"]),

    "redux": ("1 week", "Redux Essentials tutorial", "https://redux.js.org/tutorial/essentials/part-1-overview-concepts",
              "Add a shopping cart with Redux Toolkit to a React app",
              ["Store, actions and reducers", "Redux Toolkit slices", "Async logic with thunks"]),

    # ---------------- Backend ----------------

    "node.js": ("3 weeks", "Node.js Learn", "https://nodejs.org/en/learn",
                "A REST API for a notes app",
                ["Modules, npm and the event loop", "File system and HTTP", "Async patterns and error handling"]),

    "express": ("1-2 weeks", "Express getting started", "https://expressjs.com/en/starter/installing.html",
                "A REST API with authentication and a MongoDB or MySQL database",
                ["Routing and middleware", "Connecting a database", "Validation and error handling"]),

    "nestjs": ("2 weeks", "NestJS docs", "https://docs.nestjs.com/",
               "A modular REST API with users and posts",
               ["Modules, controllers and providers", "Dependency injection", "Guards, pipes and TypeORM/Prisma"]),

    "flask": ("2 weeks", "Flask tutorial", "https://flask.palletsprojects.com/en/stable/tutorial/",
              "A blog with login, posts and a MySQL database",
              ["Routes and templates", "Forms, sessions and blueprints", "Database access and deployment"]),

    "django": ("3-4 weeks", "Django tutorial", "https://docs.djangoproject.com/en/stable/intro/tutorial01/",
               "A job board with user accounts and an admin panel",
               ["Models, views and templates", "Django ORM and admin", "Authentication and Django REST Framework"]),

    "fastapi": ("1-2 weeks", "FastAPI tutorial", "https://fastapi.tiangolo.com/tutorial/",
                "A REST API with automatic docs and JWT login",
                ["Path and query parameters", "Pydantic models and validation", "Dependencies, auth and databases"]),

    "spring boot": ("4-5 weeks", "Spring guides", "https://spring.io/guides",
                    "A REST API for an e-commerce app with Spring Data JPA and MySQL",
                    ["REST controllers and dependency injection", "Spring Data JPA with a database", "Spring Security with JWT"]),

    "hibernate": ("2 weeks", "Hibernate ORM documentation", "https://hibernate.org/orm/documentation/",
                  "Add JPA entities and relationships to a Spring Boot project",
                  ["Entities and mappings", "Relationships (one-to-many, many-to-many)", "HQL and performance basics"]),

    "jdbc": ("1 week", "Oracle JDBC tutorial", "https://docs.oracle.com/javase/tutorial/jdbc/",
             "A Java console app that stores data in MySQL",
             ["Connections and statements", "PreparedStatement and ResultSet", "Transactions"]),

    ".net": ("4 weeks", ".NET learning (Microsoft Learn)", "https://learn.microsoft.com/en-us/dotnet/",
             "A web API with ASP.NET Core and Entity Framework",
             ["C# fundamentals", ".NET CLI and project structure", "Building a web API"]),

    "asp.net core": ("3 weeks", "ASP.NET Core docs", "https://learn.microsoft.com/en-us/aspnet/core/",
                     "A REST API with authentication",
                     ["Controllers and minimal APIs", "Dependency injection and middleware", "Authentication and authorization"]),

    "entity framework": ("1-2 weeks", "EF Core docs", "https://learn.microsoft.com/en-us/ef/core/",
                         "Add a database to your ASP.NET Core API",
                         ["DbContext and models", "Migrations", "Querying with LINQ"]),

    "rest api": ("1 week", "RESTful API guide", "https://restfulapi.net/",
                 "Design and build a CRUD API, then document it with Postman or Swagger",
                 ["HTTP methods and status codes", "Resource design and URLs", "Pagination, errors and versioning"]),

    "graphql": ("1-2 weeks", "Learn GraphQL", "https://graphql.org/learn/",
                "A GraphQL API for a blog",
                ["Schemas and types", "Queries and mutations", "Resolvers"]),

    "authentication": ("1 week", "Introduction to JWT", "https://jwt.io/introduction",
                       "Add sign-up, login and protected routes to a project",
                       ["Password hashing", "Sessions vs JWT tokens", "OAuth login (Google/GitHub)"]),

    # ---------------- Databases ----------------

    "sql": ("2 weeks", "SQLBolt interactive lessons", "https://sqlbolt.com/",
            "Design a database for a college or shop and write 20 useful queries",
            ["SELECT, WHERE, ORDER BY", "JOINs and GROUP BY", "Subqueries, indexes and normalization"]),

    "mysql": ("1 week", "MySQL tutorial", "https://dev.mysql.com/doc/refman/8.0/en/tutorial.html",
              "Connect one of your apps to MySQL",
              ["Creating databases and tables", "Queries and joins", "Users, indexes and backups"]),

    "postgresql": ("1-2 weeks", "PostgreSQL tutorial", "https://www.postgresql.org/docs/current/tutorial.html",
                   "Move a project's database to PostgreSQL",
                   ["Tables, types and constraints", "Joins and window functions", "Indexes and JSON columns"]),

    "mongodb": ("1-2 weeks", "MongoDB University", "https://learn.mongodb.com/",
                "A notes or chat app storing data in MongoDB",
                ["Documents and collections", "CRUD queries", "Aggregation and indexes"]),

    "sqlite": ("2-3 days", "SQLite documentation", "https://www.sqlite.org/docs.html",
               "Store app data locally with SQLite",
               ["Creating tables", "Queries", "Using SQLite from your language"]),

    "firebase": ("1 week", "Firebase docs", "https://firebase.google.com/docs",
                 "A chat app with Firebase Authentication and Firestore",
                 ["Authentication", "Firestore database", "Hosting and storage"]),

    # ---------------- DevOps / Cloud ----------------

    "git": ("3-4 days", "Pro Git book", "https://git-scm.com/book/en/v2",
            "Put all your projects on GitHub with clear commits and READMEs",
            ["init, add, commit, log", "Branches and merging", "Pull requests and resolving conflicts"]),

    "github": ("2-3 days", "GitHub docs: Get started", "https://docs.github.com/en/get-started",
               "Publish your projects with a README and screenshots",
               ["Repositories and pushing code", "Pull requests and issues", "GitHub Pages and Actions"]),

    "linux": ("2 weeks", "Linux Journey", "https://linuxjourney.com/",
              "Host one of your apps on a Linux server or VM",
              ["File system and commands", "Permissions, processes and packages", "Networking and services"]),

    "shell scripting": ("1 week", "LinuxCommand.org", "https://linuxcommand.org/",
                        "A backup script that runs automatically with cron",
                        ["Variables and loops", "Conditions and functions", "Automating tasks with cron"]),

    "networking": ("1-2 weeks", "Cloudflare Learning Center", "https://www.cloudflare.com/learning/",
                   "Explain and diagram how your deployed app is reached from a browser",
                   ["IP, DNS and HTTP", "TCP/UDP and ports", "Load balancers and firewalls"]),

    "docker": ("1-2 weeks", "Docker: Get started", "https://docs.docker.com/get-started/",
               "Dockerize one of your projects with a Dockerfile and docker-compose",
               ["Images and containers", "Writing a Dockerfile", "Docker Compose for multi-container apps"]),

    "kubernetes": ("3 weeks", "Kubernetes basics tutorial", "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
                   "Deploy your Dockerized app to a local cluster (minikube)",
                   ["Pods, deployments and services", "ConfigMaps and secrets", "Scaling and rolling updates"]),

    "ci/cd": ("1 week", "GitHub Actions docs", "https://docs.github.com/en/actions",
              "A pipeline that tests and deploys your project on every push",
              ["Workflows, jobs and steps", "Running tests automatically", "Automatic deployment"]),

    "jenkins": ("1-2 weeks", "Jenkins tutorials", "https://www.jenkins.io/doc/tutorials/",
                "A Jenkins pipeline that builds and tests a project",
                ["Installing and jobs", "Jenkinsfile pipelines", "Integrating with Git"]),

    "terraform": ("2 weeks", "Terraform tutorials", "https://developer.hashicorp.com/terraform/tutorials",
                  "Create a cloud server and database with Terraform",
                  ["Providers and resources", "Variables and state", "Modules"]),

    "ansible": ("1-2 weeks", "Ansible getting started", "https://docs.ansible.com/ansible/latest/getting_started/index.html",
                "A playbook that sets up a web server",
                ["Inventory and ad-hoc commands", "Playbooks and roles", "Variables and templates"]),

    "prometheus": ("1 week", "Prometheus overview", "https://prometheus.io/docs/introduction/overview/",
                   "Monitor your app's requests and errors",
                   ["Metrics and scraping", "PromQL queries", "Alerting"]),

    "grafana": ("3-4 days", "Grafana tutorials", "https://grafana.com/tutorials/",
                "A dashboard for your app's metrics",
                ["Data sources", "Building dashboards", "Alerts"]),

    "aws": ("4 weeks", "AWS Skill Builder", "https://skillbuilder.aws/",
            "Deploy a full-stack app on AWS (EC2 or Elastic Beanstalk + RDS + S3)",
            ["IAM, EC2 and S3", "RDS and VPC basics", "Deploying and monitoring an app"]),

    "azure": ("4 weeks", "Azure training (Microsoft Learn)", "https://learn.microsoft.com/en-us/training/azure/",
              "Deploy a web app with Azure App Service and Azure SQL",
              ["Core services and portal", "App Service and storage", "Azure DevOps basics"]),

    "google cloud": ("4 weeks", "Google Cloud training", "https://cloud.google.com/learn/training",
                     "Deploy a containerized app on Cloud Run",
                     ["Projects, IAM and Compute Engine", "Cloud Run and Cloud Storage", "Cloud SQL and monitoring"]),

    # ---------------- Data / ML ----------------

    "statistics": ("3-4 weeks", "Khan Academy: Statistics", "https://www.khanacademy.org/math/statistics-probability",
                   "Analyze a public dataset and explain your findings with statistics",
                   ["Mean, median, variance and distributions", "Probability and sampling", "Hypothesis testing and regression"]),

    "pandas": ("1-2 weeks", "pandas: Getting started", "https://pandas.pydata.org/docs/getting_started/index.html",
               "Clean and analyze a Kaggle dataset in a Jupyter notebook",
               ["DataFrames and reading CSV", "Filtering, grouping and merging", "Cleaning missing data"]),

    "numpy": ("1 week", "NumPy: Learn", "https://numpy.org/learn/",
              "Implement simple statistics and matrix operations with NumPy",
              ["Arrays and indexing", "Vectorized math", "Broadcasting and linear algebra"]),

    "excel": ("1-2 weeks", "Excel help & learning", "https://support.microsoft.com/en-us/excel",
              "A sales dashboard with pivot tables and charts",
              ["Formulas and VLOOKUP/XLOOKUP", "Pivot tables", "Charts and conditional formatting"]),

    "power bi": ("2 weeks", "Power BI training (Microsoft Learn)", "https://learn.microsoft.com/en-us/training/powerplatform/power-bi",
                 "An interactive dashboard from a public dataset",
                 ["Importing and cleaning data", "Data modeling and DAX", "Reports and dashboards"]),

    "tableau": ("2 weeks", "Tableau free training", "https://www.tableau.com/learn/training",
                "A Tableau Public dashboard you can link on your resume",
                ["Connecting data", "Charts and calculated fields", "Dashboards and stories"]),

    "matplotlib": ("3-4 days", "Matplotlib tutorials", "https://matplotlib.org/stable/tutorials/index.html",
                   "Visualize trends in a dataset",
                   ["Line, bar and scatter plots", "Subplots and styling", "Saving figures"]),

    "seaborn": ("3-4 days", "Seaborn tutorial", "https://seaborn.pydata.org/tutorial.html",
                "Exploratory data analysis of a Kaggle dataset",
                ["Distribution plots", "Categorical plots", "Heatmaps and pair plots"]),

    "jupyter": ("1-2 days", "Jupyter documentation", "https://docs.jupyter.org/en/latest/",
                "Publish a clean analysis notebook on GitHub",
                ["Running notebooks", "Markdown cells and charts", "Sharing notebooks"]),

    "machine learning": ("6-8 weeks", "Google Machine Learning Crash Course", "https://developers.google.com/machine-learning/crash-course",
                         "A house price or spam prediction model with a short report",
                         ["Supervised vs unsupervised learning", "Regression and classification", "Evaluation, overfitting and feature engineering"]),

    "deep learning": ("6-8 weeks", "fast.ai Practical Deep Learning", "https://course.fast.ai/",
                      "An image classifier deployed as a small web app",
                      ["Neural network basics", "CNNs for images", "Transfer learning and deployment"]),

    "scikit-learn": ("2 weeks", "scikit-learn: Getting started", "https://scikit-learn.org/stable/getting_started.html",
                     "Compare 3 models on a dataset and explain which is best",
                     ["Fit/predict and train-test split", "Pipelines and preprocessing", "Cross-validation and metrics"]),

    "pytorch": ("3-4 weeks", "PyTorch tutorials", "https://pytorch.org/tutorials/",
                "Train an image classifier on CIFAR-10",
                ["Tensors and autograd", "Building and training models", "Datasets, DataLoaders and GPU"]),

    "tensorflow": ("3-4 weeks", "TensorFlow tutorials", "https://www.tensorflow.org/tutorials",
                   "Train a text or image classifier with Keras",
                   ["Tensors and Keras models", "Training and evaluation", "Saving and serving models"]),

    "keras": ("1-2 weeks", "Keras: Getting started", "https://keras.io/getting_started/",
              "Build a digit recognizer (MNIST)",
              ["Sequential and functional API", "Layers and training", "Callbacks"]),

    "xgboost": ("1 week", "XGBoost: Get started", "https://xgboost.readthedocs.io/en/stable/get_started.html",
                "Beat a baseline model on a Kaggle tabular competition",
                ["Gradient boosting idea", "Training and tuning", "Feature importance"]),

    "mlflow": ("1 week", "MLflow documentation", "https://mlflow.org/docs/latest/index.html",
               "Track experiments for one of your ML projects",
               ["Tracking runs and metrics", "Model registry", "Serving models"]),

    "nlp": ("4 weeks", "Hugging Face NLP Course", "https://huggingface.co/learn/nlp-course",
            "A sentiment analyzer for product reviews",
            ["Text preprocessing", "Transformers and tokenizers", "Fine-tuning a model"]),

    # ---------------- Mobile ----------------

    "android sdk": ("4-6 weeks", "Android Developers courses", "https://developer.android.com/courses",
                    "A notes or expense app published on GitHub (or the Play Store)",
                    ["Activities, layouts and navigation", "ViewModel and Room database", "Calling APIs with Retrofit"]),

    "jetpack compose": ("2 weeks", "Jetpack Compose tutorial", "https://developer.android.com/develop/ui/compose/tutorial",
                        "Rebuild an app screen with Compose",
                        ["Composables and state", "Layouts and lists", "Navigation and theming"]),

    "coroutines": ("1 week", "Kotlin coroutines guide", "https://kotlinlang.org/docs/coroutines-guide.html",
                   "Load data from an API in the background in your Android app",
                   ["suspend functions and launch", "Dispatchers and scopes", "Flow basics"]),

    "flutter": ("4 weeks", "Flutter: Get started", "https://docs.flutter.dev/get-started",
                "A cross-platform shopping list app",
                ["Widgets and layouts", "State management", "Networking and local storage"]),

    "xml": ("2-3 days", "Android layouts guide", "https://developer.android.com/develop/ui/views/layout/declaring-layout",
            "Design the screens of an Android app with XML layouts",
            ["Layout types", "Views and attributes", "Resources and styles"]),

    # ---------------- Testing ----------------

    "manual testing": ("2 weeks", "ISTQB Foundation syllabus", "https://www.istqb.org/",
                       "Write a full test plan and test cases for a website you use",
                       ["Testing types and levels", "Test design techniques", "Writing clear bug reports"]),

    "test cases": ("1 week", "ISTQB Foundation syllabus", "https://www.istqb.org/",
                   "Write 30 test cases for a login and checkout flow",
                   ["Boundary value and equivalence partitioning", "Positive and negative cases", "Test case templates"]),

    "sdlc": ("3-4 days", "Atlassian: Agile guide", "https://www.atlassian.com/agile",
             "Describe how your team project moved through each SDLC phase",
             ["SDLC and STLC phases", "Agile and Scrum", "Where testing fits"]),

    "bug tracking": ("2-3 days", "Jira guides", "https://www.atlassian.com/software/jira/guides",
                     "Track the bugs of a project in a free Jira board",
                     ["Bug life cycle", "Severity vs priority", "Writing reproducible bug reports"]),

    "api testing": ("1 week", "Postman Learning Center", "https://learning.postman.com/docs/introduction/overview/",
                    "A Postman collection with tests for a public API",
                    ["Requests and responses", "Writing test scripts", "Collections and environments"]),

    "selenium": ("3 weeks", "Selenium documentation", "https://www.selenium.dev/documentation/",
                 "Automate login, search and checkout tests for a demo shop site",
                 ["Locators and WebDriver", "Waits and actions", "Page Object Model"]),

    "testng": ("1 week", "TestNG documentation", "https://testng.org/",
               "Organize your Selenium tests with TestNG and reports",
               ["Annotations", "Assertions and groups", "Data providers and reports"]),

    "pytest": ("1 week", "pytest: Get started", "https://docs.pytest.org/en/stable/getting-started.html",
               "Add unit tests to one of your Python projects",
               ["Writing tests and asserts", "Fixtures", "Parametrize and coverage"]),

    "junit": ("1 week", "JUnit 5 user guide", "https://junit.org/junit5/docs/current/user-guide/",
              "Add unit tests to one of your Java projects",
              ["Test methods and assertions", "Lifecycle annotations", "Parameterized tests"]),

    "cypress": ("2 weeks", "Cypress documentation", "https://docs.cypress.io/",
                "End-to-end tests for one of your web apps",
                ["Writing your first test", "Selectors and assertions", "Fixtures and CI"]),

    "playwright": ("2 weeks", "Playwright docs", "https://playwright.dev/docs/intro",
                   "Cross-browser tests for a web app",
                   ["Writing tests", "Locators and auto-waiting", "Running in CI"]),

    "jest": ("1 week", "Jest: Getting started", "https://jestjs.io/docs/getting-started",
             "Add unit tests to a JavaScript or React project",
             ["Writing tests and matchers", "Mocking", "Testing async code"]),
}


IMPORTANCE_ORDER = {"core": 0, "supporting": 1, "optional": 2}


def _fallback(skill):
    """
    Generic plan for skills we have no entry for.
    """

    return (
        "1-3 weeks",
        "YouTube tutorials for " + skill,
        "https://www.youtube.com/results?search_query=" + quote_plus(skill + " tutorial for beginners"),
        f"A small project that uses {skill} and is on your GitHub",
        [f"Learn the basics of {skill} from the official docs", "Follow one complete beginner tutorial", "Use it in a project and mention it on your resume"]
    )


def build_learning_plan(missing_skills, role_skill_groups=None, limit=6):
    """
    Returns a list of plan items, most important skills first:

    [{"skill", "importance", "time", "resource_name",
      "resource_url", "project", "steps"}, ...]
    """

    # Importance of each skill in the selected role

    importance = {}

    for skill_data in role_skill_groups or []:

        name = skill_data["skill_name"].strip().lower()
        level = skill_data["importance"]

        if IMPORTANCE_ORDER.get(level, 3) < IMPORTANCE_ORDER.get(importance.get(name), 3):
            importance[name] = level

    # Unique skills, keep original spelling

    seen = set()
    skills = []

    for skill in missing_skills:

        key = skill.strip().lower()

        if key and key not in seen:
            seen.add(key)
            skills.append(skill.strip())

    skills.sort(key=lambda s: IMPORTANCE_ORDER.get(importance.get(s.lower()), 3))

    plan = []

    for skill in skills[:limit]:

        time, resource_name, resource_url, project, steps = (
            LEARNING_PATHS.get(skill.lower()) or _fallback(skill)
        )

        plan.append({
            "skill": skill,
            "importance": importance.get(skill.lower(), ""),
            "time": time,
            "resource_name": resource_name,
            "resource_url": resource_url,
            "project": project,
            "steps": steps
        })

    return plan
