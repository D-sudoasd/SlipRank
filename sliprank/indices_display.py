"""Compact and spaced display forms for Miller and Miller–Bravais indices."""

from __future__ import annotations


def _wrap(body: str, wrapper: str) -> str:
    if wrapper == "()":
        return "(" + body + ")"
    if wrapper == "[]":
        return "[" + body + "]"
    raise ValueError("wrapper must be '()' or '[]'")


def _integers(indices: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    if len(indices) == 0:
        raise ValueError("indices must not be empty")
    return tuple(int(value) for value in indices)


def spaced(indices: tuple[int, ...] | list[int], wrapper: str) -> str:
    """Format each integer with a space between items, for example ``(1 0 -1 2)``."""
    body = " ".join(str(value) for value in _integers(indices))
    return _wrap(body, wrapper)


def compact(indices: tuple[int, ...] | list[int], wrapper: str) -> str:
    """Format single-digit indices as ``(10-12)``, ``[2-1-10]``, or ``[11-1]``."""
    parts: list[str] = []
    for value in _integers(indices):
        if abs(value) > 9:
            raise ValueError(f"index {value} is not a single digit 0-9")
        parts.append(str(value) if value >= 0 else "-" + str(abs(value)))
    return _wrap("".join(parts), wrapper)


def both_forms(indices: tuple[int, ...] | list[int], wrapper: str) -> str:
    """Return compact and spaced forms, for example ``(10-12) = (1 0 -1 2)``."""
    return compact(indices, wrapper) + " = " + spaced(indices, wrapper)
