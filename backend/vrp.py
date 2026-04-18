from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo
import numpy as np

def build_vrp_qubo(distance_matrix: np.ndarray, num_cars: int = 1):
    n = len(distance_matrix) 
    qp = QuadraticProgram(name="VRP") # helped me describe this optimization problem mathematically

    # x_ij is an indicator for my travel from i to j
    for i in range(n):
        for j in range(n):
            if i != j:
                qp.binary_var(name=f"x_{i}_{j}")


# below is an explicit declaration of my objective with this probem
    linear = {}
    for i in range(n):
        for j in range(n):
            if i != j:
                linear[f"x_{i}_{j}"] = distance_matrix[i][j]
# above lets me successfully assign each x_ij a coef
# this coef is equal to the distance between i and j
# therefore my problem now involves minimizing the sum of all these coefs.

    qp.minimize(linear=linear)

# need proper linear constraints to solve this program

# i establish each stop (except the starting depot) must be departed from exactly once
# no more, no less

    for j in range(1, n):
        constraint: dict[str | int, float]= {f"x_{i}_{j}": 1.0 for i in range(n) if i != j}
        qp.linear_constraint(linear=constraint, sense="==", rhs=1, name=f"arrive_{j}")


# i establish each stop (except the starting depot) must be arrived at exactly once
# no more, no less

    for i in range(1, n):
        constraint: dict[str | int, float]= {f"x_{i}_{j}": 1.0 for j in range(n) if i != j}
        qp.linear_constraint(linear=constraint, sense="==", rhs=1, name=f"depart_{i}")
        

# now the agenda is to convert to QUBO so this can actually be operated on by quantum solving

    converter = QuadraticProgramToQubo()
    qubo = converter.convert(qp)
    return qubo
