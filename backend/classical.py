import numpy as np
from typing import List, Tuple



# this is a classical nearest neighbours algorithm. The purpose of this is to be a comparison tool
# we want to show off the superiority of quantum solving as compared to classical solving




def solve_classical(distance_matrix: np.ndarray) -> List[Tuple[int, int]]: # type: ignore
    n = len(distance_matrix)
    visited = [False] * n
    edges = []
    current = 0  # this indicates we are starting from a given delivery depot
    visited[0] = True

    for _ in range(n - 1):
        nearest = -1
        nearest_dist = float("inf")

        for j in range(n):
            if not visited[j] and distance_matrix[current][j] < nearest_dist:
                nearest = j
                nearest_dist = distance_matrix[current][j]

        edges.append((current, nearest))
        visited[nearest] = True
        current = nearest

    edges.append((current, 0))
    return edges

def total_distance(edges: List[Tuple[int, int]], distance_matrix: np.ndarray) -> float:
    return sum(distance_matrix[i][j] for i, j in edges)
