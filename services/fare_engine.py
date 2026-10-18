# services/fare_engine.py
# ─────────────────────────────────────────────────────────────────
# Centralized fare calculation.
# ─────────────────────────────────────────────────────────────────


from services.money import to_cents, from_cents


def calculate_fare(
    distance: int,
    base_fare: int = 10,
    per_stop_rate: int = 5,
) -> int:
    """
    Calculate the fare for a trip.

    Distance must be non-negative. A zero-stop trip still incurs only
    the base fare; negative distances are rejected.
    """
    if not isinstance(distance, int) or isinstance(distance, bool):
        raise TypeError("distance must be an integer")
    if distance < 0:
        raise ValueError("distance cannot be negative")

    if not isinstance(base_fare, (int, float)) or isinstance(base_fare, bool):
        raise TypeError("base_fare must be numeric")
    if not isinstance(per_stop_rate, (int, float)) or isinstance(per_stop_rate, bool):
        raise TypeError("per_stop_rate must be numeric")
    if base_fare < 0 or per_stop_rate < 0:
        raise ValueError("fare values cannot be negative")

    cents = to_cents(base_fare) + distance * to_cents(per_stop_rate)
    result = from_cents(cents)
    to_cents(result)
    return result
