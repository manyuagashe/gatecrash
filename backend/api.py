from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple
import json
import time
from pathlib import Path

from backend.distance import build_distance_matrix
from backend.vrp import build_vrp_qubo
from backend.classical import solve_classical
from backend.qaoa import solve_qaoa, parse_result
from backend.metrics import total_distance_km, co2_kg, savings

app = FastAPI(title="gatecrash")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA = Path(__file__).parent.parent / "data" / "chapel_hill_stops.json"

# Hard cap so both solvers benchmark on the same n.
# n=5 → n(n-1) = 20 qubits. Aer statevector handles this in seconds.
# n=6 → 30 qubits → MPS simulation takes 10+ minutes. Not usable for a live demo.
BENCHMARK_MAX = 5


class OptimizeRequest(BaseModel):
    coords: List[Tuple[float, float]]
    num_vehicles: int = 1
    qaoa_reps: int = 1


def _route_payload(edges, matrix, elapsed_ms):
    dist = total_distance_km(edges, matrix)
    return {
        "edges": [list(e) for e in edges],
        "distance_km": round(dist, 4),
        "co2_kg": round(co2_kg(dist), 4),
        "compute_ms": round(elapsed_ms, 2),
    }


@app.get("/demo")
def demo():
    with open(DATA) as f:
        return json.load(f)


@app.post("/optimize")
def optimize(req: OptimizeRequest):
    full_coords = [tuple(c) for c in req.coords]

    # Trim up front so classical and quantum see identical problems.
    # Keep depot (index 0) + the nearest (BENCHMARK_MAX - 1) stops to depot.
    if len(full_coords) <= BENCHMARK_MAX:
        keep_idx = list(range(len(full_coords)))
        trimmed = False
    else:
        temp_matrix = build_distance_matrix(full_coords)
        depot_dists = [(i, temp_matrix[0][i]) for i in range(1, len(full_coords))]
        depot_dists.sort(key=lambda x: x[1])
        keep_idx = [0] + [i for i, _ in depot_dists[: BENCHMARK_MAX - 1]]
        trimmed = True

    coords = [full_coords[i] for i in keep_idx]
    matrix = build_distance_matrix(coords)

    # classical baseline
    t0 = time.perf_counter()
    c_edges = solve_classical(matrix)
    c_ms = (time.perf_counter() - t0) * 1000

    # quantum — same matrix
    qubo = build_vrp_qubo(matrix)
    t1 = time.perf_counter()
    q_result = solve_qaoa(qubo, reps=req.qaoa_reps)
    q_edges = parse_result(q_result, len(coords))
    q_ms = (time.perf_counter() - t1) * 1000

    classical = _route_payload(c_edges, matrix, c_ms)
    quantum = _route_payload(q_edges, matrix, q_ms)

    iter_log = getattr(q_result, "_iter_log", [])

    return {
        "classical": classical,
        "quantum": quantum,
        "savings": savings(classical["distance_km"], quantum["distance_km"]),
        "problem": {
            "n": len(coords),
            "qubits": qubo.get_num_vars(),
            "coord_indices": keep_idx,
            "trimmed_from": len(full_coords) if trimmed else None,
            "benchmark_parity": True,
        },
        "run_log": iter_log,
        "stack": {
            "qiskit": "1.4.2",
            "aer": "0.15.1",
            "optimizer": "COBYLA",
            "reps": req.qaoa_reps,
            "shots": 1024,
        },
    }
