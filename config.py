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

    url = ""

    for name in ("MYSQL_URL", "MYSQL_PUBLIC_URL", "DATABASE_URL"):
        value = (os.getenv(name) or "").strip()
        if value.startswith("mysql"):
            url = value
            break
        if value:
            # Usually an unresolved Railway reference such as ${{MySQL.MYSQL_URL}}
            print(f"WARNING: {name} is set but is not a mysql:// address "
                  f"(it starts with {value[:10]!r}). Check the variable reference.")

    if not url:
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
    # 1. MYSQL_HOST etc.  2. parts of MYSQL_URL  3. Railway's own names
    #    (MYSQLHOST, MYSQLPORT, ...)  4. the local default
    railway_name = name.replace("MYSQL_", "MYSQL")
    return os.getenv(name) or _URL.get(name) or os.getenv(railway_name) or default


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    MYSQL_HOST = _setting("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(_setting("MYSQL_PORT", "3306"))
    MYSQL_USER = _setting("MYSQL_USER", "root")
    MYSQL_PASSWORD = _setting("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = _setting("MYSQL_DATABASE", "ats_resume_analyzer_v2")

    # Private folder (not under static/), so resumes are never
    # downloadable by URL. Older uploads in static/uploads are
    # blocked by security.py.
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

    # Set SESSION_COOKIE_SECURE=1 in .env when the site runs on HTTPS
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
