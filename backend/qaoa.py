from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit.primitives import Sampler
import numpy as np

# I build a function that puts the solver together

def solve_qaoa(qubo, reps: int = 1):
    iteration = [0]

    def callback(x):
        iteration[0] += 1
        print(f"  iter {iteration[0]:3d}")


    sampler = Sampler()
    optimizer = COBYLA(maxiter=50, callback=callback)
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=reps)
    solver = MinimumEigenOptimizer(qaoa)
    result = solver.solve(qubo)
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



