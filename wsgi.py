"""
Entry point for a production server:

    gunicorn wsgi:app            (Linux hosts: Railway, Render, a VPS)
    waitress-serve wsgi:app      (Windows)
"""

import os

from werkzeug.middleware.proxy_fix import ProxyFix

from app import app

# Behind a hosting proxy (HTTPS is handled by the host): trust its headers
# so redirects and secure cookies use https.

if os.getenv("BEHIND_PROXY", "0") == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
