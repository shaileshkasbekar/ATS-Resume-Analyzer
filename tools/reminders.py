"""
Weekly learning-roadmap reminder emails.

Sends one email per user who turned reminders on in Settings, listing their
open roadmap tasks. At most one email per user every 6 days.

Setup (in .env):
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=you@gmail.com
    SMTP_PASSWORD=your-app-password      (Gmail: create an "App password")
    SMTP_FROM=ATS Resume Analyzer <you@gmail.com>
    APP_URL=http://127.0.0.1:5000

Run (preview without sending):
    venv\\Scripts\\python.exe -m tools.reminders --dry-run
Send:
    venv\\Scripts\\python.exe -m tools.reminders
Schedule it weekly with Windows Task Scheduler (or cron on a server).
"""

import os
import smtplib
import sys
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv                                   # noqa: E402

load_dotenv()

MIN_DAYS_BETWEEN = 6


def email_configured():

    return all(os.getenv(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def due_reminders(connection):
    """
    [(user, [open tasks])] for users who want a reminder now.
    """

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        f"""
        SELECT user_id, full_name, email FROM users
        WHERE reminders_enabled = 1
          AND (last_reminder_at IS NULL OR last_reminder_at < NOW() - INTERVAL {MIN_DAYS_BETWEEN} DAY)
        """
    )

    users = cursor.fetchall()

    due = []

    for user in users:

        cursor.execute(
            """
            SELECT ri.skill, ri.priority, jd.job_title
            FROM roadmap_items ri JOIN jd_results jd ON jd.jd_result_id = ri.jd_result_id
            WHERE ri.user_id = %s AND ri.status != 'done'
            ORDER BY FIELD(ri.priority, 'high', 'medium', 'low'), ri.item_id
            LIMIT 10
            """,
            (user["user_id"],)
        )

        tasks = cursor.fetchall()

        if tasks:
            due.append((user, tasks))

    cursor.close()

    return due


def build_email(user, tasks):

    app_url = os.getenv("APP_URL", "http://127.0.0.1:5000").rstrip("/")

    labels = {"high": "required", "medium": "show it better", "low": "preferred"}

    lines = [f"Hi {user['full_name']},", "",
             f"You have {len(tasks)} open task(s) on your learning roadmap:", ""]

    lines += [f"  - {t['skill']} ({labels.get(t['priority'], t['priority'])}) for {t['job_title'] or 'your job match'}"
              for t in tasks]

    lines += ["", f"Open your roadmap: {app_url}/roadmap", "",
              f"You get this email because reminders are on. Turn them off in Settings: {app_url}/settings"]

    message = EmailMessage()
    message["Subject"] = f"Your learning roadmap: {len(tasks)} task(s) to go"
    message["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER", "")
    message["To"] = user["email"]
    message.set_content("\n".join(lines))

    return message


def send_all(dry_run=False, connection=None, smtp_factory=None):
    """
    Returns the number of emails sent (or that would be sent).
    """

    from models.database import get_db_connection

    own_connection = connection is None
    connection = connection or get_db_connection()

    try:

        due = due_reminders(connection)

        if dry_run:
            for user, tasks in due:
                print(f"[dry run] would email {user['email']}: {len(tasks)} task(s)")
            return len(due)

        if not email_configured():
            print("Email is not configured. Add SMTP_HOST, SMTP_USER and SMTP_PASSWORD to .env (see tools/reminders.py).")
            return 0

        smtp_factory = smtp_factory or (lambda: smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587")), timeout=30))

        sent = 0

        with smtp_factory() as smtp:

            smtp.starttls()
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))

            cursor = connection.cursor()

            for user, tasks in due:

                try:
                    smtp.send_message(build_email(user, tasks))
                except smtplib.SMTPException as e:
                    print(f"Could not email {user['email']}: {e}")
                    continue

                cursor.execute("UPDATE users SET last_reminder_at = NOW() WHERE user_id = %s", (user["user_id"],))
                connection.commit()
                sent += 1

            cursor.close()

        print(f"Sent {sent} reminder email(s).")

        return sent

    finally:

        if own_connection:
            connection.close()


if __name__ == "__main__":
    send_all(dry_run="--dry-run" in sys.argv)
