-- =========================================================
-- Upgrade v7: Agentic AI (Career Agent)
--
-- Only ADDS three new tables. Existing tables are not changed.
-- Safe to run more than once.
--
--   venv\Scripts\python.exe database\run_sql.py database\upgrade_v7.sql
-- =========================================================

USE ats_resume_analyzer_v2;


-- One row per agent run: the user's goal, the plan the planner chose,
-- the final answer and everything the agents produced (JSON).

CREATE TABLE IF NOT EXISTS agent_runs (
    run_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    goal TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    plan TEXT,
    final_answer MEDIUMTEXT,
    result MEDIUMTEXT,
    error TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);


-- Execution trace: every planner decision, LLM call, tool call and error.

CREATE TABLE IF NOT EXISTS agent_steps (
    step_id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL,
    step_no INT NOT NULL,
    agent VARCHAR(50) NOT NULL,
    kind VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    input_data MEDIUMTEXT,
    output_data MEDIUMTEXT,
    ok BOOLEAN DEFAULT 1,
    duration_ms INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES agent_runs(run_id) ON DELETE CASCADE
);


-- Long-term memory: career facts about the user that agents recall
-- in later runs (target role, skills, gaps, goals).

CREATE TABLE IF NOT EXISTS agent_memory (
    memory_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    mem_key VARCHAR(50) NOT NULL,
    mem_value TEXT NOT NULL,
    source VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY user_memory_key (user_id, mem_key),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
