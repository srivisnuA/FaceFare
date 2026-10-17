"""SQLite wallets: balance changes and ledger entries commit together.

Call init_db() at startup. Importing this module does not create data. Legacy REAL
balances remain compatible; arithmetic and ledger amounts use integer cents.
Fractional cents are rejected rather than rounded.
"""
from contextlib import closing

from database.db import get_connection, init_db
from services.money import from_cents, to_cents


def _pid(pid):
    if not isinstance(pid, str) or not pid.strip():
        raise ValueError("pid must be non-empty text")


def _row(conn, pid):
    row = conn.execute("SELECT balance FROM passengers WHERE pid = ?", (pid,)).fetchone()
    if row is None:
        raise ValueError(f"Passenger not found: {pid}")
    return row


def _record(conn, pid, delta, balance, kind, operation_id=None):
    conn.execute("""INSERT INTO wallet_transactions
        (pid, delta_cents, balance_cents, kind, operation_id) VALUES (?, ?, ?, ?, ?)""",
        (pid, delta, balance, kind, operation_id))


def get_passengers():
    return {pid: {"balance": balance} for pid, balance in get_all_balances().items()}


def get_all_balances():
    with closing(get_connection()) as conn:
        return {row["pid"]: row["balance"] for row in
                conn.execute("SELECT pid, balance FROM passengers ORDER BY pid")}


def get_balance(pid):
    _pid(pid)
    with closing(get_connection()) as conn:
        return _row(conn, pid)["balance"]


def get_transactions(pid):
    _pid(pid)
    with closing(get_connection()) as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM wallet_transactions WHERE pid = ? ORDER BY id", (pid,))]


def change_balance(pid, delta, operation_id=None):
    """Serialize adjustments; optional operation IDs prevent retry charges.

    Insufficient funds returns None without writing. Reusing an operation ID for
    different input is an error. A successful retry returns the current balance.
    """
    _pid(pid)
    cents = to_cents(delta, allow_negative=True)
    if cents == 0:
        raise ValueError("delta must be non-zero")
    if operation_id is not None and (not isinstance(operation_id, str) or
                                   not operation_id.strip() or len(operation_id) > 128):
        raise ValueError("operation_id must be 1 to 128 characters")
    with closing(get_connection()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        current = to_cents(_row(conn, pid)["balance"])
        if operation_id is not None:
            previous = conn.execute("SELECT pid, delta_cents FROM wallet_transactions WHERE operation_id = ?",
                                    (operation_id,)).fetchone()
            if previous:
                if previous["pid"] != pid or previous["delta_cents"] != cents:
                    raise ValueError("operation_id already used for a different adjustment")
                return from_cents(current)
        balance = current + cents
        if balance < 0:
            return None
        value = from_cents(balance)
        to_cents(value)
        conn.execute("UPDATE passengers SET balance = ? WHERE pid = ?", (value, pid))
        _record(conn, pid, cents, balance, "adjustment", operation_id)
        return value


def edit_passenger(old_pid, new_pid, new_balance=None):
    """Rename and optionally replace a balance in one transaction.

    Omitted balance preserves the database value even after concurrent top-ups.
    Ledger foreign keys follow a rename atomically.
    """
    _pid(old_pid)
    _pid(new_pid)
    requested = None if new_balance is None else to_cents(new_balance)
    with closing(get_connection()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        current = to_cents(_row(conn, old_pid)["balance"])
        balance = current if requested is None else requested
        conn.execute("UPDATE passengers SET pid = ?, balance = ? WHERE pid = ?",
                     (new_pid, from_cents(balance), old_pid))
        if balance != current:
            _record(conn, new_pid, balance - current, balance, "set")
        return from_cents(balance)


def update_balance(pid, new_balance):
    return edit_passenger(pid, pid, new_balance)


def rename_passenger(old_pid, new_pid):
    return edit_passenger(old_pid, new_pid)


def add_passenger(pid, initial_balance=100):
    _pid(pid)
    cents = to_cents(initial_balance)
    with closing(get_connection()) as conn, conn:
        conn.execute("INSERT INTO passengers(pid, balance) VALUES (?, ?)", (pid, from_cents(cents)))
        _record(conn, pid, cents, cents, "opening")


def delete_passenger(pid):
    _pid(pid)
    with closing(get_connection()) as conn, conn:
        cursor = conn.execute("DELETE FROM passengers WHERE pid = ?", (pid,))
        if cursor.rowcount == 0:
            raise ValueError(f"Passenger not found: {pid}")
