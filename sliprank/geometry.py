"""Crystal-frame vectors for uniaxial Schmid factors.

HCP Cartesian frame, in units of the basal lattice parameter a:

- x is parallel to a1 = [2-1-10]
- y is parallel to [01-10]
- z is parallel to [0001]

A Miller–Bravais direction [uvtw] with u + v + t = 0 converts as

    x = (3/2) u
    y = (sqrt(3)/2) (u + 2v)
    z = w (c/a)

A Miller–Bravais plane (hkil) with h + k + i = 0 has a normal, in units of 1/a,

    x = h
    y = (h + 2k) / sqrt(3)
    z = l / (c/a)

BCC planes and directions use the cubic Cartesian components of the Miller indices.
"""

from __future__ import annotations

import math
from typing import Sequence

Vector = tuple[float, float, float]


def format_indices(indices: Sequence[int], wrapper: str) -> str:
    """Format small Miller indices as (10-12) or [11-1]."""
    body = "".join(str(int(value)) if value >= 0 else "-" + str(abs(int(value))) for value in indices)
    if wrapper == "()":
        return "(" + body + ")"
    if wrapper == "[]":
        return "[" + body + "]"
    raise ValueError("wrapper must be '()' or '[]'")


def first_nonzero_sign(values: Sequence[int]) -> int:
    for value in values:
        if value > 0:
            return 1
        if value < 0:
            return -1
    return 0


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    return float(left[0] * right[0] + left[1] * right[1] + left[2] * right[2])


def norm(vector: Sequence[float]) -> float:
    return math.sqrt(dot(vector, vector))


def unit(vector: Sequence[float]) -> Vector:
    length = norm(vector)
    if length == 0.0:
        raise ValueError("zero vector")
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def hcp_direction_cartesian(indices: Sequence[int], c_over_a: float) -> Vector:
    u, v, _t, w = indices
    return (
        1.5 * u,
        (math.sqrt(3) / 2.0) * (u + 2.0 * v),
        w * c_over_a,
    )


def hcp_normal_cartesian(indices: Sequence[int], c_over_a: float) -> Vector:
    h, k, _i, l = indices
    return (
        float(h),
        (h + 2.0 * k) / math.sqrt(3.0),
        l / c_over_a,
    )


def bcc_cartesian(indices: Sequence[int]) -> Vector:
    return (float(indices[0]), float(indices[1]), float(indices[2]))


def zone_integer(plane: Sequence[int], direction: Sequence[int]) -> int:
    """Miller or Miller–Bravais zone product. Zero means the direction lies in the plane."""
    return sum(int(h) * int(u) for h, u in zip(plane, direction))
