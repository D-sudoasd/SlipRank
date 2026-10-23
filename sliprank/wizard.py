"""Turn one typed direction into the JSON object evaluate() already accepts.

This module does not calculate a Schmid factor and does not invent CRSS values.
"""

from __future__ import annotations


class WizardError(ValueError):
    """A direction or answer that cannot be turned into a SlipRank input."""


def _compact(text: str) -> list[int]:
    indices: list[int] = []
    index = 0
    while index < len(text):
        sign = 1
        if text[index] == "-":
            sign = -1
            index += 1
            if index >= len(text) or not text[index].isdigit():
                raise WizardError(f"负号后面必须是一位数字。无法读取方向『{text}』。")
        if not text[index].isdigit():
            raise WizardError(
                f"紧凑方向每个指数只能是一位数字，负号属于下一位。无法读取『{text}』。"
            )
        indices.append(sign * int(text[index]))
        index += 1
    if not indices:
        raise WizardError("方向是空的。")
    return indices


def _spaced(text: str) -> list[int]:
    indices: list[int] = []
    for token in text.split():
        try:
            number = int(token)
        except ValueError as exc:
            raise WizardError(f"方向中的『{token}』不是整数。") from exc
        indices.append(number)
    return indices


def parse_direction(structure: str, text: str) -> dict[str, object]:
    """Parse one HCP or BCC load direction.

    Returns ``{"frame": "miller_bravais"|"miller", "indices": [int, ...]}``.
    Compact text uses one digit per index, and a hyphen belongs to the next digit.
    ``10-11`` is ``[1, 0, -1, 1]``. Spaced text keeps each token as one integer.
    """
    kind = structure.strip().lower()
    if kind not in ("hcp", "bcc"):
        raise WizardError(f"structure 只能是 hcp 或 bcc；实际得到 {structure!r}。")
    raw = text.strip()
    if not raw:
        raise WizardError("方向是空的。HCP 例如 0001 或 2-1-10，BCC 例如 001。")
    if raw[0] in "[(" and raw[-1] in "])":
        raw = raw[1:-1].strip()
    raw = raw.replace(",", " ").replace("，", " ")
    if any(character.isspace() for character in raw):
        indices = _spaced(raw)
    else:
        indices = _compact(raw)
    expected = 4 if kind == "hcp" else 3
    frame = "miller_bravais" if kind == "hcp" else "miller"
    if len(indices) != expected:
        if kind == "hcp":
            raise WizardError(
                "HCP 方向需要四个整数 [u, v, t, w]。"
                f"紧凑写法一位一个指数，例如 0001 或 2-1-10。实际得到 {indices}。"
            )
        raise WizardError(f"BCC 方向需要三个整数 [u, v, w]，例如 001。实际得到 {indices}。")
    if all(value == 0 for value in indices):
        raise WizardError("载荷方向是零矢量。请给出非零的 Miller 或 Miller–Bravais 方向。")
    if kind == "hcp":
        u, v, t, w = indices
        if u + v + t != 0:
            raise WizardError(
                f"Miller–Bravais 方向 [{u}, {v}, {t}, {w}] 必须满足 u+v+t=0；"
                f"实际 {u}+{v}+{t}={u + v + t}。"
            )
    return {"frame": frame, "indices": indices}


def build_document(
    structure: str,
    loading: str,
    direction: str,
    stress_MPa: float | None,
    label: str,
) -> dict[str, object]:
    """Build one input object. CRSS is omitted until the user supplies it in JSON."""
    kind = structure.strip().lower()
    modes = {
        "拉伸": "tension",
        "压缩": "compression",
        "tension": "tension",
        "compression": "compression",
    }
    mode = modes.get(loading.strip())
    if mode is None:
        raise WizardError("加载只能是拉伸、压缩、tension 或 compression。")
    if label not in ("synthetic", "user"):
        raise WizardError("label 必须是 synthetic 或 user。")
    parsed = parse_direction(kind, direction)
    document: dict[str, object] = {
        "label": label,
        "description": "由方向向导生成。未提供 CRSS，因此只按 Schmid 因子排序，没有 Sachs 应力。",
        "structure": kind,
        "loading": mode,
        "orientation_name": " ".join(direction.split()),
        "load": {"frame": parsed["frame"], "indices": list(parsed["indices"])},
    }
    if stress_MPa is not None:
        document["applied_stress_MPa"] = stress_MPa
    return document
