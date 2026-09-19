# services/logger.py
# ─────────────────────────────────────────────────────────────────
# Transaction logging. Events are written to the console and to a
# persistent audit log.
# ─────────────────────────────────────────────────────────────────

import datetime
import os
import threading

LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs",
    "transactions.log",
)

_log_lock = threading.Lock()


def log_transaction(pid: str, event: str, details: str = ""):
    """Record a passenger transaction/event safely."""
    if not pid:
        raise ValueError("pid is required")
    if not event:
        raise ValueError("event is required")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {pid} | {event}"
    if details:
        line += f" | {details}"

    print(f"[Transaction] {line}")

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # Multiple camera/socket threads can log concurrently.
    # Serialize writes so individual transaction lines are not interleaved.
    with _log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
