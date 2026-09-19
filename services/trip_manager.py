"""Passenger boarding and exit state helpers."""


def board(session_state: dict, passenger_id: str) -> list:
    """Add a passenger to the onboard list if not already present."""
    if not passenger_id:
        raise ValueError("passenger_id is required")

    onboard = session_state.setdefault("onboard", [])
    if passenger_id not in onboard:
        onboard.append(passenger_id)

    return onboard


def exit_bus(session_state: dict, passenger_id: str) -> list:
    """Remove a passenger from the onboard list if present."""
    if not passenger_id:
        raise ValueError("passenger_id is required")

    onboard = session_state.setdefault("onboard", [])
    if passenger_id in onboard:
        onboard.remove(passenger_id)

    return onboard
