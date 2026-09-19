# services/wallet.py
# ─────────────────────────────────────────────────────────────────
# Wallet operations — works with both storage formats:
#   {"srivisnu": {"balance": 100}}   ← dict with nested key
#   {"srivisnu": 100}                ← flat int (legacy)
#
# Balance changes are applied to the in-memory passengers dict
# AND persisted to the database, so they survive an app restart.
# ─────────────────────────────────────────────────────────────────

from database.models import change_balance as _change_balance


def _get(passengers: dict, pid: str) -> int | float:
    """Read balance regardless of storage format."""
    val = passengers.get(pid)
    if val is None:
        return 0
    return val["balance"] if isinstance(val, dict) else val


def _set(passengers: dict, pid: str, amount: int | float):
    """Write balance regardless of storage format."""
    if pid not in passengers:
        return
    if isinstance(passengers[pid], dict):
        passengers[pid]["balance"] = amount
    else:
        passengers[pid] = amount


def _valid_amount(amount: int | float) -> bool:
    """Return True only for strictly positive numeric amounts."""
    return (
        isinstance(amount, (int, float))
        and not isinstance(amount, bool)
        and amount > 0
    )


def deduct_balance(passengers: dict, pid: str, amount: int | float) -> bool:
    """Atomically deduct amount from a passenger wallet."""
    if not _valid_amount(amount) or pid not in passengers:
        return False

    new_balance = _change_balance(pid, -amount)
    if new_balance is None:
        return False

    _set(passengers, pid, new_balance)
    return True


def top_up(passengers: dict, pid: str, amount: int | float) -> bool:
    """Atomically add a strictly positive amount to a passenger wallet."""
    if not _valid_amount(amount) or pid not in passengers:
        return False

    new_balance = _change_balance(pid, amount)
    _set(passengers, pid, new_balance)
    return True
