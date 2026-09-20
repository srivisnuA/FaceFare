# database/db.py
# ─────────────────────────────────────────────────────────────────
# SQLite connection + schema setup for FaceFare.
# The database file itself (facefare.db) is git-ignored — it's
# regenerated automatically on first run with seed passenger data.
# ─────────────────────────────────────────────────────────────────

import sqlite3
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.environ.get(
    "FACEFARE_DATA_DIR",
    os.path.join(PROJECT_ROOT, "data"),
)
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "facefare.db")

# Seed data used only the very first time the DB is created.
DEFAULT_PASSENGERS = {
    "srivisnu": 100,
    "praveen":  120,
    "bob":      80,
}


def get_connection() -> sqlite3.Connection:
    """Open a new connection to the FaceFare SQLite database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the passengers table and seed it only when it is empty."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS passengers (
                pid     TEXT PRIMARY KEY,
                balance REAL NOT NULL CHECK (balance >= 0)
            )
        """)

        cur.execute("SELECT COUNT(*) FROM passengers")
        count = cur.fetchone()[0]

        if count == 0:
            cur.executemany(
                "INSERT INTO passengers (pid, balance) VALUES (?, ?)",
                list(DEFAULT_PASSENGERS.items()),
            )

        conn.commit()
    finally:
        conn.close()
