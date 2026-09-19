# security/auth.py
# ─────────────────────────────────────────────────────────────────
# Simple session-based authentication for the driver/admin panel.
# ─────────────────────────────────────────────────────────────────

import os
from functools import wraps
from hmac import compare_digest

from flask import session, redirect, url_for, request

ADMIN_PASSWORD = os.environ.get("FACEFARE_ADMIN_PASSWORD")

if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = "facefare123"
    if os.environ.get("FACEFARE_ENV", "development").lower() != "development":
        raise RuntimeError(
            "FACEFARE_ADMIN_PASSWORD must be set outside development."
        )


def check_password(password: str) -> bool:
    """Check a submitted password using constant-time comparison."""
    return compare_digest(password, ADMIN_PASSWORD)


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
