def calculate_fare(distance=5):

    base_fare = 10
    per_km_rate = 2

    fare = base_fare + (distance * per_km_rate)

    return fare