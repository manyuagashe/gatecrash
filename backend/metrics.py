from typing import List, Tuple
import numpy as np

# we need a way to take all the edges we receive from the solvers
# and then turn those into human readable statistics that can be integrated into a UI


def total_distance_km(edges: List[Tuple[int, int]], distance_matrix: np.ndarray) -> float:
    return sum(distance_matrix[i][j] for i, j in edges)

# just multiplying km by 0.21kg CO2 per km as per CO2 
def co2_kg(distance_km: float) -> float:
    return distance_km * 0.21


# built a savings calculator to actually compare how much the quantum solver's results help

def savings(classical_km: float, quantum_km: float) -> dict:
    delta_km = classical_km - quantum_km
    delta_co2 = co2_kg(classical_km) - co2_kg(quantum_km)
    pct = (delta_km / classical_km * 100) if classical_km > 0 else 0
    return {
        "distance_saved_km": round(delta_km, 3),
        "co2_saved_kg": round(delta_co2, 3),
        "percent_improvement": round(pct, 1)
    }
