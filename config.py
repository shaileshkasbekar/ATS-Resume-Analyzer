import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ats_resume_analyzer_v2")

    # Private folder (not under static/), so resumes are never
    # downloadable by URL. Older uploads in static/uploads are
    # blocked by security.py.
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

    # Set SESSION_COOKIE_SECURE=1 in .env when the site runs on HTTPS
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
