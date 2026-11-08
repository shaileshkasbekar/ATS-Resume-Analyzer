import os
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

load_dotenv()


def _mysql_from_url():
    """
    Online hosts (Railway) give one MYSQL_URL like
    mysql://user:password@host:port/database. Its parts are used
    when the separate MYSQL_* settings are not set.
    """

    url = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL") or ""

    if not url.startswith("mysql"):
        return {}

    parts = urlparse(url)

    return {
        "MYSQL_HOST": parts.hostname,
        "MYSQL_PORT": str(parts.port or 3306),
        "MYSQL_USER": unquote(parts.username or ""),
        "MYSQL_PASSWORD": unquote(parts.password or ""),
        "MYSQL_DATABASE": parts.path.lstrip("/") or None,
    }


_URL = _mysql_from_url()


def _setting(name, default):
    return os.getenv(name) or _URL.get(name) or default


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    MYSQL_HOST = _setting("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(_setting("MYSQL_PORT", "3306"))
    MYSQL_USER = _setting("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD") or _URL.get("MYSQL_PASSWORD") or ""
    MYSQL_DATABASE = _setting("MYSQL_DATABASE", "ats_resume_analyzer_v2")

    # Private folder (not under static/), so resumes are never
    # downloadable by URL. Older uploads in static/uploads are
    # blocked by security.py.
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

    # Set SESSION_COOKIE_SECURE=1 in .env when the site runs on HTTPS
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
