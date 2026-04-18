from backend.distance import build_distance_matrix
from backend.vrp import build_vrp_qubo
from backend.classical import solve_classical, total_distance
from backend.metrics import total_distance_km, co2_kg, savings

coords = [
    (35.9049, -79.0469),  # depot
    (35.9132, -79.0558),
    (35.9060, -79.0300),
    (35.9200, -79.0400),
]

matrix = build_distance_matrix(coords)
print("Distance matrix:\n", matrix)

classical_edges = solve_classical(matrix)
classical_km = total_distance(classical_edges, matrix)
print(f"\nClassical route: {classical_edges}")
print(f"Classical distance: {classical_km:.3f} km | CO2: {co2_kg(classical_km):.3f} kg")

qubo = build_vrp_qubo(matrix)
print(f"\nQUBO variables: {qubo.get_num_vars()}")

from backend.qaoa import solve_qaoa, parse_result
result = solve_qaoa(qubo, reps=1)
quantum_edges = parse_result(result, len(coords))
quantum_km = total_distance_km(quantum_edges, matrix)
print(f"\nQAOA route: {quantum_edges}")
print(f"QAOA distance: {quantum_km:.3f} km")

print("\n--- Savings ---")
print(savings(classical_km, quantum_km))
