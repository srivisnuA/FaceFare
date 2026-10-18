# security/auth.py
# ─────────────────────────────────────────────────────────────────
# Simple session-based authentication for the driver/admin panel.
# ─────────────────────────────────────────────────────────────────

import os
import secrets
import threading
from functools import wraps
from hmac import compare_digest

from flask import session, redirect, url_for, request, jsonify

ADMIN_PASSWORD = os.environ.get("FACEFARE_ADMIN_PASSWORD")
_active_sessions = set()
_session_lock = threading.Lock()


def start_session():
    session.clear()
    token = secrets.token_urlsafe(32)
    with _session_lock:
        _active_sessions.add(token)
    session["auth_id"] = token
    session["authenticated"] = True


def end_session():
    with _session_lock:
        _active_sessions.discard(session.get("auth_id"))
    session.clear()

if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = "facefare123"
    if os.environ.get("FACEFARE_ENV", "development").lower() != "development":
        raise RuntimeError(
            "FACEFARE_ADMIN_PASSWORD must be set outside development."
        )


def check_password(password: str) -> bool:
    """Check a submitted password using constant-time comparison."""
    return isinstance(password, str) and compare_digest(password.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8"))


def is_authenticated() -> bool:
    """Check whether the current session is logged in."""
    with _session_lock:
        return session.get("auth_id") in _active_sessions


def login_required(view_func):
    """Route decorator: redirect to /login if not authenticated."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            if request.path.startswith("/api/") or request.path == "/control":
                return jsonify({"ok": False, "error": "Authentication required."}), 401
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped
