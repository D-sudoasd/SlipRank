"""Uniaxial Schmid-factor ranking.

The geometric Schmid factor for a unit load direction l_hat is

    m = (n_hat · l_hat) (s_hat · l_hat)

n_hat is the unit plane normal and s_hat is the unit shear direction.
Both vectors and l_hat are in the same Cartesian crystal frame.
m is dimensionless.

Resolved shear stress, with the uniaxial stress magnitude σ in MPa:

    τ / MPa = m_active × σ / MPa

Slip uses m_active = |m| because either shear sense is allowed.
Twinning uses m_active = m in tension and m_active = -m in compression,
and only when that value is positive. The opposite sense has m_active = 0.

The single-crystal Sachs yield stress, in MPa, is

    σ_y = min(CRSS / m_active)

over systems with m_active > 0 and a supplied CRSS. It applies to uniaxial
tension or compression of one orientation, without hardening, lattice
rotation, or grain interaction. BCC scores are geometric only: non-Schmid
stresses on screw dislocations are outside this calculation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sliprank.catalog import DeformationSystem, families_for, systems_for
from sliprank.geometry import (
    bcc_cartesian,
    dot,
    hcp_direction_cartesian,
    hcp_normal_cartesian,
    norm,
    unit,
)

DEFAULT_C_OVER_A = 1.587
ACTIVE_TOLERANCE = 1e-10
SACHS_TIE_MPA = 1e-6

FORMULA = (
    "m = (n_hat · l_hat) (s_hat · l_hat)，无量纲。",
    "τ / MPa = m_active × σ / MPa。",
    "σ_y / MPa = min(CRSS / m_active)，只对 m_active > 0 且已给出 CRSS 的变形系。",
)

APPLICABILITY = (
    "单轴拉伸或单轴压缩。σ 取正值，单位 MPa；拉或压由 loading 指定。",
    "滑移按双向处理，m_active = |m|。孪晶按单向处理，只有与孪生剪切同号的一侧 m_active > 0。",
    "{10-12}<10-11> 的剪切方向取使 [0001] 伸长的一侧；{11-22}<11-23> 和 {10-11}<10-12> 取使 [0001] 缩短的一侧。",
    "HCP 直角坐标：x ∥ [2-1-10]，y ∥ [01-10]，z ∥ [0001]。c/a 使用输入值。缺省 1.587 只作为 α-Ti 筛查用的常规比值，不是某块样品的实测点阵常数。",
    "Sachs 应力是单晶体、无硬化、无晶粒相互作用的估计。不包含多晶 Taylor 或自洽平均、晶格转动、孪晶体积分数，也不包含 BCC 螺位错的 non-Schmid 应力。",
    "CRSS 全部来自输入。程序不把示例里的整数 CRSS 当作实测值。",
)


class SlipRankError(ValueError):
    """A named problem in the input. The message is the user-facing text."""


@dataclass(frozen=True)
class AnalysisRequest:
    label: str
    description: str
    orientation_name: str
    structure: str
    loading: str
    c_over_a: float | None
    c_over_a_is_default: bool
    applied_stress_MPa: float | None
    crss_MPa: tuple[tuple[str, float], ...]
    load_frame: str
    load_indices: tuple[int, ...] | None
    load_xyz: tuple[float, float, float] | None

    def crss_map(self) -> dict[str, float]:
        return dict(self.crss_MPa)


@dataclass(frozen=True)
class SystemScore:
    family: str
    kind: str
    polarity: str
    plane: str
    direction: str
    plane_indices: tuple[int, ...]
    direction_indices: tuple[int, ...]
    schmid_tension: float
    active_schmid: float
    sense_ok: bool
    tau_MPa: float | None
    crss_MPa: float | None
    tau_over_crss: float | None
    sachs_yield_MPa: float | None


@dataclass(frozen=True)
class AnalysisResult:
    label: str
    description: str
    orientation_name: str
    structure: str
    c_over_a: float | None
    c_over_a_is_default: bool
    loading: str
    applied_stress_MPa: float | None
    load_frame: str
    load_indices: tuple[int, ...] | None
    load_xyz: tuple[float, float, float] | None
    load_cartesian: tuple[float, float, float]
    systems: tuple[SystemScore, ...]
    favored: tuple[SystemScore, ...]
    sachs_yield_MPa: float | None


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise SlipRankError(f"{name} 必须是有限数值；实际得到 {value!r}。")
    return float(value)


def _integral(value: object, name: str) -> int:
    number = _finite_number(value, name)
    if not number.is_integer():
        raise SlipRankError(f"{name} 必须是整数；实际得到 {value!r}。")
    return int(number)


def _one_request(payload: dict, default_name: str) -> AnalysisRequest:
    if not isinstance(payload, dict):
        raise SlipRankError("每一组取向必须是 JSON 对象。")
    label = payload.get("label")
    if label not in ("synthetic", "user"):
        raise SlipRankError("label 必须是 synthetic 或 user。synthetic 表示构造数据，user 表示使用者自己的输入。")
    description = payload.get("description", "")
    if not isinstance(description, str):
        raise SlipRankError("description 必须是字符串。")
    structure = payload.get("structure")
    if structure not in ("hcp", "bcc"):
        raise SlipRankError(f"structure 只能是 hcp 或 bcc；实际得到 {structure!r}。")
    loading = payload.get("loading")
    if loading not in ("tension", "compression"):
        raise SlipRankError(f"loading 只能是 tension 或 compression；实际得到 {loading!r}。")
    name = payload.get("orientation_name", default_name)
    if not isinstance(name, str) or not name.strip():
        raise SlipRankError("orientation_name 必须是非空字符串。")
    c_over_a = None
    c_over_a_is_default = False
    if "c_over_a" in payload and payload["c_over_a"] is not None:
        if structure != "hcp":
            raise SlipRankError("c_over_a 只用于 hcp；bcc 不使用这个参数。")
        c_over_a = _finite_number(payload["c_over_a"], "c_over_a")
    elif structure == "hcp":
        c_over_a = DEFAULT_C_OVER_A
        c_over_a_is_default = True
    applied = None
    if "applied_stress_MPa" in payload and payload["applied_stress_MPa"] is not None:
        applied = _finite_number(payload["applied_stress_MPa"], "applied_stress_MPa")
    crss_payload = payload.get("crss_MPa", {})
    if crss_payload is None:
        crss_payload = {}
    if not isinstance(crss_payload, dict):
        raise SlipRankError("crss_MPa 必须是对象，键为变形系家族，值为 CRSS，单位 MPa。")
    known = families_for(structure)
    crss_pairs: list[tuple[str, float]] = []
    for key, raw in crss_payload.items():
        if key not in known:
            names = "、".join(known)
            raise SlipRankError(f"未知的 CRSS 家族『{key}』。{structure} 可用的家族是：{names}。")
        crss_value = _finite_number(raw, f"CRSS『{key}』")
        crss_pairs.append((str(key), crss_value))
    load = payload.get("load")
    if not isinstance(load, dict):
        raise SlipRankError("缺少 load。需要 load.frame，以及 indices 或 xyz。")
    frame = load.get("frame")
    indices = None
    xyz = None
    if frame == "cartesian":
        raw_xyz = load.get("xyz")
        if not isinstance(raw_xyz, (list, tuple)) or len(raw_xyz) != 3:
            raise SlipRankError("直角坐标载荷需要 load.xyz，且必须是三个数 [x, y, z]。")
        xyz = tuple(_finite_number(item, "load.xyz") for item in raw_xyz)
    elif frame == "miller_bravais":
        if structure != "hcp":
            raise SlipRankError("miller_bravais 只用于 hcp。bcc 请使用 miller 或 cartesian。")
        raw_indices = load.get("indices")
        if not isinstance(raw_indices, (list, tuple)) or len(raw_indices) != 4:
            raise SlipRankError("Miller–Bravais 载荷需要四个整数 load.indices = [u, v, t, w]。")
        indices = tuple(_integral(item, "load.indices") for item in raw_indices)
    elif frame == "miller":
        if structure != "bcc":
            raise SlipRankError("hcp 载荷请使用 miller_bravais 或 cartesian，不要使用三指数 miller。")
        raw_indices = load.get("indices")
        if not isinstance(raw_indices, (list, tuple)) or len(raw_indices) != 3:
            raise SlipRankError("立方 Miller 载荷需要三个整数 load.indices = [u, v, w]。")
        indices = tuple(_integral(item, "load.indices") for item in raw_indices)
    else:
        raise SlipRankError(
            f"load.frame 只能是 cartesian、miller_bravais 或 miller；实际得到 {frame!r}。"
        )
    return AnalysisRequest(
        label=label,
        description=description,
        orientation_name=name.strip(),
        structure=structure,
        loading=loading,
        c_over_a=c_over_a,
        c_over_a_is_default=c_over_a_is_default,
        applied_stress_MPa=applied,
        crss_MPa=tuple(crss_pairs),
        load_frame=frame,
        load_indices=indices,
        load_xyz=xyz,
    )


def requests_from_mapping(document: object) -> tuple[AnalysisRequest, ...]:
    if not isinstance(document, dict):
        raise SlipRankError("输入 JSON 必须是对象。")
    if "orientations" in document:
        items = document["orientations"]
        if not isinstance(items, list) or not items:
            raise SlipRankError("orientations 必须是非空数组。")
        shared = {key: value for key, value in document.items() if key != "orientations"}
        requests: list[AnalysisRequest] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise SlipRankError(f"orientations 的第 {index} 项必须是对象。")
            merged = {**shared, **item}
            merged.pop("orientations", None)
            if "orientation_name" not in merged and "name" in item:
                merged["orientation_name"] = item["name"]
            requests.append(_one_request(merged, f"orientation-{index}"))
        return tuple(requests)
    return (_one_request(document, "orientation-1"),)


def _check_science(request: AnalysisRequest) -> None:
    if request.structure == "hcp":
        if request.c_over_a is None or request.c_over_a <= 0.0:
            raise SlipRankError(f"c_over_a 必须大于 0；实际得到 {request.c_over_a}。")
    if request.applied_stress_MPa is not None and request.applied_stress_MPa <= 0.0:
        raise SlipRankError(
            "applied_stress_MPa 必须大于 0，单位 MPa；拉或压已经由 loading 表示。"
            f"实际得到 {request.applied_stress_MPa}。"
        )
    for family, value in request.crss_MPa:
        if value <= 0.0:
            raise SlipRankError(f"CRSS『{family}』必须是大于 0 的数，单位 MPa；实际得到 {value}。")
    if request.load_frame == "miller_bravais" and request.load_indices is not None:
        u, v, t, _w = request.load_indices
        if u + v + t != 0:
            raise SlipRankError(
                f"Miller–Bravais 载荷方向 [{u}, {v}, {t}, {_w}] 必须满足 u+v+t=0；"
                f"实际 {u}+{v}+{t}={u + v + t}。"
            )


def _load_cartesian(request: AnalysisRequest) -> tuple[float, float, float]:
    if request.load_frame == "cartesian":
        if request.load_xyz is None:
            raise SlipRankError("直角坐标载荷缺少 xyz。")
        vector = request.load_xyz
    elif request.structure == "hcp":
        if request.load_indices is None or request.c_over_a is None:
            raise SlipRankError("HCP 载荷缺少 Miller–Bravais 指数或 c/a。")
        vector = hcp_direction_cartesian(request.load_indices, request.c_over_a)
    else:
        if request.load_indices is None:
            raise SlipRankError("BCC 载荷缺少 Miller 指数。")
        vector = bcc_cartesian(request.load_indices)
    if norm(vector) == 0.0:
        raise SlipRankError("载荷方向是零矢量。请给出非零的 Miller、Miller–Bravais 或直角坐标方向。")
    return vector


def _vectors(system: DeformationSystem, c_over_a: float | None) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if system.structure == "hcp":
        if c_over_a is None:
            raise SlipRankError("HCP 计算缺少 c/a。")
        return hcp_normal_cartesian(system.plane, c_over_a), hcp_direction_cartesian(system.direction, c_over_a)
    return bcc_cartesian(system.plane), bcc_cartesian(system.direction)


def plane_normal_and_shear(
    system: DeformationSystem,
    c_over_a: float | None,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Cartesian plane normal and shear direction used by evaluate."""
    return _vectors(system, c_over_a)


def _score_system(
    system: DeformationSystem,
    *,
    loading: str,
    load: tuple[float, float, float],
    c_over_a: float | None,
    stress: float | None,
    crss: float | None,
) -> SystemScore:
    normal, shear = _vectors(system, c_over_a)
    schmid_tension = dot(unit(normal), unit(load)) * dot(unit(shear), unit(load))
    if system.polarity == "bidirectional":
        active = abs(schmid_tension)
    elif loading == "tension":
        active = schmid_tension if schmid_tension > ACTIVE_TOLERANCE else 0.0
    else:
        active = -schmid_tension if -schmid_tension > ACTIVE_TOLERANCE else 0.0
    if active <= ACTIVE_TOLERANCE:
        active = 0.0
    sense_ok = active > 0.0
    tau = None if stress is None else active * stress
    ratio = None
    sachs = None
    if crss is not None and sense_ok:
        sachs = crss / active
        if tau is not None:
            ratio = tau / crss
    elif crss is not None and tau is not None:
        ratio = 0.0
    return SystemScore(
        family=system.family,
        kind=system.kind,
        polarity=system.polarity,
        plane=system.plane_text,
        direction=system.direction_text,
        plane_indices=tuple(system.plane),
        direction_indices=tuple(system.direction),
        schmid_tension=schmid_tension,
        active_schmid=active,
        sense_ok=sense_ok,
        tau_MPa=tau,
        crss_MPa=crss,
        tau_over_crss=ratio,
        sachs_yield_MPa=sachs,
    )


def _rank(score: SystemScore) -> tuple:
    return (
        0 if score.sense_ok else 1,
        0 if score.tau_over_crss is not None else 1,
        -(score.tau_over_crss if score.tau_over_crss is not None else 0.0),
        -score.active_schmid,
        score.family,
        score.plane,
        score.direction,
    )


def evaluate(request: AnalysisRequest) -> AnalysisResult:
    """Rank every built-in system for one orientation. This is the calculation entry point."""
    _check_science(request)
    load = _load_cartesian(request)
    crss = request.crss_map()
    scores = [
        _score_system(
            system,
            loading=request.loading,
            load=load,
            c_over_a=request.c_over_a,
            stress=request.applied_stress_MPa,
            crss=crss.get(system.family),
        )
        for system in systems_for(request.structure)
    ]
    scores.sort(key=_rank)
    candidates = [score for score in scores if score.sachs_yield_MPa is not None]
    favored: list[SystemScore]
    sachs_yield = None
    if candidates:
        sachs_yield = min(score.sachs_yield_MPa for score in candidates if score.sachs_yield_MPa is not None)
        favored = [
            score
            for score in candidates
            if score.sachs_yield_MPa is not None and abs(score.sachs_yield_MPa - sachs_yield) <= SACHS_TIE_MPA
        ]
    else:
        positive = [score for score in scores if score.sense_ok]
        if positive:
            best = max(score.active_schmid for score in positive)
            favored = [score for score in positive if abs(score.active_schmid - best) <= ACTIVE_TOLERANCE]
        else:
            favored = []
    return AnalysisResult(
        label=request.label,
        description=request.description,
        orientation_name=request.orientation_name,
        structure=request.structure,
        c_over_a=request.c_over_a,
        c_over_a_is_default=request.c_over_a_is_default,
        loading=request.loading,
        applied_stress_MPa=request.applied_stress_MPa,
        load_frame=request.load_frame,
        load_indices=request.load_indices,
        load_xyz=request.load_xyz,
        load_cartesian=load,
        systems=tuple(scores),
        favored=tuple(favored),
        sachs_yield_MPa=sachs_yield,
    )
