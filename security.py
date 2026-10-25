"""
Security helpers:

- CSRF protection: every POST must send the session's token
  (hidden form field "csrf_token" or header "X-CSRF-Token").
- Rate limiting for login and AI-heavy routes (in memory, per user / IP).
- Secure session cookie settings.
- Login-required decorator.
- Uploaded resumes are never served as public static files.
"""

import hmac
import secrets
import time
from collections import defaultdict, deque
from functools import wraps

from flask import abort, flash, redirect, request, session
from markupsafe import Markup


# =========================================
# CSRF
# =========================================

def csrf_token():

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    return session["csrf_token"]


def csrf_field():
    """
    {{ csrf_field() }} inside every <form method="POST">.
    """

    return Markup(f'<input type="hidden" name="csrf_token" value="{csrf_token()}">')


def check_csrf():

    if request.method != "POST":
        return

    expected = session.get("csrf_token")

    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")

    if not expected or not sent or not hmac.compare_digest(expected, sent):

        if request.is_json or request.headers.get("X-CSRF-Token") is not None:
            abort(400, "Invalid CSRF token")

        flash("Your session expired. Please try again.", "danger")

        return redirect(request.referrer or "/")


# =========================================
# Rate limiting
# =========================================

_hits = defaultdict(deque)


def _client_key(name):

    who = session.get("user_id") or request.headers.get("X-Forwarded-For", request.remote_addr)

    return f"{name}:{who}"


def rate_limited(name, limit, period_seconds):
    """
    True if this user/IP made more than `limit` requests
    to `name` in the last `period_seconds`.
    """

    now = time.time()

    hits = _hits[_client_key(name)]

    while hits and hits[0] <= now - period_seconds:
        hits.popleft()

    if len(hits) >= limit:
        return True

    hits.append(now)

    return False


def rate_limit(name, limit, period_seconds, redirect_to=None):
    """
    Decorator for POST routes (GET requests are not limited).
    """

    def decorator(view):

        @wraps(view)
        def wrapper(*args, **kwargs):

            if request.method == "POST" and rate_limited(name, limit, period_seconds):

                message = "Too many requests. Please wait a minute and try again."

                if request.is_json:
                    return {"error": message}, 429

                flash(message, "danger")

                return redirect(redirect_to or request.path)

            return view(*args, **kwargs)

        return wrapper

    return decorator


def reset_rate_limits():

    _hits.clear()


# =========================================
# Login required
# =========================================

def login_required(view):

    @wraps(view)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            if request.is_json:
                return {"error": "Login required"}, 401

            return redirect("/login")

        return view(*args, **kwargs)

    return wrapper


# =========================================
# App setup
# =========================================

def init_security(app):

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    )

    app.jinja_env.globals["csrf_field"] = csrf_field
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def _security_checks():

        # Old uploads live in static/uploads; never serve them publicly

        if request.path.startswith("/static/uploads/"):
            abort(404)

        if app.config.get("CSRF_ENABLED", True):
            return check_csrf()

    @app.after_request
    def _security_headers(response):

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")

        return response
