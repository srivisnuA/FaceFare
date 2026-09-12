# database/models.py
# ─────────────────────────────────────────────────────────────────
# Passenger data access layer.
# Backed by SQLite (see database/db.py) — balances now persist
# across restarts instead of resetting to hardcoded defaults.
#
# NOTE: function names/signatures are unchanged from the old
# in-memory version, so app.py needs NO changes at all.
# ─────────────────────────────────────────────────────────────────

from database.db import get_connection, init_db

# Ensure the table exists (and is seeded) as soon as this module loads.
init_db()


def get_passengers() -> dict:
    """Return all passengers as {pid: {'balance': ...}} — loaded fresh from the DB."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT pid, balance FROM passengers")
    rows = cur.fetchall()
    conn.close()
    return {row["pid"]: {"balance": row["balance"]} for row in rows}


def get_balance(pid: str):
    """Return the numeric balance for a passenger (0 if not found)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM passengers WHERE pid = ?", (pid,))
    row = cur.fetchone()
    conn.close()
    return row["balance"] if row else 0


def update_balance(pid: str, new_balance):
    """Overwrite a passenger's balance in the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE passengers SET balance = ? WHERE pid = ?", (new_balance, pid))
    conn.commit()
    conn.close()


def add_passenger(pid: str, initial_balance=100):
    """Add a new passenger (e.g. for admin top-ups), or reset an existing one."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO passengers (pid, balance) VALUES (?, ?)",
        (pid, initial_balance),
    )
    conn.commit()
    conn.close()


def get_all_balances() -> dict:
    """Return {pid: balance} with plain numbers — safe for JSON serialisation."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT pid, balance FROM passengers")
    rows = cur.fetchall()
    conn.close()
    return {row["pid"]: row["balance"] for row in rows}