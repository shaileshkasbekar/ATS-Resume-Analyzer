-- ============================================================
-- FIX ROLE SKILL GROUPS
--
-- 1. "Python Core" and "Java Core" are required skills,
--    not alternative technology paths -> make them common.
--
-- 2. Django / Flask / FastAPI are alternatives, so each one
--    becomes its own technology path for Python Developer.
-- ============================================================

USE ats_resume_analyzer_v2;


-- 1. Core language groups become common requirements

UPDATE role_skill_groups
SET group_type = 'common'
WHERE group_name IN ('Python Core', 'Java Core');


-- 2. One technology path per Python framework

INSERT IGNORE INTO role_skill_groups (role_id, group_name, group_type)
SELECT role_id, 'Django', 'technology'
FROM job_roles WHERE role_name = 'Python Developer';

INSERT IGNORE INTO role_skill_groups (role_id, group_name, group_type)
SELECT role_id, 'Flask', 'technology'
FROM job_roles WHERE role_name = 'Python Developer';

INSERT IGNORE INTO role_skill_groups (role_id, group_name, group_type)
SELECT role_id, 'FastAPI', 'technology'
FROM job_roles WHERE role_name = 'Python Developer';

UPDATE job_role_skills jrs
JOIN job_roles jr
    ON jr.role_id = jrs.role_id
    AND jr.role_name = 'Python Developer'
JOIN role_skill_groups g
    ON g.role_id = jrs.role_id
    AND g.group_name = jrs.skill_name
SET jrs.group_id = g.group_id,
    jrs.importance = 'core',
    jrs.weight = 5.00
WHERE jrs.skill_name IN ('Django', 'Flask', 'FastAPI');

DELETE g
FROM role_skill_groups g
JOIN job_roles jr
    ON jr.role_id = g.role_id
    AND jr.role_name = 'Python Developer'
WHERE g.group_name = 'Python Frameworks';


-- 3. Spring Boot is the main Java framework

UPDATE job_role_skills jrs
JOIN job_roles jr
    ON jr.role_id = jrs.role_id
    AND jr.role_name = 'Java Developer'
SET jrs.importance = 'core'
WHERE jrs.skill_name = 'Spring Boot';
