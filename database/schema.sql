-- ============================================================
-- ATS RESUME ANALYZER - DATABASE SCHEMA
--
-- Fresh setup (run from the project folder):
--   venv\Scripts\python.exe database\run_sql.py database\schema.sql
--   venv\Scripts\python.exe database\run_sql.py database\upgrade_v3.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS ats_resume_analyzer_v2;

USE ats_resume_analyzer_v2;

-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE IF NOT EXISTS `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `full_name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- RESUMES
-- ============================================================

CREATE TABLE IF NOT EXISTS `resumes` (
  `resume_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `file_path` varchar(500) NOT NULL,
  `upload_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`resume_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `resumes_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- JOB_ROLES
-- ============================================================

CREATE TABLE IF NOT EXISTS `job_roles` (
  `role_id` int NOT NULL AUTO_INCREMENT,
  `role_name` varchar(100) NOT NULL,
  `description` text,
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- SKILLS
-- ============================================================

CREATE TABLE IF NOT EXISTS `skills` (
  `skill_id` int NOT NULL AUTO_INCREMENT,
  `skill_name` varchar(100) NOT NULL,
  PRIMARY KEY (`skill_id`),
  UNIQUE KEY `skill_name` (`skill_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- ROLE_SKILL_GROUPS
-- ============================================================

CREATE TABLE IF NOT EXISTS `role_skill_groups` (
  `group_id` int NOT NULL AUTO_INCREMENT,
  `role_id` int NOT NULL,
  `group_name` varchar(100) NOT NULL,
  `group_type` enum('common','technology','specialization') DEFAULT 'technology',
  `description` text,
  PRIMARY KEY (`group_id`),
  UNIQUE KEY `role_id` (`role_id`,`group_name`),
  CONSTRAINT `role_skill_groups_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `job_roles` (`role_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- JOB_ROLE_SKILLS
-- ============================================================

CREATE TABLE IF NOT EXISTS `job_role_skills` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_id` int NOT NULL,
  `skill_name` varchar(100) NOT NULL,
  `group_id` int DEFAULT NULL,
  `importance` enum('core','supporting','optional') DEFAULT 'supporting',
  `weight` decimal(5,2) DEFAULT '1.00',
  PRIMARY KEY (`id`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `job_role_skills_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `job_roles` (`role_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- RESUME_RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS `resume_results` (
  `result_id` int NOT NULL AUTO_INCREMENT,
  `resume_id` int NOT NULL,
  `role_id` int NOT NULL,
  `ats_score` decimal(5,2) DEFAULT NULL,
  `matched_skills` text,
  `missing_skills` text,
  `recommended_skills` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `technology_path` varchar(150) DEFAULT NULL,
  `ai_relevance` decimal(5,2) DEFAULT NULL,
  `experience_relevance` decimal(5,2) DEFAULT NULL,
  `project_relevance` decimal(5,2) DEFAULT NULL,
  `semantic_matches` text,
  `strengths` text,
  `weaknesses` text,
  `ai_recommendations` text,
  PRIMARY KEY (`result_id`),
  KEY `resume_id` (`resume_id`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `resume_results_ibfk_1` FOREIGN KEY (`resume_id`) REFERENCES `resumes` (`resume_id`) ON DELETE CASCADE,
  CONSTRAINT `resume_results_ibfk_2` FOREIGN KEY (`role_id`) REFERENCES `job_roles` (`role_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- GENERAL_RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS `general_results` (
  `general_result_id` int NOT NULL AUTO_INCREMENT,
  `resume_id` int NOT NULL,
  `score` decimal(5,2) DEFAULT NULL,
  `email_detected` tinyint(1) DEFAULT NULL,
  `phone_detected` tinyint(1) DEFAULT NULL,
  `word_count` int DEFAULT NULL,
  `skills` text,
  `sections` text,
  `recommendations` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `linkedin_detected` tinyint(1) DEFAULT '0',
  `github_detected` tinyint(1) DEFAULT '0',
  `ai_quality` decimal(5,2) DEFAULT NULL,
  `summary_quality` decimal(5,2) DEFAULT NULL,
  `experience_quality` decimal(5,2) DEFAULT NULL,
  `project_quality` decimal(5,2) DEFAULT NULL,
  `skills_quality` decimal(5,2) DEFAULT NULL,
  `clarity_quality` decimal(5,2) DEFAULT NULL,
  `ai_strengths` text,
  `ai_weaknesses` text,
  `ai_recommendations` text,
  PRIMARY KEY (`general_result_id`),
  KEY `resume_id` (`resume_id`),
  CONSTRAINT `general_results_ibfk_1` FOREIGN KEY (`resume_id`) REFERENCES `resumes` (`resume_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================
-- DEFAULT JOB ROLES AND SKILLS
-- ============================================================

INSERT IGNORE INTO job_roles (role_id, role_name, description) VALUES
(1, 'Python Developer', 'Develops Python applications'),
(2, 'Java Developer', 'Java Backend Development'),
(3, 'Frontend Developer', 'Frontend Web Development'),
(4, 'Data Analyst', 'Data Analysis'),
(5, 'Full Stack Developer', 'Full Stack Web Development'),
(6, 'Backend Developer', 'Develops server-side applications, APIs, databases and backend systems using different technology stacks.');

INSERT IGNORE INTO role_skill_groups (group_id, role_id, group_name, group_type, description) VALUES
(1, 6, 'Common Backend', 'common', 'Skills commonly used across backend development stacks.'),
(2, 6, 'Python Backend', 'technology', 'Backend development using Python technologies.'),
(3, 6, 'Node.js Backend', 'technology', 'Backend development using Node.js technologies.'),
(4, 6, 'Java Backend', 'technology', 'Backend development using Java technologies.'),
(5, 6, '.NET Backend', 'technology', 'Backend development using C# and .NET technologies.'),
(6, 1, 'Python Core', 'common', 'Core Python programming skills.'),
(8, 1, 'Database and API', 'common', 'Database and API skills used in Python development.'),
(9, 1, 'Development Tools', 'common', 'Tools and technologies commonly used in development.'),
(10, 2, 'Java Core', 'common', 'Core Java programming skills.'),
(11, 2, 'Java Frameworks', 'technology', 'Java frameworks and enterprise technologies.'),
(12, 2, 'Database and API', 'common', 'Database and API skills used in Java development.'),
(13, 2, 'Development Tools', 'common', 'Tools and technologies commonly used in Java development.'),
(14, 3, 'Frontend Fundamentals', 'common', 'Core web technologies required for frontend development.'),
(15, 3, 'React', 'technology', 'Frontend development using React.'),
(16, 3, 'Angular', 'technology', 'Frontend development using Angular.'),
(17, 3, 'Vue', 'technology', 'Frontend development using Vue.'),
(18, 3, 'Frontend Tools', 'common', 'Common frontend development tools and practices.'),
(19, 4, 'Data Analysis Core', 'common', 'Core skills required for data analysis.'),
(20, 4, 'Python Analytics', 'technology', 'Data analysis using Python and its ecosystem.'),
(21, 4, 'Business Intelligence', 'technology', 'Business intelligence and reporting tools.'),
(22, 4, 'Data Visualization', 'technology', 'Tools used for data visualization and reporting.'),
(23, 4, 'Data Tools', 'common', 'Common tools used in data analysis workflows.'),
(24, 5, 'Frontend Core', 'common', 'Core frontend technologies used in full stack development.'),
(25, 5, 'React Frontend', 'technology', 'Full stack development using React for the frontend.'),
(26, 5, 'Angular Frontend', 'technology', 'Full stack development using Angular for the frontend.'),
(27, 5, 'Python Backend', 'technology', 'Full stack development using Python backend technologies.'),
(28, 5, 'Node.js Backend', 'technology', 'Full stack development using Node.js backend technologies.'),
(29, 5, 'Java Backend', 'technology', 'Full stack development using Java backend technologies.'),
(30, 5, 'Database', 'common', 'Database technologies used in full stack applications.'),
(31, 5, 'Development and Deployment', 'common', 'Common development, API and deployment technologies.'),
(35, 1, 'Django', 'technology', NULL),
(36, 1, 'Flask', 'technology', NULL),
(37, 1, 'FastAPI', 'technology', NULL);

INSERT IGNORE INTO job_role_skills (id, role_id, skill_name, group_id, importance, weight) VALUES
(34, 6, 'REST API', 1, 'core', '5.00'),
(35, 6, 'SQL', 1, 'core', '4.00'),
(36, 6, 'Git', 1, 'supporting', '2.00'),
(37, 6, 'Authentication', 1, 'supporting', '2.00'),
(38, 6, 'Docker', 1, 'optional', '1.00'),
(39, 6, 'Python', 2, 'core', '5.00'),
(40, 6, 'Flask', 2, 'supporting', '3.00'),
(41, 6, 'Django', 2, 'supporting', '3.00'),
(42, 6, 'FastAPI', 2, 'supporting', '3.00'),
(43, 6, 'Node.js', 3, 'core', '5.00'),
(44, 6, 'Express', 3, 'supporting', '3.00'),
(45, 6, 'NestJS', 3, 'supporting', '3.00'),
(46, 6, 'JavaScript', 3, 'supporting', '3.00'),
(47, 6, 'TypeScript', 3, 'supporting', '2.00'),
(48, 6, 'Java', 4, 'core', '5.00'),
(49, 6, 'Spring Boot', 4, 'supporting', '4.00'),
(50, 6, 'Hibernate', 4, 'supporting', '3.00'),
(51, 6, 'JDBC', 4, 'supporting', '2.00'),
(52, 6, 'C#', 5, 'core', '5.00'),
(53, 6, '.NET', 5, 'core', '4.00'),
(54, 6, 'ASP.NET Core', 5, 'supporting', '4.00'),
(55, 6, 'Entity Framework', 5, 'supporting', '3.00'),
(56, 1, 'Python', 6, 'core', '5.00'),
(57, 1, 'Flask', 36, 'core', '5.00'),
(58, 1, 'Django', 35, 'core', '5.00'),
(59, 1, 'FastAPI', 37, 'core', '5.00'),
(60, 1, 'SQL', 8, 'core', '4.00'),
(61, 1, 'MySQL', 8, 'supporting', '2.00'),
(62, 1, 'PostgreSQL', 8, 'supporting', '2.00'),
(63, 1, 'REST API', 8, 'core', '4.00'),
(64, 1, 'Git', 9, 'supporting', '2.00'),
(65, 1, 'Docker', 9, 'optional', '1.00'),
(66, 1, 'AWS', 9, 'optional', '1.00'),
(67, 1, 'Linux', 9, 'supporting', '2.00'),
(68, 2, 'Java', 10, 'core', '5.00'),
(69, 2, 'Spring Boot', 11, 'core', '4.00'),
(70, 2, 'Hibernate', 11, 'supporting', '3.00'),
(71, 2, 'JDBC', 11, 'supporting', '2.00'),
(72, 2, 'SQL', 12, 'core', '4.00'),
(73, 2, 'MySQL', 12, 'supporting', '2.00'),
(74, 2, 'PostgreSQL', 12, 'supporting', '2.00'),
(75, 2, 'REST API', 12, 'core', '4.00'),
(76, 2, 'Git', 13, 'supporting', '2.00'),
(77, 2, 'Docker', 13, 'optional', '1.00'),
(78, 2, 'AWS', 13, 'optional', '1.00'),
(79, 2, 'Linux', 13, 'supporting', '2.00'),
(80, 3, 'HTML', 14, 'core', '4.00'),
(81, 3, 'CSS', 14, 'core', '4.00'),
(82, 3, 'JavaScript', 14, 'core', '5.00'),
(83, 3, 'Responsive Design', 14, 'supporting', '2.00'),
(84, 3, 'React', 15, 'core', '5.00'),
(85, 3, 'Angular', 16, 'core', '5.00'),
(86, 3, 'Vue', 17, 'core', '5.00'),
(87, 3, 'Git', 18, 'supporting', '2.00'),
(88, 3, 'Bootstrap', 18, 'optional', '1.00'),
(89, 3, 'REST API', 18, 'supporting', '2.00'),
(90, 3, 'TypeScript', 18, 'supporting', '3.00'),
(91, 4, 'SQL', 19, 'core', '5.00'),
(92, 4, 'Statistics', 19, 'core', '5.00'),
(93, 4, 'Python', 20, 'supporting', '4.00'),
(94, 4, 'Pandas', 20, 'supporting', '4.00'),
(95, 4, 'NumPy', 20, 'supporting', '3.00'),
(96, 4, 'Excel', 21, 'supporting', '4.00'),
(97, 4, 'Power BI', 21, 'supporting', '4.00'),
(98, 4, 'Tableau', 22, 'supporting', '4.00'),
(99, 4, 'Power BI', 22, 'supporting', '3.00'),
(100, 4, 'Git', 23, 'optional', '1.00'),
(101, 4, 'MySQL', 23, 'supporting', '2.00'),
(102, 5, 'HTML', 24, 'core', '4.00'),
(103, 5, 'CSS', 24, 'core', '4.00'),
(104, 5, 'JavaScript', 24, 'core', '5.00'),
(105, 5, 'React', 25, 'core', '5.00'),
(106, 5, 'Angular', 26, 'core', '5.00'),
(107, 5, 'Python', 27, 'core', '4.00'),
(108, 5, 'Flask', 27, 'supporting', '3.00'),
(109, 5, 'Django', 27, 'supporting', '3.00'),
(110, 5, 'FastAPI', 27, 'supporting', '3.00'),
(111, 5, 'Node.js', 28, 'core', '4.00'),
(112, 5, 'Express', 28, 'supporting', '3.00'),
(113, 5, 'NestJS', 28, 'supporting', '3.00'),
(114, 5, 'TypeScript', 28, 'supporting', '2.00'),
(115, 5, 'Java', 29, 'core', '4.00'),
(116, 5, 'Spring Boot', 29, 'supporting', '3.00'),
(117, 5, 'Hibernate', 29, 'supporting', '2.00'),
(118, 5, 'SQL', 30, 'core', '4.00'),
(119, 5, 'MySQL', 30, 'supporting', '2.00'),
(120, 5, 'PostgreSQL', 30, 'supporting', '2.00'),
(121, 5, 'MongoDB', 30, 'supporting', '2.00'),
(122, 5, 'REST API', 31, 'core', '4.00'),
(123, 5, 'Git', 31, 'supporting', '2.00'),
(124, 5, 'Docker', 31, 'optional', '1.00'),
(125, 5, 'AWS', 31, 'optional', '1.00');
