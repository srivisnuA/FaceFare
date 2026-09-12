# services/fare_engine.py
# ─────────────────────────────────────────────────────────────────
# Centralized fare calculation. app.py now calls this instead of
# computing fare inline, so there's a single source of truth.
# ─────────────────────────────────────────────────────────────────

def calculate_fare(distance: int, base_fare: int = 10, per_stop_rate: int = 5) -> int:
    """
    Calculate the fare for a trip.

    distance:      number of stops travelled (minimum 1 is enforced)
    base_fare:     flat starting fare
    per_stop_rate: fare added per stop travelled
    """
    distance = max(1, distance)
    return base_fare + (distance * per_stop_rate)