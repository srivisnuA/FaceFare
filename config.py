# config.py
# ─────────────────────────────────────────────────────────────────
# Central app configuration. Previously these values were hardcoded
# directly inside app.py — now app.py imports them from here.
#
# SECRET_KEY can be overridden via an environment variable so a real
# secret is never committed to git.
# ─────────────────────────────────────────────────────────────────

import os

SECRET_KEY = os.environ.get("FACEFARE_SECRET_KEY", "facefare_secret")

BUS_STOPS     = ["Stop A", "Stop B", "Stop C", "Stop D", "Stop E"]
BASE_FARE     = 10
PER_STOP_RATE = 5