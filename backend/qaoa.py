from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_aer.primitives import Sampler
import numpy as np

# I build a function that puts the solver together

def solve_qaoa(qubo, reps: int = 1):
    iteration = [0]
    log = []

    def callback(x):
        iteration[0] += 1
        msg = f"cobyla iter {iteration[0]:3d}"
        log.append(msg)
        print(f"  {msg}")


    # Aer shot-based sampler. At n=4 (12 qubits) Aer's automatic method picks
    # statevector, which runs in seconds. Default Sampler (qiskit.primitives)
    # also does exact statevector but has far more per-call overhead — hence Aer.

    sampler = Sampler(run_options={"shots": 1024})
    optimizer = COBYLA(maxiter=10, callback=callback)
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=reps)
    solver = MinimumEigenOptimizer(qaoa)
    result = solver.solve(qubo)
    # stash the iteration log on the result so api.py can forward it to the frontend
    result._iter_log = log  # type: ignore[attr-defined]
    return result

# the raw result is just a binary array, useless for our purposes
# I use edges to decode back into (i,j) pairs

def parse_result(result, n: int):
    x = result.x
    edges = []
    idx = 0
    for i in range(n):
        for j in range(n):
            if i != j:
                if x[idx] > 0.5:
                    edges.append((i, j))
                idx += 1
    return edges
