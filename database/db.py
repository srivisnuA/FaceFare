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
DB_PATH = os.path.join(DATA_DIR, "facefare.db")

# Seed data used only the very first time the DB is created.
DEFAULT_PASSENGERS = {
    "srivisnu": 100,
    "praveen":  120,
    "bob":      80,
}


def get_connection() -> sqlite3.Connection:
    """Open a new connection to the FaceFare SQLite database."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(seed=True):
    """Create the passengers table and seed it only when it is empty."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        first_setup = cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='passengers'").fetchone() is None

        cur.execute("""
            CREATE TABLE IF NOT EXISTS passengers (
                pid     TEXT PRIMARY KEY,
                balance REAL NOT NULL CHECK (balance >= 0)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY,
                pid TEXT NOT NULL REFERENCES passengers(pid)
                    ON UPDATE CASCADE ON DELETE CASCADE,
                delta_cents INTEGER NOT NULL,
                balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0),
                kind TEXT NOT NULL CHECK (kind IN ('opening', 'adjustment', 'set')),
                operation_id TEXT UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS wallet_transactions_pid ON wallet_transactions(pid, id)")

        cur.execute("SELECT COUNT(*) FROM passengers")
        count = cur.fetchone()[0]

        if first_setup and count == 0 and seed:
            cur.executemany(
                "INSERT INTO passengers (pid, balance) VALUES (?, ?)",
                list(DEFAULT_PASSENGERS.items()),
            )

        # Migrate existing wallets once, without inventing historical transactions.
        from services.money import to_cents
        for row in cur.execute("SELECT pid, balance FROM passengers").fetchall():
            cents = to_cents(row["balance"])
            cur.execute("""INSERT INTO wallet_transactions(pid, delta_cents, balance_cents, kind)
                SELECT ?, ?, ?, 'opening'
                WHERE NOT EXISTS (SELECT 1 FROM wallet_transactions WHERE pid = ?)""",
                (row["pid"], cents, cents, row["pid"]))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
