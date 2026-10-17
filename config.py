# config.py
# ─────────────────────────────────────────────────────────────────
# Central application configuration.
# ─────────────────────────────────────────────────────────────────

import os
import secrets


SECRET_KEY = os.environ.get("FACEFARE_SECRET_KEY")

if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    if os.environ.get("FACEFARE_ENV", "development").lower() != "development":
        raise RuntimeError(
            "FACEFARE_SECRET_KEY must be set outside development."
        )


BUS_STOPS = ["Stop A", "Stop B", "Stop C", "Stop D", "Stop E"]
BASE_FARE = 10
PER_STOP_RATE = 5
DEMO_MODE = os.environ.get("FACEFARE_DEMO", "0") == "1"
