# ATS Resume Analyzer

## Overview

ATS Resume Analyzer is a Flask-based web application that analyzes resumes against specific job roles. It extracts text from PDF resumes, compares the candidate's skills with the required skills for the selected role, calculates an ATS score, and provides recommendations for improvement.

---

## Features

- User Registration and Login
- Secure Session Management
- Resume Upload (PDF)
- PDF Text Extraction
- Dynamic Job Role Selection
- Skill Matching
- ATS Score Calculation
- Missing Skill Identification
- Resume History
- MySQL Database Integration
- Responsive User Interface

---

## Tech Stack

### Backend
- Python
- Flask

### Frontend
- HTML
- CSS
- Jinja2 Templates

### Database
- MySQL

### Libraries
- Flask
- mysql-connector-python
- PyMuPDF
- Werkzeug

---

## Project Structure

```
ATS_RESUME_ANALYZER/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── schema/
│   └── database.sql
│
├── database/
├── models/
├── resume_parser/
├── routes/
├── static/
├── templates/
└── venv/
```

---

## Database Tables

- users
- resumes
- job_roles
- skills
- job_role_skills
- resume_results

---

## Installation

### Clone Repository

```bash
git clone <repository-url>
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Create Database

Run:

```
schema/database.sql
```

in MySQL.

### Start Application

```bash
python app.py
```

Open:

```
http://127.0.0.1:5000
```

---

## Future Enhancements

- AI Resume Suggestions
- Resume Preview
- Dashboard Analytics
- Charts and Reports
- Cloud Deployment

---

## Author

Shailesh Kasbekar

B.Tech Information Technology

SGGS Institute of Engineering and Technology, Nanded