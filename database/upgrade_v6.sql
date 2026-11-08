-- ============================================================
-- UPGRADE V6 - application tracker, share links, reminders
--
-- Only ADDS tables and columns. No data is changed or deleted.
-- Safe to run more than once.
-- ============================================================

USE ats_resume_analyzer_v2;


-- Job application tracker

CREATE TABLE IF NOT EXISTS applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    company VARCHAR(200) NOT NULL,
    job_title VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'saved',
    applied_on DATE NULL,
    interview_on DATE NULL,
    job_url VARCHAR(500),
    notes TEXT,
    version_id INT NULL,
    saved_job_id INT NULL,
    jd_result_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);


-- Read-only share link for one job match result (NULL = not shared)

ALTER TABLE jd_results ADD COLUMN share_token VARCHAR(64) NULL;

ALTER TABLE jd_results ADD UNIQUE INDEX share_token_unique (share_token);


-- Weekly learning-roadmap reminder e-mails (off unless the user turns them on)

ALTER TABLE users ADD COLUMN reminders_enabled BOOLEAN DEFAULT 0;

ALTER TABLE users ADD COLUMN last_reminder_at TIMESTAMP NULL;
