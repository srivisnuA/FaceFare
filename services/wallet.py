# services/wallet.py
# ─────────────────────────────────────────────────────────────────
# Wallet operations — works with both storage formats:
#   {"srivisnu": {"balance": 100}}   ← dict with nested key
#   {"srivisnu": 100}                ← flat int (legacy)
# ─────────────────────────────────────────────────────────────────


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


def deduct_balance(passengers: dict, pid: str, amount: int | float) -> bool:
    """
    Deduct *amount* from *pid*'s wallet.
    Returns True on success, False if funds are insufficient (no deduction made).
    """
    current = _get(passengers, pid)
    if current < amount:
        return False
    _set(passengers, pid, current - amount)
    return True


def top_up(passengers: dict, pid: str, amount: int | float):
    """Add *amount* to *pid*'s wallet (for admin recharge)."""
    current = _get(passengers, pid)
    _set(passengers, pid, current + amount)