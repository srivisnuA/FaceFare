# services/logger.py
# ─────────────────────────────────────────────────────────────────
# Transaction logging. Every board/exit/decline event is written to
# the console AND appended to logs/transactions.log for a persistent
# audit trail (previously only kept in-memory, lost on restart).
# ─────────────────────────────────────────────────────────────────

import datetime
import os

LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs",
    "transactions.log",
)


def log_transaction(pid: str, event: str, details: str = ""):
    """Record a passenger transaction/event to console + a persistent log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {pid} | {event}"
    if details:
        line += f" | {details}"

    print(f"[Transaction] {line}")

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")