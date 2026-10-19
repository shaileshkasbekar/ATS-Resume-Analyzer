# ATS Resume Analyzer

An AI-powered web app that checks how well a resume fits a job, the way an Applicant Tracking System (ATS) would, and then tells the candidate exactly what to fix and what to learn.

It combines a **rule-based scoring engine** (skill matching, weights, technology paths, evidence) with an **LLM review** (Groq), so scores are explainable and not just an AI guess.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Flask](https://img.shields.io/badge/Flask-3.1-black)
![MySQL](https://img.shields.io/badge/MySQL-8-orange)
![Groq](https://img.shields.io/badge/AI-Groq-purple)

---

## Features

### 🎯 ATS analysis for a job role
- 11 job roles (Backend, Frontend, Full Stack, Java, Python, Data Analyst, Data Scientist, ML Engineer, DevOps, Android, Software Tester)
- **Technology paths**: a Java backend developer is not penalized for not knowing Node.js — the engine detects the candidate's strongest path and scores against it
- **Skill evidence**: skills used in projects or experience get full credit; skills that are only listed get partial credit
- Weighted core / supporting / optional skills, per-group breakdown
- Hybrid score: rule-based engine + AI relevance, experience and project review

### 🤝 Job description match
- Paste any real job posting (LinkedIn, Naukri, company site)
- AI extracts must-have and nice-to-have skills; the code then verifies each one in the resume itself
- Match score, missing skills, **keywords to add**, and a **professional summary rewritten for that job**

### 🎓 Learning plan
- For every missing skill: steps to learn it, a free official resource, a project idea that proves it on a resume, and a time estimate
- Ordered by importance (must-have first)

### ✍️ General resume check
- Section detection from real headings (Education, Experience, Projects, Skills, …)
- Contact info, LinkedIn / GitHub, length
- **Writing quality**: numbers that show impact, action verbs, weak phrases ("responsible for"), personal pronouns
- AI review of summary, experience, projects, skills and clarity

### 📊 Dashboard and history
- Average and best scores, all past analyses with search and filter
- Responsive UI with automatic dark mode

---

## How the ATS score works

```
Resume PDF ──► text (PyMuPDF) ──► sections (headings) ──► skills + evidence
                                                              │
            Role skills (MySQL: groups, weights, paths) ──────┤
                                                              ▼
                                               Rule-based engine
                                    common skills 40%  +  best technology path 60%
                                                              │
                         AI review (Groq) ────────────────────┤
                                                              ▼
       Final score = rule 40% + AI relevance 25% + experience 15% + projects 10% + path strength 10%
```

If the AI is unavailable, the app still works and shows the rule-based score.

---

## Tech stack

| Layer     | Tools |
|-----------|-------|
| Backend   | Python, Flask (blueprints) |
| Database  | MySQL (`mysql-connector-python`) |
| PDF       | PyMuPDF |
| AI        | Groq API (`openai/gpt-oss-20b`) |
| Frontend  | Jinja2 templates, CSS (no framework), vanilla JavaScript |

---

## Project structure

```
ATS_Resume_Analyzer/
├── app.py                    # Flask app, registers blueprints
├── config.py                 # Settings loaded from .env
├── database/
│   ├── schema.sql            # Tables + default roles and skills
│   ├── upgrade_v3.sql        # Skill evidence, job match table, 5 more roles
│   └── run_sql.py            # Runs a .sql file using the .env settings
├── models/database.py        # MySQL connection
├── resume_parser/
│   ├── pdf_reader.py         # PDF -> text
│   ├── sections.py           # Splits a resume into sections by heading
│   ├── skill_extractor.py    # Skill matching, aliases, evidence
│   ├── ats_score.py          # Rule-based ATS engine
│   ├── ai_client.py          # Groq client + safe JSON parsing
│   ├── ai_analyzer.py        # AI review for a job role
│   ├── jd_analyzer.py        # Job description matching
│   ├── general_analyzer.py   # General checks + writing quality
│   ├── general_ai_analyzer.py
│   └── recommendation.py     # Learning plan for missing skills
├── routes/                   # auth, dashboard, upload, job_match, general_analyzer, history
├── templates/                # Jinja2 pages (base.html + pages)
└── static/                   # app.css, script.js, uploads/
```

---

## Setup (Windows)

**Requirements:** Python 3.10+, MySQL 8, a free [Groq API key](https://console.groq.com/keys).

1. **Clone and install**
   ```
   git clone https://github.com/shaileshkasbekar/ATS-Resume-Analyzer.git
   cd ATS-Resume-Analyzer
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   ```

2. **Settings** — copy `.env.example` to `.env` and fill in your Groq key, a secret key and your MySQL password.
   ```
   copy .env.example .env
   ```

3. **Database** — creates the database, tables and job roles:
   ```
   venv\Scripts\python.exe database\run_sql.py database\schema.sql
   venv\Scripts\python.exe database\run_sql.py database\upgrade_v3.sql
   ```

4. **Run**
   ```
   venv\Scripts\python.exe app.py
   ```
   Open http://127.0.0.1:5000, register an account and upload a resume (text-based PDF, max 5 MB).

On macOS / Linux use `venv/bin/python` instead of `venv\Scripts\python.exe`.

---

## Adding a job role

Roles live in the database, not in code. Add a row to `job_roles`, its skill groups to `role_skill_groups`
(`common` = required for everyone, `technology` = alternative paths) and its skills to `job_role_skills`
with an importance (`core`, `supporting`, `optional`) and a weight. See `database/upgrade_v3.sql` for examples.
New skills are detected automatically.

---

## Author

**Shailesh Kasbekar** — [GitHub](https://github.com/shaileshkasbekar)
