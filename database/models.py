# database/models.py
# ─────────────────────────────────────────────────────────────────
# Passenger database
# Stores each passenger's balance as a plain integer.
# ─────────────────────────────────────────────────────────────────

_passengers = {
    "srivisnu": {"balance": 100},
    "praveen":    {"balance": 120},
    "bob":      {"balance": 80},
}


def get_passengers() -> dict:
    """Return the full passengers dict."""
    return _passengers


def get_balance(pid: str) -> int | float:
    """Return the numeric balance for a passenger."""
    p = _passengers.get(pid)
    if p is None:
        return 0
    return p["balance"] if isinstance(p, dict) else p


def update_balance(pid: str, new_balance: int | float):
    """Overwrite a passenger's balance."""
    if pid not in _passengers:
        return
    if isinstance(_passengers[pid], dict):
        _passengers[pid]["balance"] = new_balance
    else:
        _passengers[pid] = new_balance


def add_passenger(pid: str, initial_balance: int | float = 100):
    """Add a new passenger (e.g. for admin top-ups)."""
    _passengers[pid] = {"balance": initial_balance}


def get_all_balances() -> dict[str, int | float]:
    """Return {pid: balance} with plain numbers — safe for JSON serialisation."""
    return {
        k: (v["balance"] if isinstance(v, dict) else v)
        for k, v in _passengers.items()
    }