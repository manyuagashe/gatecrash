from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo
import numpy as np

# time-indexed TSP QUBO (Lucas 2014).
# the edge-indicator version I had before (x_{i,j} = "did we use this edge?")
# let QAOA return disconnected subtours — "1-in / 1-out per non-depot stop"
# was satisfiable by multiple disjoint cycles among non-depot nodes with the
# depot sitting out. this version uses x_{i,t} = "is non-depot stop i visited
# at time slot t?" instead. a valid solution is a permutation matrix, which
# by construction is a single cycle — disconnected routes are impossible.

def build_vrp_qubo(distance_matrix: np.ndarray, num_cars: int = 1):
    n = len(distance_matrix)
    qp = QuadraticProgram(name="VRP")  # helped me describe this optimization problem mathematically

    # x_{i}_{t} is an indicator: non-depot stop i is the t-th visit on my route.
    # depot (index 0) is fixed at slot 0 implicitly, so I only declare variables
    # for non-depot stops × non-depot slots — (n-1)^2 binary vars total.
    for i in range(1, n):
        for t in range(1, n):
            qp.binary_var(name=f"x_{i}_{t}")

    # below is an explicit declaration of my objective. it splits into three
    # distance-weighted pieces, all pulled straight from the distance matrix:
    #   (a) depot -> first visit:   d[0][i] * x_{i,1}         (linear)
    #   (b) transitions:            d[i][j] * x_{i,t} * x_{j,t+1}   (quadratic)
    #   (c) last visit -> depot:    d[i][0] * x_{i,n-1}       (linear)

    linear: dict[str, float] = {}
    for i in range(1, n):
        linear[f"x_{i}_1"]     = linear.get(f"x_{i}_1", 0.0)     + distance_matrix[0][i]
        linear[f"x_{i}_{n-1}"] = linear.get(f"x_{i}_{n-1}", 0.0) + distance_matrix[i][0]

    quadratic: dict[tuple[str, str], float] = {}
    for t in range(1, n - 1):
        for i in range(1, n):
            for j in range(1, n):
                if i != j:
                    quadratic[(f"x_{i}_{t}", f"x_{j}_{t+1}")] = distance_matrix[i][j]

    qp.minimize(linear=linear, quadratic=quadratic)
    # the full objective above = total tour distance. minimizing = shortest route.

    # now the linear constraints that force x into a permutation matrix shape.

    # i establish each non-depot stop is visited exactly once across all slots.
    # no more, no less.
    for i in range(1, n):
        constraint: dict[str | int, float] = {f"x_{i}_{t}": 1.0 for t in range(1, n)}
        qp.linear_constraint(linear=constraint, sense="==", rhs=1, name=f"city_{i}_once")

    # i establish each non-depot time slot holds exactly one stop.
    # no more, no less.
    for t in range(1, n):
        constraint: dict[str | int, float] = {f"x_{i}_{t}": 1.0 for i in range(1, n)}
        qp.linear_constraint(linear=constraint, sense="==", rhs=1, name=f"slot_{t}_once")

    # now the agenda is to convert to QUBO so this can actually be operated on
    # by quantum solving. penalty coefficient is auto-tuned by the converter.
    converter = QuadraticProgramToQubo()
    qubo = converter.convert(qp)
    return qubo
