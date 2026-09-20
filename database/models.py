# database/models.py
# ─────────────────────────────────────────────────────────────────
# Passenger data access layer backed by SQLite.
# ─────────────────────────────────────────────────────────────────

import math

from database.db import get_connection, init_db

init_db()


def _valid_balance(value) -> bool:
    """Return True only for non-negative numeric wallet balances."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _valid_delta(value) -> bool:
    """Return True only for numeric wallet adjustments."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


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
    if not _valid_balance(new_balance):
        raise ValueError("balance must be a non-negative number")

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


def change_balance(pid: str, delta):
    """
    Atomically adjust a passenger balance.

    Returns the new balance on success, or None when the passenger does
    not have enough balance for a deduction.
    """
    if not pid:
        raise ValueError("pid is required")
    if not _valid_delta(delta) or delta == 0:
        raise ValueError("delta must be a non-zero number")

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT balance FROM passengers WHERE pid = ?",
            (pid,),
        ).fetchone()

        if row is None:
            raise ValueError(f"Passenger not found: {pid}")

        new_balance = row["balance"] + delta
        if new_balance < 0:
            conn.rollback()
            return None

        conn.execute(
            "UPDATE passengers SET balance = ? WHERE pid = ?",
            (new_balance, pid),
        )
        conn.commit()
        return new_balance
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def add_passenger(pid: str, initial_balance=100):
    """Add a new passenger without silently replacing an existing wallet."""
    if not pid:
        raise ValueError("pid is required")
    if not _valid_balance(initial_balance):
        raise ValueError("initial_balance must be a non-negative number")

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


def rename_passenger(old_pid: str, new_pid: str):
    """Rename a passenger while preserving the wallet balance."""
    if not old_pid or not new_pid:
        raise ValueError("passenger names are required")
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE passengers SET pid = ? WHERE pid = ?",
            (new_pid, old_pid),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Passenger not found: {old_pid}")
        conn.commit()
    finally:
        conn.close()


def delete_passenger(pid: str):
    """Delete a passenger record from the wallet database."""
    if not pid:
        raise ValueError("pid is required")
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM passengers WHERE pid = ?", (pid,))
        if cursor.rowcount == 0:
            raise ValueError(f"Passenger not found: {pid}")
        conn.commit()
    finally:
        conn.close()
