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

### 🤝 Job description match (primary feature)
- Paste a job posting, upload it as PDF/TXT, or pick a predefined role
- Requirements extracted into mandatory / preferred skills (with "A or B" alternatives), experience, education, certifications, responsibilities and soft skills
- Every requirement is labelled exact / alias / semantic / missing, with the resume line that proves it
- **Job Match Score** with every component and every lost point explained (versioned formula in `resume_parser/scoring_config.py`)
- AI output is validated: requirements must appear in the posting, evidence quotes must appear in the resume, and instructions hidden inside documents are ignored

### ✨ AI resume improvement assistant
- Rewrite suggestions for the summary, experience and project bullets, aimed at the target job
- Each shows the original, the improved version (editable), the reason, the job requirement and the evidence
- Accept or reject each suggestion; the original resume is never changed
- Guard rails in code: the original must exist in the resume, rewrites cannot add skills the bullet never had, invented numbers become **[add real number]**

### 📄 Job-specific optimized resume
- Builds a tailored resume from your resume + accepted suggestions
- Templates: Classic, Modern, Technical, Fresher — one column, standard headings, selectable text
- Preview, download as PDF, or save as a new resume version

### 🗂️ Resume versions, saved jobs, multi-job comparison
- Keep labelled resume versions; compare two versions side by side (skills added/removed, changed bullets)
- Against a saved job, see **which edits changed the score and by how much**
- Save job descriptions once (requirements extracted and stored), edit, reuse, and compare one resume against several jobs: common skills, gaps shared by several jobs, suggested roles

### 🎓 Learning roadmap, project ideas, mock interview
- Roadmap from missing requirements (required first) with objectives, exercises, project extensions and progress tracking
- Project recommendations that prove missing skills and avoid duplicating existing projects
- Mock interview: technical, project, skill, behavioral and HR questions, answer feedback (relevance, correctness, clarity, completeness, examples), optional voice input

### ✍️ Resume quality check
- Section detection from real headings, contact info, LinkedIn / GitHub, length
- Writing quality: impact numbers, action verbs, weak phrases, pronouns, repetition, vague bullets
- Adapts to experience level (freshers are not penalized for no work history)
- **Confirmed vs potential issues**, including PDF reading problems (unreadable icons, multi-column layouts)

### 📊 Dashboard, history and reports
- Real statistics and charts: job match history, most frequently missing skills, skills demonstrated vs required, roadmap progress
- History with search, filters (type, role/job), sorting and pagination
- Professional **PDF reports** for every analysis and the learning roadmap

### 🔒 Security
- Password hashing, login rate limiting, CSRF protection on every form, secure session cookies
- Every record is checked against the logged-in user; resumes are stored outside the public folder
- File type checks (real PDF signature), size limit, safe handling of broken PDFs
- Uploaded documents are treated as untrusted: instructions inside them are ignored and AI output is validated

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
├── app.py                    # Flask app, registers blueprints, error pages
├── config.py                 # Settings loaded from .env
├── security.py               # CSRF, rate limiting, session settings, login_required
├── pdf_export.py             # HTML -> PDF (PyMuPDF) for reports and resumes
├── database/
│   ├── schema.sql            # Tables + default roles and skills
│   ├── upgrade_v3.sql … v5   # Non-destructive upgrades (only add tables/columns)
│   └── run_sql.py            # Runs a .sql file using the .env settings
├── models/
│   ├── database.py           # MySQL connection
│   └── repository.py         # Owner-checked queries for the newer features
├── resume_parser/
│   ├── pdf_reader.py         # PDF -> text
│   ├── sections.py           # Splits a resume into sections by heading
│   ├── skill_extractor.py    # Skill matching, aliases, evidence
│   ├── job_requirements.py   # Job description -> structured requirements
│   ├── job_matcher.py        # Job Match engine + explainable score
│   ├── scoring_config.py     # Score weights and version (edit to tune)
│   ├── ai_client.py          # Groq client, JSON mode, untrusted-input rules
│   ├── ai_validation.py      # Validation of AI output (quotes, scores, lists)
│   ├── improvement.py        # Resume improvement assistant
│   ├── resume_builder.py     # Optimized resume + templates
│   ├── version_compare.py    # Resume version comparison
│   ├── multi_job.py          # One resume vs several jobs
│   ├── career.py             # Roadmap, project ideas, mock interview
│   ├── ats_score.py          # Rule-based ATS engine for predefined roles
│   ├── general_analyzer.py   # Quality checks, experience level, issues
│   └── recommendation.py     # Learning resources per skill
├── routes/                   # one blueprint per feature
├── templates/                # Jinja2 pages, reports/ for PDF layouts
├── tests/                    # pytest suite (fake AI + temporary database)
└── uploads/                  # private resume storage (not served publicly)
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
   venv\Scripts\python.exe database\run_sql.py database\upgrade_v4.sql
   venv\Scripts\python.exe database\run_sql.py database\upgrade_v5.sql
   ```

4. **Run**
   ```
   venv\Scripts\python.exe app.py
   ```
   Open http://127.0.0.1:5000, register an account and upload a resume (text-based PDF, max 5 MB).

On macOS / Linux use `venv/bin/python` instead of `venv\Scripts\python.exe`.

---

## Tests

```
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python.exe -m pytest tests
```

AI calls are replaced by fakes, and route tests run on a temporary MySQL database
that is created and deleted automatically (your real data is never touched).

---

## Adding a job role

Roles live in the database, not in code. Add a row to `job_roles`, its skill groups to `role_skill_groups`
(`common` = required for everyone, `technology` = alternative paths) and its skills to `job_role_skills`
with an importance (`core`, `supporting`, `optional`) and a weight. See `database/upgrade_v3.sql` for examples.
New skills are detected automatically.

---

## Author

**Shailesh Kasbekar** — [GitHub](https://github.com/shaileshkasbekar)
