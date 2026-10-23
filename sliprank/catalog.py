"""Built-in HCP and BCC slip and twin systems.

HCP twin shear senses are fixed by the c axis:

- {10-12}<10-11> extends [0001] (tension twin)
- {11-22}<11-23> and {10-11}<10-12> contract [0001] (compression twins)

Slip systems are bidirectional: the opposite shear direction is the same system.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from sliprank.geometry import first_nonzero_sign, format_indices


@dataclass(frozen=True)
class DeformationSystem:
    structure: str
    family: str
    kind: str
    polarity: str
    c_axis_effect: str | None
    plane: tuple[int, ...]
    direction: tuple[int, ...]

    @property
    def plane_text(self) -> str:
        return format_indices(self.plane, "()")

    @property
    def direction_text(self) -> str:
        return format_indices(self.direction, "[]")


def _component_permutations(components: tuple[int, int, int]) -> tuple[tuple[int, int, int], ...]:
    seeds = {components, tuple(-value for value in components)}
    found: list[tuple[int, int, int]] = []
    for seed in seeds:
        for perm in set(itertools.permutations(seed)):
            found.append((int(perm[0]), int(perm[1]), int(perm[2])))
    unique: list[tuple[int, int, int]] = []
    for item in found:
        if item not in unique:
            unique.append(item)
    return tuple(unique)


def _orient_hcp(
    plane: tuple[int, int, int, int],
    direction: tuple[int, int, int, int],
    *,
    bidirectional: bool,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    if plane[3] < 0 or (plane[3] == 0 and first_nonzero_sign(plane) < 0):
        plane = tuple(-value for value in plane)  # type: ignore[assignment]
        direction = tuple(-value for value in direction)  # type: ignore[assignment]
    if bidirectional and first_nonzero_sign(direction) < 0:
        direction = tuple(-value for value in direction)  # type: ignore[assignment]
    return plane, direction


def _hcp_family(
    *,
    family: str,
    kind: str,
    polarity: str,
    c_axis_effect: str | None,
    plane_hki: tuple[int, int, int],
    plane_l: tuple[int, ...],
    direction_uvt: tuple[int, int, int],
    direction_w: tuple[int, ...],
) -> tuple[DeformationSystem, ...]:
    planes = [(*perm, int(ell)) for perm in _component_permutations(plane_hki) for ell in plane_l]
    directions = [(*perm, int(w)) for perm in _component_permutations(direction_uvt) for w in direction_w]
    bidirectional = polarity == "bidirectional"
    found: dict[tuple[tuple[int, ...], tuple[int, ...]], DeformationSystem] = {}
    for plane in planes:
        for direction in directions:
            if sum(h * u for h, u in zip(plane, direction)) != 0:
                continue
            product = plane[3] * direction[3]
            if c_axis_effect == "extend" and product <= 0:
                continue
            if c_axis_effect == "contract" and product >= 0:
                continue
            oriented_plane, oriented_direction = _orient_hcp(plane, direction, bidirectional=bidirectional)
            system = DeformationSystem(
                structure="hcp",
                family=family,
                kind=kind,
                polarity=polarity,
                c_axis_effect=c_axis_effect,
                plane=oriented_plane,
                direction=oriented_direction,
            )
            found[(system.plane, system.direction)] = system
    return tuple(found.values())


def _bcc_planes(seed: tuple[int, int, int]) -> tuple[tuple[int, int, int], ...]:
    raw: list[tuple[int, int, int]] = []
    for perm in set(itertools.permutations(seed)):
        for signs in itertools.product((-1, 1), repeat=3):
            raw.append((signs[0] * perm[0], signs[1] * perm[1], signs[2] * perm[2]))
    unique: list[tuple[int, int, int]] = []
    for plane in raw:
        opposite = tuple(-value for value in plane)
        canonical = plane if plane > opposite else opposite
        if canonical not in unique:
            unique.append(canonical)  # type: ignore[arg-type]
    return tuple(unique)


def _bcc_family(family: str, plane_seed: tuple[int, int, int]) -> tuple[DeformationSystem, ...]:
    directions = list(itertools.product((-1, 1), repeat=3))
    found: dict[tuple[tuple[int, ...], tuple[int, ...]], DeformationSystem] = {}
    for plane in _bcc_planes(plane_seed):
        for direction in directions:
            if plane[0] * direction[0] + plane[1] * direction[1] + plane[2] * direction[2] != 0:
                continue
            oriented = direction if first_nonzero_sign(direction) > 0 else tuple(-value for value in direction)
            system = DeformationSystem(
                structure="bcc",
                family=family,
                kind="slip",
                polarity="bidirectional",
                c_axis_effect=None,
                plane=plane,
                direction=oriented,
            )
            found[(system.plane, system.direction)] = system
    return tuple(found.values())


def hcp_systems() -> tuple[DeformationSystem, ...]:
    specs = (
        ("basal_a", "slip", "bidirectional", None, (0, 0, 0), (1,), (1, 1, -2), (0,)),
        ("prismatic_a", "slip", "bidirectional", None, (1, 0, -1), (0,), (1, 1, -2), (0,)),
        ("pyramidal_a", "slip", "bidirectional", None, (1, 0, -1), (1,), (1, 1, -2), (0,)),
        ("pyramidal_ca_I", "slip", "bidirectional", None, (1, 0, -1), (1,), (1, 1, -2), (3, -3)),
        ("pyramidal_ca_II", "slip", "bidirectional", None, (1, 1, -2), (2,), (1, 1, -2), (3, -3)),
        ("twin_10_12", "twin", "unidirectional", "extend", (1, 0, -1), (2,), (1, 0, -1), (1, -1)),
        ("twin_11_22", "twin", "unidirectional", "contract", (1, 1, -2), (2,), (1, 1, -2), (3, -3)),
        ("twin_10_11", "twin", "unidirectional", "contract", (1, 0, -1), (1,), (1, 0, -1), (2, -2)),
    )
    systems: list[DeformationSystem] = []
    for spec in specs:
        systems.extend(
            _hcp_family(
                family=spec[0],
                kind=spec[1],
                polarity=spec[2],
                c_axis_effect=spec[3],
                plane_hki=spec[4],
                plane_l=spec[5],
                direction_uvt=spec[6],
                direction_w=spec[7],
            )
        )
    return tuple(systems)


def bcc_systems() -> tuple[DeformationSystem, ...]:
    systems: list[DeformationSystem] = []
    for family, seed in (
        ("slip_110", (1, 1, 0)),
        ("slip_112", (1, 1, 2)),
        ("slip_123", (1, 2, 3)),
    ):
        systems.extend(_bcc_family(family, seed))
    return tuple(systems)


def systems_for(structure: str) -> tuple[DeformationSystem, ...]:
    if structure == "hcp":
        return hcp_systems()
    if structure == "bcc":
        return bcc_systems()
    raise ValueError(structure)


def families_for(structure: str) -> tuple[str, ...]:
    seen: list[str] = []
    for system in systems_for(structure):
        if system.family not in seen:
            seen.append(system.family)
    return tuple(seen)
