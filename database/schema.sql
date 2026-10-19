-- ============================================================
-- ATS RESUME ANALYZER
-- COMPLETE DATABASE SCHEMA
-- Database: ats_resume_analyzer_v2
-- ============================================================


-- ============================================================
-- DATABASE
-- ============================================================

CREATE DATABASE IF NOT EXISTS ats_resume_analyzer_v2;

USE ats_resume_analyzer_v2;


-- ============================================================
-- USERS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS users (

    user_id INT AUTO_INCREMENT PRIMARY KEY,

    full_name VARCHAR(100) NOT NULL,

    email VARCHAR(100) NOT NULL UNIQUE,

    password VARCHAR(255) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);


-- ============================================================
-- RESUMES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS resumes (

    resume_id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    file_name VARCHAR(255) NOT NULL,

    file_path VARCHAR(500) NOT NULL,

    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE

);


-- ============================================================
-- JOB ROLES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS job_roles (

    role_id INT AUTO_INCREMENT PRIMARY KEY,

    role_name VARCHAR(100) NOT NULL UNIQUE,

    description TEXT

);


-- ============================================================
-- SKILLS MASTER TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS skills (

    skill_id INT AUTO_INCREMENT PRIMARY KEY,

    skill_name VARCHAR(100) NOT NULL UNIQUE

);


-- ============================================================
-- ROLE SKILL GROUPS
--
-- Allows multiple valid technology paths for one role.
--
-- Example:
--
-- Backend Developer
--     ├── Common Backend
--     ├── Python Backend
--     ├── Node.js Backend
--     ├── Java Backend
--     └── .NET Backend
--
-- ============================================================

CREATE TABLE IF NOT EXISTS role_skill_groups (

    group_id INT AUTO_INCREMENT PRIMARY KEY,

    role_id INT NOT NULL,

    group_name VARCHAR(100) NOT NULL,

    group_type ENUM(
        'common',
        'technology',
        'specialization'
    ) DEFAULT 'technology',

    description TEXT,

    FOREIGN KEY (role_id)
        REFERENCES job_roles(role_id)
        ON DELETE CASCADE,

    UNIQUE (role_id, group_name)

);


-- ============================================================
-- JOB ROLE SKILLS
--
-- Each skill belongs to a particular role/technology group.
--
-- importance:
-- core       = important/core skill
-- supporting = supporting skill
-- optional   = optional/advanced skill
--
-- weight will later be used by the ATS scoring engine.
--
-- ============================================================

CREATE TABLE IF NOT EXISTS job_role_skills (

    id INT AUTO_INCREMENT PRIMARY KEY,

    role_id INT NOT NULL,

    group_id INT NOT NULL,

    skill_name VARCHAR(100) NOT NULL,

    importance ENUM(
        'core',
        'supporting',
        'optional'
    ) DEFAULT 'supporting',

    weight DECIMAL(5,2) DEFAULT 1.00,

    FOREIGN KEY (role_id)
        REFERENCES job_roles(role_id)
        ON DELETE CASCADE,

    FOREIGN KEY (group_id)
        REFERENCES role_skill_groups(group_id)
        ON DELETE CASCADE,

    UNIQUE (group_id, skill_name)

);


-- ============================================================
-- ATS RESUME RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS resume_results (

    result_id INT AUTO_INCREMENT PRIMARY KEY,

    resume_id INT NOT NULL,

    role_id INT NOT NULL,

    ats_score DECIMAL(5,2),

    matched_skills TEXT,

    missing_skills TEXT,

    recommended_skills TEXT,

    detected_stack VARCHAR(150),

    match_level VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (resume_id)
        REFERENCES resumes(resume_id)
        ON DELETE CASCADE,

    FOREIGN KEY (role_id)
        REFERENCES job_roles(role_id)
        ON DELETE CASCADE

);


-- ============================================================
-- GENERAL RESUME RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS general_results (

    general_result_id INT AUTO_INCREMENT PRIMARY KEY,

    resume_id INT NOT NULL,

    score DECIMAL(5,2),

    email_detected BOOLEAN,

    phone_detected BOOLEAN,

    word_count INT,

    skills TEXT,

    sections TEXT,

    recommendations TEXT,

    linkedin_detected BOOLEAN DEFAULT 0,

    github_detected BOOLEAN DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (resume_id)
        REFERENCES resumes(resume_id)
        ON DELETE CASCADE

);


-- ============================================================
-- DEFAULT JOB ROLES
-- ============================================================

INSERT INTO job_roles
(role_id, role_name, description)
VALUES

(
    1,
    'Python Developer',
    'Develops applications and backend systems using Python and Python frameworks.'
),

(
    2,
    'Java Developer',
    'Develops enterprise and backend applications using Java technologies.'
),

(
    3,
    'Frontend Developer',
    'Develops user interfaces and web applications using frontend technologies.'
),

(
    4,
    'Data Analyst',
    'Analyzes data and creates business insights using analytics tools.'
),

(
    5,
    'Full Stack Developer',
    'Develops both frontend and backend applications using multiple technology stacks.'
),

(
    6,
    'Backend Developer',
    'Develops server-side applications, APIs, databases and backend systems using different technology stacks.'
);


-- ============================================================
-- SKILL MASTER DATA
-- ============================================================

INSERT INTO skills
(skill_name)
VALUES

('Python'),
('Flask'),
('Django'),
('FastAPI'),
('Java'),
('Spring Boot'),
('Hibernate'),
('JDBC'),
('HTML'),
('CSS'),
('JavaScript'),
('TypeScript'),
('React'),
('Angular'),
('Vue'),
('Node.js'),
('Express'),
('NestJS'),
('C#'),
('.NET'),
('ASP.NET Core'),
('Entity Framework'),
('SQL'),
('MySQL'),
('PostgreSQL'),
('MongoDB'),
('Redis'),
('REST API'),
('GraphQL'),
('Git'),
('GitHub'),
('Docker'),
('Kubernetes'),
('AWS'),
('Azure'),
('Google Cloud'),
('Linux'),
('Excel'),
('Power BI'),
('Tableau'),
('Pandas'),
('NumPy'),
('Statistics'),
('Machine Learning'),
('TensorFlow'),
('PyTorch'),
('Bootstrap'),
('Responsive Design');


-- ============================================================
-- PYTHON DEVELOPER GROUPS
-- ============================================================

INSERT INTO role_skill_groups
(group_id, role_id, group_name, group_type, description)
VALUES

(
    1,
    1,
    'Python Core',
    'technology',
    'Core Python development skills.'
),

(
    2,
    1,
    'Python Frameworks',
    'specialization',
    'Popular Python backend frameworks.'
),

(
    3,
    1,
    'Common Development',
    'common',
    'Common development and database skills.'
);


-- ============================================================
-- PYTHON DEVELOPER SKILLS
-- ============================================================

INSERT INTO job_role_skills
(role_id, group_id, skill_name, importance, weight)
VALUES

(1, 1, 'Python', 'core', 5.00),

(1, 2, 'Flask', 'supporting', 3.00),
(1, 2, 'Django', 'supporting', 3.00),
(1, 2, 'FastAPI', 'supporting', 3.00),

(1, 3, 'SQL', 'core', 4.00),
(1, 3, 'MySQL', 'supporting', 2.00),
(1, 3, 'Git', 'supporting', 2.00),
(1, 3, 'REST API', 'core', 4.00),
(1, 3, 'Docker', 'optional', 1.00),
(1, 3, 'AWS', 'optional', 1.00);


-- ============================================================
-- JAVA DEVELOPER GROUPS
-- ============================================================

INSERT INTO role_skill_groups
(group_id, role_id, group_name, group_type, description)
VALUES

(
    4,
    2,
    'Java Core',
    'technology',
    'Core Java development skills.'
),

(
    5,
    2,
    'Java Frameworks',
    'specialization',
    'Java backend frameworks and technologies.'
),

(
    6,
    2,
    'Common Development',
    'common',
    'Common database and development skills.'
);


-- ============================================================
-- JAVA DEVELOPER SKILLS
-- ============================================================

INSERT INTO job_role_skills
(role_id, group_id, skill_name, importance, weight)
VALUES

(2, 4, 'Java', 'core', 5.00),

(2, 5, 'Spring Boot', 'supporting', 4.00),
(2, 5, 'Hibernate', 'supporting', 3.00),
(2, 5, 'JDBC', 'supporting', 2.00),

(2, 6, 'SQL', 'core', 4.00),
(2, 6, 'MySQL', 'supporting', 2.00),
(2, 6, 'Git', 'supporting', 2.00),
(2, 6, 'REST API', 'core', 4.00),
(2, 6, 'Docker', 'optional', 1.00),
(2, 6, 'AWS', 'optional', 1.00);


-- ============================================================
-- FRONTEND DEVELOPER GROUPS
-- ============================================================

INSERT INTO role_skill_groups
(group_id, role_id, group_name, group_type, description)
VALUES

(
    7,
    3,
    'Frontend Fundamentals',
    'common',
    'Core web technologies.'
),

(
    8,
    3,
    'Frontend Frameworks',
    'technology',
    'Popular frontend frameworks and libraries.'
);


-- ============================================================
-- FRONTEND DEVELOPER SKILLS
-- ============================================================

INSERT INTO job_role_skills
(role_id, group_id, skill_name, importance, weight)
VALUES

(3, 7, 'HTML', 'core', 4.00),
(3, 7, 'CSS', 'core', 4.00),
(3, 7, 'JavaScript', 'core', 5.00),
(3, 7, 'Responsive Design', 'supporting', 2.00),
(3, 7, 'Git', 'supporting', 2.00),

(3, 8, 'React', 'supporting', 4.00),
(3, 8, 'Angular', 'supporting', 4.00),
(3, 8, 'Vue', 'supporting', 4.00),
(3, 8, 'Bootstrap', 'optional', 1.00);


-- ============================================================
-- DATA ANALYST GROUPS
-- ============================================================

INSERT INTO role_skill_groups
(group_id, role_id, group_name, group_type, description)
VALUES

(
    9,
    4,
    'Data Analysis Core',
    'common',
    'Core data analysis skills.'
),

(
    10,
    4,
    'Data Tools',
    'technology',
    'Tools used for analytics and visualization.'
);


-- ============================================================
-- DATA ANALYST SKILLS
-- ============================================================

INSERT INTO job_role_skills
(role_id, group_id, skill_name, importance, weight)
VALUES

(4, 9, 'SQL', 'core', 5.00),
(4, 9, 'Python', 'supporting', 4.00),
(4, 9, 'Statistics', 'core', 4.00),

(4, 10, 'Pandas', 'supporting', 3.00),
(4, 10, 'NumPy', 'supporting', 2.00),
(4, 10, 'Excel', 'supporting', 3.00),
(4, 10, 'Power BI', 'supporting', 3.00),
(4, 10, 'Tableau', 'supporting', 3.00);


-- ============================================================
-- FULL STACK DEVELOPER GROUPS
-- ============================================================

INSERT INTO role_skill_groups
(group_id, role_id, group_name, group_type, description)
VALUES

(
    11,
    5,
    'Frontend',
    'common',
    'Frontend development capabilities.'
),

(
    12,
    5,
    'Python Backend',
    'technology',
    'Python-based backend stack.'
),

(
    13,
    5,
    'Node.js Backend',
    'technology',
    'Node.js-based backend stack.'
),

(
    14,
    5,
    'Database',
    'common',
    'Database technologies used in full stack development.'
),

(
    15,
    5,
    'Development Tools',
    'common',
    'Common development and deployment tools.'
);


-- ============================================================
-- FULL STACK DEVELOPER SKILLS
-- ============================================================

INSERT INTO job_role_skills
(role_id, group_id, skill_name, importance, weight)
VALUES

-- Frontend

(5, 11, 'HTML', 'core', 3.00),
(5, 11, 'CSS', 'core', 3.00),
(5, 11, 'JavaScript', 'core', 4.00),
(5, 11, 'React', 'supporting', 3.00),
(5, 11, 'Angular', 'supporting', 3.00),
(5, 11, 'Vue', 'supporting', 3.00),

-- Python Backend

(5, 12, 'Python', 'core', 4.00),
(5, 12, 'Flask', 'supporting', 3.00),
(5, 12, 'Django', 'supporting', 3.00),
(5, 12, 'FastAPI', 'supporting', 3.00),

-- Node.js Backend

(5, 13, 'Node.js', 'core', 4.00),
(5, 13, 'Express', 'supporting', 3.00),
(5, 13, 'NestJS', 'supporting', 3.00),
(5, 13, 'TypeScript', 'supporting', 2.00),

-- Database

(5, 14, 'SQL', 'core', 3.00),
(5, 14, 'MySQL', 'supporting', 2.00),
(5, 14, 'PostgreSQL', 'supporting', 2.00),
(5, 14, 'MongoDB', 'supporting', 2.00),

-- Tools

(5, 15, 'REST API', 'core', 3.00),
(5, 15, 'Git', 'supporting', 2.00),
(5, 15, 'Docker', 'optional', 1.00),
(5, 15, 'AWS', 'optional', 1.00);


-- ============================================================
-- BACKEND DEVELOPER GROUPS
-- ============================================================

INSERT INTO role_skill_groups
(group_id, role_id, group_name, group_type, description)
VALUES

(
    16,
    6,
    'Common Backend',
    'common',
    'Backend concepts and technologies common to multiple stacks.'
),

(
    17,
    6,
    'Python Backend',
    'technology',
    'Backend development using Python.'
),

(
    18,
    6,
    'Node.js Backend',
    'technology',
    'Backend development using JavaScript and Node.js.'
),

(
    19,
    6,
    'Java Backend',
    'technology',
    'Backend development using Java.'
),

(
    20,
    6,
    '.NET Backend',
    'technology',
    'Backend development using C# and .NET.'
);


-- ============================================================
-- BACKEND DEVELOPER SKILLS
-- ============================================================

INSERT INTO job_role_skills
(role_id, group_id, skill_name, importance, weight)
VALUES

-- Common Backend

(6, 16, 'REST API', 'core', 5.00),
(6, 16, 'SQL', 'core', 4.00),
(6, 16, 'Git', 'supporting', 2.00),
(6, 16, 'Authentication', 'supporting', 2.00),
(6, 16, 'Docker', 'optional', 1.00),

-- Python Backend

(6, 17, 'Python', 'core', 5.00),
(6, 17, 'Flask', 'supporting', 3.00),
(6, 17, 'Django', 'supporting', 3.00),
(6, 17, 'FastAPI', 'supporting', 3.00),

-- Node.js Backend

(6, 18, 'Node.js', 'core', 5.00),
(6, 18, 'Express', 'supporting', 3.00),
(6, 18, 'NestJS', 'supporting', 3.00),
(6, 18, 'JavaScript', 'supporting', 3.00),
(6, 18, 'TypeScript', 'supporting', 2.00),

-- Java Backend

(6, 19, 'Java', 'core', 5.00),
(6, 19, 'Spring Boot', 'supporting', 4.00),
(6, 19, 'Hibernate', 'supporting', 3.00),
(6, 19, 'JDBC', 'supporting', 2.00),

-- .NET Backend

(6, 20, 'C#', 'core', 5.00),
(6, 20, '.NET', 'core', 4.00),
(6, 20, 'ASP.NET Core', 'supporting', 4.00),
(6, 20, 'Entity Framework', 'supporting', 3.00);


-- ============================================================
-- END OF SCHEMA
-- ============================================================