import numpy as np
from math import radians, sin, cos, sqrt, atan2
from typing import List, Tuple

#I just a simple often used function for straight line distance in km between two lat/lon points


def haversine(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    R = 6371  # Earth radius in km
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

# I also need a proper distance matrix though!

def build_distance_matrix(coords: List[Tuple[float, float]]) -> np.ndarray:
    n = len(coords)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = haversine(coords[i], coords[j])
    return matrix

