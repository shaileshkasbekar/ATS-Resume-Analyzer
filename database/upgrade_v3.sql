-- ============================================================
-- UPGRADE V3
--
-- 1. Save skill evidence (used / only listed) with ATS results
-- 2. New table for job description matching
-- 3. Five new job roles
--
-- Safe to run more than once.
-- ============================================================

USE ats_resume_analyzer_v2;


-- ============================================================
-- 1. SKILL EVIDENCE
-- ============================================================

ALTER TABLE resume_results
ADD COLUMN skill_evidence TEXT;


-- ============================================================
-- 2. JOB DESCRIPTION MATCH RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS jd_results (

    jd_result_id INT AUTO_INCREMENT PRIMARY KEY,

    resume_id INT NOT NULL,

    job_title VARCHAR(200),

    job_description MEDIUMTEXT,

    score DECIMAL(5,2),

    keyword_score DECIMAL(5,2),

    ai_relevance DECIMAL(5,2),

    experience_match DECIMAL(5,2),

    -- all lists (skills, strengths, gaps, ...) as JSON
    details MEDIUMTEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (resume_id)
        REFERENCES resumes(resume_id)
        ON DELETE CASCADE
);


-- ============================================================
-- 3. NEW JOB ROLES
-- ============================================================

INSERT IGNORE INTO job_roles (role_name, description) VALUES
('DevOps Engineer', 'Builds and automates CI/CD pipelines, infrastructure and cloud deployments.'),
('Android Developer', 'Builds native or cross-platform Android mobile applications.'),
('Machine Learning Engineer', 'Builds, trains and deploys machine learning models.'),
('Software Tester', 'Tests software manually and with automation to find and track defects.'),
('Data Scientist', 'Analyzes data and builds statistical and machine learning models to answer business questions.');


-- ---------------- DevOps Engineer ----------------

SET @r = (SELECT role_id FROM job_roles WHERE role_name = 'DevOps Engineer');

INSERT IGNORE INTO role_skill_groups (role_id, group_name, group_type) VALUES
(@r, 'DevOps Fundamentals', 'common'),
(@r, 'Orchestration and Monitoring', 'common'),
(@r, 'AWS Cloud', 'technology'),
(@r, 'Azure Cloud', 'technology'),
(@r, 'Google Cloud', 'technology');

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'DevOps Fundamentals');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Linux', 'core', 5), (@r, @g, 'Git', 'core', 4), (@r, @g, 'CI/CD', 'core', 5),
(@r, @g, 'Docker', 'core', 5), (@r, @g, 'Shell Scripting', 'supporting', 3), (@r, @g, 'Networking', 'supporting', 2);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Orchestration and Monitoring');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Kubernetes', 'core', 4), (@r, @g, 'Jenkins', 'supporting', 3), (@r, @g, 'Ansible', 'supporting', 2),
(@r, @g, 'Prometheus', 'optional', 1), (@r, @g, 'Grafana', 'optional', 1);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'AWS Cloud');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'AWS', 'core', 5), (@r, @g, 'Terraform', 'supporting', 3);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Azure Cloud');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Azure', 'core', 5), (@r, @g, 'Terraform', 'supporting', 3);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Google Cloud');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Google Cloud', 'core', 5), (@r, @g, 'Terraform', 'supporting', 3);


-- ---------------- Android Developer ----------------

SET @r = (SELECT role_id FROM job_roles WHERE role_name = 'Android Developer');

INSERT IGNORE INTO role_skill_groups (role_id, group_name, group_type) VALUES
(@r, 'Android Fundamentals', 'common'),
(@r, 'Kotlin Android', 'technology'),
(@r, 'Java Android', 'technology'),
(@r, 'Flutter', 'technology');

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Android Fundamentals');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Android SDK', 'core', 5), (@r, @g, 'REST API', 'supporting', 3), (@r, @g, 'Git', 'supporting', 2),
(@r, @g, 'Firebase', 'supporting', 2), (@r, @g, 'SQLite', 'supporting', 2);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Kotlin Android');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Kotlin', 'core', 5), (@r, @g, 'Jetpack Compose', 'supporting', 3), (@r, @g, 'Coroutines', 'supporting', 2);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Java Android');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Java', 'core', 5), (@r, @g, 'XML', 'supporting', 3);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Flutter');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Flutter', 'core', 5), (@r, @g, 'Dart', 'core', 4);


-- ---------------- Machine Learning Engineer ----------------

SET @r = (SELECT role_id FROM job_roles WHERE role_name = 'Machine Learning Engineer');

INSERT IGNORE INTO role_skill_groups (role_id, group_name, group_type) VALUES
(@r, 'ML Fundamentals', 'common'),
(@r, 'MLOps and Tools', 'common'),
(@r, 'PyTorch', 'technology'),
(@r, 'TensorFlow', 'technology'),
(@r, 'Classical ML', 'technology');

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'ML Fundamentals');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Python', 'core', 5), (@r, @g, 'Machine Learning', 'core', 5), (@r, @g, 'Statistics', 'supporting', 3),
(@r, @g, 'NumPy', 'supporting', 2), (@r, @g, 'Pandas', 'supporting', 2), (@r, @g, 'SQL', 'supporting', 2);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'MLOps and Tools');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Git', 'supporting', 2), (@r, @g, 'Docker', 'optional', 1), (@r, @g, 'MLflow', 'optional', 1),
(@r, @g, 'FastAPI', 'optional', 1);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'PyTorch');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'PyTorch', 'core', 5), (@r, @g, 'Deep Learning', 'supporting', 3);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'TensorFlow');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'TensorFlow', 'core', 5), (@r, @g, 'Keras', 'supporting', 3), (@r, @g, 'Deep Learning', 'supporting', 3);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Classical ML');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Scikit-learn', 'core', 5), (@r, @g, 'XGBoost', 'supporting', 2);


-- ---------------- Software Tester ----------------

SET @r = (SELECT role_id FROM job_roles WHERE role_name = 'Software Tester');

INSERT IGNORE INTO role_skill_groups (role_id, group_name, group_type) VALUES
(@r, 'Testing Fundamentals', 'common'),
(@r, 'Selenium with Java', 'technology'),
(@r, 'Selenium with Python', 'technology'),
(@r, 'JavaScript Testing', 'technology');

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Testing Fundamentals');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Manual Testing', 'core', 5), (@r, @g, 'Test Cases', 'core', 4), (@r, @g, 'SDLC', 'supporting', 3),
(@r, @g, 'Bug Tracking', 'supporting', 3), (@r, @g, 'API Testing', 'supporting', 3), (@r, @g, 'SQL', 'supporting', 2);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Selenium with Java');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Selenium', 'core', 5), (@r, @g, 'Java', 'supporting', 3), (@r, @g, 'TestNG', 'supporting', 3);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Selenium with Python');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Selenium', 'core', 5), (@r, @g, 'Python', 'supporting', 3), (@r, @g, 'Pytest', 'supporting', 3);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'JavaScript Testing');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Cypress', 'core', 5), (@r, @g, 'Playwright', 'supporting', 4), (@r, @g, 'JavaScript', 'supporting', 3);


-- ---------------- Data Scientist ----------------

SET @r = (SELECT role_id FROM job_roles WHERE role_name = 'Data Scientist');

INSERT IGNORE INTO role_skill_groups (role_id, group_name, group_type) VALUES
(@r, 'Data Science Core', 'common'),
(@r, 'Visualization and Tools', 'common'),
(@r, 'Classical ML', 'technology'),
(@r, 'Deep Learning', 'technology');

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Data Science Core');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Python', 'core', 5), (@r, @g, 'Statistics', 'core', 5), (@r, @g, 'Machine Learning', 'core', 5),
(@r, @g, 'SQL', 'supporting', 3), (@r, @g, 'Pandas', 'supporting', 3), (@r, @g, 'NumPy', 'supporting', 2);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Visualization and Tools');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Matplotlib', 'supporting', 2), (@r, @g, 'Seaborn', 'supporting', 2), (@r, @g, 'Jupyter', 'supporting', 2),
(@r, @g, 'Git', 'optional', 1);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Classical ML');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Scikit-learn', 'core', 5), (@r, @g, 'XGBoost', 'supporting', 2);

SET @g = (SELECT group_id FROM role_skill_groups WHERE role_id = @r AND group_name = 'Deep Learning');
INSERT IGNORE INTO job_role_skills (role_id, group_id, skill_name, importance, weight) VALUES
(@r, @g, 'Deep Learning', 'core', 4), (@r, @g, 'TensorFlow', 'supporting', 3), (@r, @g, 'PyTorch', 'supporting', 3);
