-- ============================================================
-- UPGRADE V5 - Phases 2, 3 and 4
--
-- Only ADDS tables and columns. No data is changed or deleted.
-- Safe to run more than once.
-- ============================================================

USE ats_resume_analyzer_v2;


-- ------------------------------------------------------------
-- Resume versions (labelled resumes that can be reused)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS resume_versions (
    version_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    label VARCHAR(100) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    resume_text MEDIUMTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

ALTER TABLE resumes ADD COLUMN version_id INT NULL;


-- ------------------------------------------------------------
-- Saved job descriptions
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS saved_jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200),
    company VARCHAR(200),
    description MEDIUMTEXT NOT NULL,
    requirements MEDIUMTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

ALTER TABLE jd_results ADD COLUMN saved_job_id INT NULL;

ALTER TABLE jd_results ADD COLUMN version_id INT NULL;


-- ------------------------------------------------------------
-- AI resume improvement suggestions (accept / reject)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS resume_suggestions (
    suggestion_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    jd_result_id INT NOT NULL,
    kind VARCHAR(30),
    original TEXT,
    improved TEXT,
    reason TEXT,
    requirement VARCHAR(200),
    evidence TEXT,
    needs_metric BOOLEAN DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (jd_result_id) REFERENCES jd_results(jd_result_id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
-- Generated content per job match (projects, interview questions)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS generated_content (
    content_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    jd_result_id INT NOT NULL,
    kind VARCHAR(30) NOT NULL,
    content MEDIUMTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (jd_result_id, kind),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (jd_result_id) REFERENCES jd_results(jd_result_id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
-- Learning roadmap with progress
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS roadmap_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    jd_result_id INT NOT NULL,
    skill VARCHAR(100) NOT NULL,
    priority VARCHAR(20),
    why TEXT,
    objectives TEXT,
    exercises TEXT,
    project_extension TEXT,
    demonstrate TEXT,
    resource_name VARCHAR(200),
    resource_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'todo',
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (jd_result_id, skill),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (jd_result_id) REFERENCES jd_results(jd_result_id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
-- Mock interview answers + feedback
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS interview_answers (
    answer_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    jd_result_id INT NOT NULL,
    question_index INT NOT NULL,
    question TEXT,
    answer TEXT,
    feedback MEDIUMTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (jd_result_id) REFERENCES jd_results(jd_result_id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
-- Scoring versions and quality issues for older result types
-- ------------------------------------------------------------

ALTER TABLE resume_results ADD COLUMN scoring_version VARCHAR(20);

ALTER TABLE general_results ADD COLUMN scoring_version VARCHAR(20);

ALTER TABLE general_results ADD COLUMN experience_level VARCHAR(20);

ALTER TABLE general_results ADD COLUMN issues MEDIUMTEXT;
