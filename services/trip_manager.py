def board(session_state, passenger_id):

    if passenger_id not in session_state["onboard"]:
        session_state["onboard"].append(passenger_id)

    return session_state["onboard"]


def exit_bus(session_state, passenger_id):

    if passenger_id in session_state["onboard"]:
        session_state["onboard"].remove(passenger_id)

    return session_state["onboard"]