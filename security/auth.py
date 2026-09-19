# security/auth.py
# ─────────────────────────────────────────────────────────────────
# Simple session-based authentication for the driver/admin panel.
#
# NOTE: ADMIN_PASSWORD is read from an environment variable so the
# real password is never committed to git. Falls back to a default
# for local development only — set FACEFARE_ADMIN_PASSWORD before
# deploying this anywhere real.
# ─────────────────────────────────────────────────────────────────

import os
from functools import wraps
from flask import session, redirect, url_for, request

ADMIN_PASSWORD = os.environ.get("FACEFARE_ADMIN_PASSWORD", "facefare123")


def check_password(password: str) -> bool:
    """Check a submitted password against the configured admin password."""
    return password == ADMIN_PASSWORD


def is_authenticated() -> bool:
    """Check whether the current session is logged in."""
    return bool(session.get("authenticated"))


def login_required(view_func):
    """Route decorator: redirect to /login if not authenticated."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped