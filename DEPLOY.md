# Putting ATS Resume Analyzer online

The project is ready to deploy (`wsgi.py`, `Procfile`, `gunicorn` in `requirements.txt`).
You need two things online: the **app** and a **MySQL database**. Railway gives both
in one place, so these steps use Railway. Render or a VPS work the same way.

## 1. Create the database

1. Sign up at <https://railway.app> with your GitHub account.
2. **New Project → Deploy from GitHub repo →** choose `ATS-Resume-Analyzer`.
3. In the same project: **New → Database → MySQL**.
4. Open the MySQL service → **Variables**: note `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`,
   `MYSQLPASSWORD`, `MYSQLDATABASE`.

## 2. Set the app's variables

Open the app service → **Variables** and add:

| Variable | Value |
|---|---|
| `SECRET_KEY` | a long random text (run `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `GROQ_API_KEY` | your Groq key |
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | from step 1 |
| `SESSION_COOKIE_SECURE` | `1` |
| `BEHIND_PROXY` | `1` |
| `FLASK_DEBUG` | `0` |
| `ADMIN_EMAILS` | your email (for the admin page) |
| `APP_URL` | the app's public address, e.g. `https://ats-resume-analyzer.up.railway.app` |

Railway starts the app with the `Procfile` (`gunicorn wsgi:app`).

## 3. Create the tables

The SQL files use the database name `ats_resume_analyzer_v2`. Either create a database with
that name on the MySQL server, or replace the name in the `USE ...` line of each file.
Then, on your own computer with the online database's values in `.env`, run:

```
venv\Scripts\python.exe database\run_sql.py database\schema.sql
venv\Scripts\python.exe database\run_sql.py database\upgrade_v3.sql
venv\Scripts\python.exe database\run_sql.py database\upgrade_v4.sql
venv\Scripts\python.exe database\run_sql.py database\upgrade_v5.sql
venv\Scripts\python.exe database\run_sql.py database\upgrade_v6.sql
```

(Railway's MySQL has a public connection address under **Settings → Networking** for this.)

## 4. Open it

Railway shows the public `https://` address. Register an account and try a job match.

## Things to know

- **Uploaded resumes:** most free hosts wipe the disk when the app restarts. Analyses stay in the
  database, but the original files (used for re-reading and the resume builder) can disappear.
  Add a persistent volume mounted at the `uploads` folder (Railway: **Settings → Volumes**) and set
  `UPLOAD_FOLDER` to its path.
- **AI cache:** stored in `cache/ai`; it is fine if a restart clears it.
- **Email reminders:** add the `SMTP_*` variables (see `tools/reminders.py`) and run
  `python -m tools.reminders` weekly with the host's cron / scheduled job feature.
- **Rate limits** are kept in memory per worker, so with 2 workers each limit is per worker.
- **OCR** for scanned PDFs needs Tesseract installed on the server; without it the app asks for a
  text-based file.
