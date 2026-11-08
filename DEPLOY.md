# Putting ATS Resume Analyzer online (and on Google)

Everything is automatic: when the app starts online it creates or upgrades the database
tables itself (`python -m database.setup` in the `Procfile`), then starts `gunicorn wsgi:app`.

## 1. Railway: app + database

1. Sign in at <https://railway.app> with GitHub.
2. **New Project → Deploy from GitHub repo →** `ATS-Resume-Analyzer`.
3. In the same project: **+ New → Database → Add MySQL**.
4. Click the app service → **Settings → Networking → Generate Domain**.
   You get an address like `https://ats-resume-analyzer-production.up.railway.app`.

## 2. App variables

App service → **Variables → Raw Editor**, paste and fill in:

```
MYSQL_URL=${{MySQL.MYSQL_URL}}
SECRET_KEY=paste-a-long-random-text
GROQ_API_KEY=your-groq-key
APP_URL=https://your-address.up.railway.app
SESSION_COOKIE_SECURE=1
BEHIND_PROXY=1
FLASK_DEBUG=0
```

`${{MySQL.MYSQL_URL}}` is typed exactly like that: Railway fills in the database address.
Make a secret key with `python -c "import secrets; print(secrets.token_hex(32))"`.

Railway redeploys. Open the address: you should see the homepage. `/health` shows
`{"status": "ok"}` when the database is connected.

## 3. Google

1. Open <https://search.google.com/search-console> → **Add property → URL prefix** → your address.
2. Choose **HTML tag**. Copy only the `content` value, e.g. `abc123XYZ`.
3. In Railway add the variable `GOOGLE_SITE_VERIFICATION=abc123XYZ`, wait for the redeploy,
   then click **Verify** in Search Console.
4. Search Console → **Sitemaps** → enter `sitemap.xml` → **Submit**.
5. **URL inspection** → paste your address → **Request indexing**.

Google usually lists a new site within a few days to a few weeks. Searching the exact name
("ATS Resume Analyzer Shailesh Kasbekar") works first; general searches like "resume checker"
take much longer, because many large sites compete for them.

## Things to know

- **Uploaded resumes:** a restart wipes the disk. Analyses stay in the database, but original files
  (used for re-reading and the resume builder) can disappear. To keep them: app service →
  **Settings → Volumes → mount at `/app/uploads`**.
- **Separate settings instead of MYSQL_URL:** `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`,
  `MYSQL_PASSWORD`, `MYSQL_DATABASE` also work.
- **Email reminders:** add the `SMTP_*` variables (see `tools/reminders.py`) and run
  `python -m tools.reminders` weekly as a Railway cron job.
- **Admin page:** optional, set `ADMIN_EMAILS` to your login email.
- **Rate limits** are kept in memory per worker (2 workers).
- **OCR** for scanned PDFs needs Tesseract on the server; without it the app asks for a text-based file.
