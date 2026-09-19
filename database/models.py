# database/models.py
# ─────────────────────────────────────────────────────────────────
# Passenger data access layer backed by SQLite.
# ─────────────────────────────────────────────────────────────────

from database.db import get_connection, init_db

init_db()


def get_passengers() -> dict:
    """Return all passengers as {pid: {'balance': ...}}."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT pid, balance FROM passengers").fetchall()
        return {row["pid"]: {"balance": row["balance"]} for row in rows}
    finally:
        conn.close()


def get_balance(pid: str):
    """Return the numeric balance for a passenger, or 0 if not found."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT balance FROM passengers WHERE pid = ?",
            (pid,),
        ).fetchone()
        return row["balance"] if row else 0
    finally:
        conn.close()


def update_balance(pid: str, new_balance):
    """Overwrite a passenger's balance in the database."""
    if not pid:
        raise ValueError("pid is required")
    if new_balance < 0:
        raise ValueError("balance cannot be negative")

    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE passengers SET balance = ? WHERE pid = ?",
            (new_balance, pid),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Passenger not found: {pid}")
        conn.commit()
    finally:
        conn.close()


def add_passenger(pid: str, initial_balance=100):
    """Add a new passenger without silently replacing an existing wallet."""
    if not pid:
        raise ValueError("pid is required")
    if initial_balance < 0:
        raise ValueError("initial_balance cannot be negative")

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO passengers (pid, balance) VALUES (?, ?)",
            (pid, initial_balance),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_balances() -> dict:
    """Return {pid: balance} with plain numbers for JSON serialization."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT pid, balance FROM passengers").fetchall()
        return {row["pid"]: row["balance"] for row in rows}
    finally:
        conn.close()
