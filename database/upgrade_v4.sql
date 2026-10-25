-- ============================================================
-- UPGRADE V4 - Job Match (Phase 1)
--
-- Only ADDS columns. No data is changed or deleted.
-- Safe to run more than once.
-- ============================================================

USE ats_resume_analyzer_v2;

ALTER TABLE jd_results ADD COLUMN company_name VARCHAR(200);

ALTER TABLE jd_results ADD COLUMN source_type VARCHAR(30);

ALTER TABLE jd_results ADD COLUMN role_id INT NULL;

ALTER TABLE jd_results ADD COLUMN scoring_version VARCHAR(20);

-- Extracted job requirements as JSON
ALTER TABLE jd_results ADD COLUMN requirements MEDIUMTEXT;
