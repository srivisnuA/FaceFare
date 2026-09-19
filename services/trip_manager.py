"""Passenger boarding and exit state helpers."""


def _validate_state(session_state: dict) -> None:
    """Ensure trip state is a mutable mapping."""
    if not isinstance(session_state, dict):
        raise TypeError("session_state must be a dictionary")


def _validate_passenger_id(passenger_id: str) -> None:
    """Ensure passenger IDs are non-empty strings."""
    if not isinstance(passenger_id, str) or not passenger_id.strip():
        raise ValueError("passenger_id must be a non-empty string")


def board(session_state: dict, passenger_id: str) -> list:
    """Add a passenger to the onboard list if not already present."""
    _validate_state(session_state)
    _validate_passenger_id(passenger_id)

    onboard = session_state.setdefault("onboard", [])
    if not isinstance(onboard, list):
        raise TypeError("session_state['onboard'] must be a list")

    if passenger_id not in onboard:
        onboard.append(passenger_id)

    return onboard


def exit_bus(session_state: dict, passenger_id: str) -> list:
    """Remove a passenger from the onboard list if present."""
    _validate_state(session_state)
    _validate_passenger_id(passenger_id)

    onboard = session_state.setdefault("onboard", [])
    if not isinstance(onboard, list):
        raise TypeError("session_state['onboard'] must be a list")

    if passenger_id in onboard:
        onboard.remove(passenger_id)

    return onboard
