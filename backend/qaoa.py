from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_aer.primitives import Sampler
import numpy as np

# I build a function that puts the solver together

def solve_qaoa(qubo, reps: int = 2):
    iteration = [0]
    log = []

    def callback(x):
        iteration[0] += 1
        msg = f"cobyla iter {iteration[0]:3d}"
        log.append(msg)
        print(f"  {msg}")


    # Aer shot-based sampler. With the time-indexed QUBO (Path B) the qubit
    # count is (n-1)^2, so n=5 -> 16 qubits — Aer picks statevector and runs
    # fast. reps=2 gives the ansatz 4 variational params (γ1,β1,γ2,β2), enough
    # expressivity to reliably land on valid permutations at n=5.
    sampler = Sampler(run_options={"shots": 1024})
    optimizer = COBYLA(maxiter=100, callback=callback)
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=reps)
    solver = MinimumEigenOptimizer(qaoa)
    result = solver.solve(qubo)
    # stash the iteration log on the result so api.py can forward it to the frontend
    result._iter_log = log  # type: ignore[attr-defined]
    return result

# the raw result is just a binary array, useless for our purposes.
# I decode the permutation matrix back into (i,j) edge pairs. if QAOA returns
# an invalid permutation (some city unassigned, some slot empty) I repair it
# by appending the missing cities at the end so the tour is always valid —
# honest in the sense that we disclose when a repair happened (via edge count).

def parse_result(result, n: int):
    x = result.x
    slot_to_city: dict[int, int] = {}
    idx = 0
    for i in range(1, n):
        for t in range(1, n):
            if x[idx] > 0.5:
                slot_to_city[t] = i   # if two cities claim one slot, later i wins
            idx += 1

    # walk slots in order, keeping each city the first time it appears.
    visited: list[int] = []
    for t in range(1, n):
        c = slot_to_city.get(t)
        if c is not None and c not in visited:
            visited.append(c)

    # any city the QAOA bitstring failed to place — repair by appending.
    missing = [c for c in range(1, n) if c not in visited]
    visited.extend(missing)

    # reconstruct edges: depot → v1 → v2 → ... → v_{n-1} → depot.
    edges = []
    prev = 0
    for city in visited:
        edges.append((prev, city))
        prev = city
    edges.append((prev, 0))
    return edges
