"""Viewable and saved renderings of an evaluate() result."""

from __future__ import annotations

import csv
import io
import json
from xml.sax.saxutils import escape

from sliprank.friendly import verdict_lines
from sliprank.indices_display import both_forms, spaced
from sliprank.schmid import APPLICABILITY, FORMULA, AnalysisResult, SystemScore

_CRSS_WARNING = (
    "不得把本示例的 50 MPa（柱面 <a> / prismatic_a）或 100 MPa（{10-12} / twin_10_12）"
    "写成、引用为或当作任何合金（包括 α-Ti）的临界分切应力。"
)
_TWIN_SIGN = "孪晶：拉伸时 m_active = m，压缩时 m_active = −m，并且只在该值大于 0 时开动。"


def format_schmid(value: float) -> str:
    return f"{value:.6f}"


def format_signed_schmid(value: float) -> str:
    return f"{value:+.6f}"


def format_mpa(value: float) -> str:
    return f"{value:.4f}"


def format_ratio(value: float) -> str:
    return f"{value:.4f}"


def _blank(value: float | None, formatter) -> str:
    if value is None:
        return "—"
    return formatter(value)


def _data_line(label: str) -> str:
    if label == "synthetic":
        return "数据性质：合成示例，不是实测实验，也不是实测 CRSS。"
    return "数据性质：用户输入。程序不判断这些数是否来自实测。"


def _inactive_soft_note(result: AnalysisResult) -> str | None:
    supplied = [score for score in result.systems if score.crss_MPa is not None]
    if not supplied:
        return None
    softest = min(supplied, key=lambda score: (score.crss_MPa or 0.0, score.family))
    if softest.sense_ok:
        return None
    return (
        f"CRSS 最低的家族是 {softest.family}（{format_mpa(softest.crss_MPa or 0.0)} MPa），"
        "但在这个载荷方向上 m_active = 0，不进入 Sachs 估计。"
    )


def _score_dict(score: SystemScore) -> dict:
    return {
        "family": score.family,
        "kind": score.kind,
        "polarity": score.polarity,
        "plane": score.plane,
        "direction": score.direction,
        "plane_indices": list(score.plane_indices),
        "direction_indices": list(score.direction_indices),
        "schmid_tension": score.schmid_tension,
        "active_schmid": score.active_schmid,
        "active_schmid_unit": "dimensionless",
        "sense_ok": score.sense_ok,
        "tau_MPa": score.tau_MPa,
        "crss_MPa": score.crss_MPa,
        "tau_over_crss": score.tau_over_crss,
        "sachs_yield_MPa": score.sachs_yield_MPa,
    }


def _index_text(indices: tuple[int, ...] | list[int], wrapper: str, fallback: str) -> str:
    try:
        return both_forms(indices, wrapper)
    except ValueError:
        return spaced(indices, wrapper) if indices else fallback


def _has_crss(result: AnalysisResult) -> bool:
    return any(score.crss_MPa is not None for score in result.systems)


def render_report(results: list[AnalysisResult]) -> str:
    lines: list[str] = ["# SlipRank 结果", ""]
    for result in results:
        lines.extend(verdict_lines(result))
        if result.favored:
            score = result.favored[0]
            shown = _index_text(score.plane_indices, "()", score.plane) + _index_text(
                score.direction_indices, "[]", score.direction
            )
            if len(result.favored) == 1:
                lines.append(f"变体 {shown}。")
            else:
                lines.append(
                    f"代表变体 {shown}。其余 {len(result.favored) - 1} 个变体与它并列，不是单一优胜者，见全表。"
                )
        lines.append("")
    if results and results[0].description:
        lines.extend([results[0].description, ""])
    if any(result.label == "synthetic" and result.structure == "hcp" and _has_crss(result) for result in results):
        lines.extend([_CRSS_WARNING, ""])
    lines.extend(["## 公式和单位", ""])
    lines.extend(f"- {line}" for line in FORMULA)
    lines.append(f"- {_TWIN_SIGN}")
    lines.extend(["", "## 适用条件", ""])
    lines.extend(f"- {line}" for line in APPLICABILITY)
    for result in results:
        lines.extend(["", f"## 取向 {result.orientation_name}", ""])
        lines.append(f"- structure：{result.structure}")
        if result.structure == "hcp":
            source = "缺省 α-Ti 筛查值，不是实测点阵常数" if result.c_over_a_is_default else "输入值"
            lines.append(f"- c/a：{result.c_over_a}（{source}）")
        lines.append(f"- loading：{result.loading}")
        if result.applied_stress_MPa is None:
            lines.append("- 施加应力：未给出，因此不计算 τ")
        else:
            lines.append(f"- 施加应力 σ：{format_mpa(result.applied_stress_MPa)} MPa")
        if result.load_indices is not None:
            shown = _index_text(result.load_indices, "[]", str(list(result.load_indices)))
            lines.append(f"- 载荷指数（{result.load_frame}）：{shown}")
        if result.load_xyz is not None:
            lines.append(f"- 输入直角坐标：{list(result.load_xyz)}")
        cartesian = ", ".join(f"{value:.6f}" for value in result.load_cartesian)
        lines.append(f"- 晶体直角坐标中的载荷矢量：[{cartesian}]（归一化前）")
        lines.append("")
        if result.sachs_yield_MPa is None and not _has_crss(result):
            lines.append("未提供 CRSS，因此只按 Schmid 因子排序，没有 Sachs 应力。")
        elif result.sachs_yield_MPa is None:
            lines.append("取向 Sachs 屈服应力：没有可比较的系。需要 m_active > 0，并且该家族给出了 CRSS。")
        else:
            lines.append(f"取向 Sachs 屈服应力：{format_mpa(result.sachs_yield_MPa)} MPa")
        if not result.favored:
            lines.append("优先变形系：这个载荷方向上没有 m_active > 0 的变形系。")
        else:
            lines.append(f"优先变形系：{result.favored[0].family}，{len(result.favored)} 个变体并列。")
        note = _inactive_soft_note(result)
        if note:
            lines.extend(["", note])
        lines.extend(
            [
                "",
                "| 家族 | 类型 | 晶面 | 方向 | m_tension | m_active | 方向允许 | τ/MPa | CRSS/MPa | τ/CRSS | 单系 σ_y/MPa |",
                "|---|---|---|---|---:|---:|---|---:|---:|---:|---:|",
            ]
        )
        for score in result.systems:
            kind = "滑移" if score.kind == "slip" else "孪晶"
            allowed = "是" if score.sense_ok else "否"
            lines.append(
                "| "
                + " | ".join(
                    [
                        score.family,
                        kind,
                        score.plane,
                        score.direction,
                        format_signed_schmid(score.schmid_tension),
                        format_schmid(score.active_schmid),
                        allowed,
                        _blank(score.tau_MPa, format_mpa),
                        _blank(score.crss_MPa, format_mpa),
                        _blank(score.tau_over_crss, format_ratio),
                        _blank(score.sachs_yield_MPa, format_mpa),
                    ]
                )
                + " |"
            )
    if results:
        lines.extend(["", "## 先看这里", ""])
        for result in results:
            lines.extend(verdict_lines(result))
            lines.append("")
    lines.append("")
    return "\n".join(lines)


def render_csv(results: list[AnalysisResult]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "orientation",
            "family",
            "kind",
            "plane",
            "direction",
            "plane_indices",
            "direction_indices",
            "schmid_tension_dimensionless",
            "active_schmid_dimensionless",
            "sense_ok",
            "tau_MPa",
            "crss_MPa",
            "tau_over_crss",
            "sachs_yield_MPa",
        ]
    )
    for result in results:
        for score in result.systems:
            writer.writerow(
                [
                    result.orientation_name,
                    score.family,
                    score.kind,
                    score.plane,
                    score.direction,
                    ";".join(str(value) for value in score.plane_indices),
                    ";".join(str(value) for value in score.direction_indices),
                    format_signed_schmid(score.schmid_tension),
                    format_schmid(score.active_schmid),
                    "yes" if score.sense_ok else "no",
                    "" if score.tau_MPa is None else format_mpa(score.tau_MPa),
                    "" if score.crss_MPa is None else format_mpa(score.crss_MPa),
                    "" if score.tau_over_crss is None else format_ratio(score.tau_over_crss),
                    "" if score.sachs_yield_MPa is None else format_mpa(score.sachs_yield_MPa),
                ]
            )
    return buffer.getvalue()


def render_summary(results: list[AnalysisResult], input_name: str) -> str:
    payload = {
        "tool": "SlipRank",
        "input_name": input_name,
        "data_class": results[0].label if results else "",
        "formula": list(FORMULA),
        "applicability": list(APPLICABILITY),
        "units": {
            "schmid_factor": "dimensionless",
            "applied_stress": "MPa",
            "resolved_shear_stress": "MPa",
            "crss": "MPa",
            "sachs_yield_stress": "MPa",
        },
        "orientations": [
            {
                "name": result.orientation_name,
                "description": result.description,
                "structure": result.structure,
                "c_over_a": result.c_over_a,
                "c_over_a_is_default": result.c_over_a_is_default,
                "loading": result.loading,
                "applied_stress_MPa": result.applied_stress_MPa,
                "load_frame": result.load_frame,
                "load_indices": None if result.load_indices is None else list(result.load_indices),
                "load_xyz": None if result.load_xyz is None else list(result.load_xyz),
                "load_cartesian": list(result.load_cartesian),
                "sachs_yield_MPa": result.sachs_yield_MPa,
                "favored": [_score_dict(score) for score in result.favored],
                "systems": [_score_dict(score) for score in result.systems],
            }
            for result in results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_svg(results: list[AnalysisResult]) -> str:
    """Horizontal bar chart of the highest τ/CRSS, or of m_active when CRSS is absent."""
    rows: list[tuple[str, float]] = []
    for result in results:
        ranked = [score for score in result.systems if score.sense_ok]
        use_ratio = any(score.tau_over_crss is not None for score in ranked)
        if use_ratio:
            ranked = [score for score in ranked if score.tau_over_crss is not None]
            ranked.sort(key=lambda score: (-(score.tau_over_crss or 0.0), score.family, score.plane, score.direction))
            picked = [(f"{result.orientation_name} {score.family} {score.plane}{score.direction}", score.tau_over_crss or 0.0) for score in ranked[:12]]
            quantity = "tau/CRSS"
        else:
            ranked.sort(key=lambda score: (-score.active_schmid, score.family, score.plane, score.direction))
            picked = [(f"{result.orientation_name} {score.family} {score.plane}{score.direction}", score.active_schmid) for score in ranked[:12]]
            quantity = "active Schmid factor (dimensionless)"
        rows.extend(picked)
    title = "SlipRank ranking"
    if results and results[0].label == "synthetic":
        title += " — synthetic, not a measured experiment"
    width = 920
    height = 70 + max(1, len(rows)) * 28
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f4ee"/>',
        f'<text x="24" y="32" font-family="Consolas, Segoe UI, sans-serif" font-size="16" fill="#1f2933">{escape(title)}</text>',
        f'<text x="24" y="52" font-family="Consolas, Segoe UI, sans-serif" font-size="12" fill="#52606d">{escape(quantity)}</text>',
    ]
    if not rows:
        parts.append(
            '<text x="24" y="88" font-family="Consolas, Segoe UI, sans-serif" font-size="14" fill="#1f2933">No system with m_active &gt; 0.</text>'
        )
    else:
        maximum = max(value for _label, value in rows) or 1.0
        for index, (label, value) in enumerate(rows):
            y = 72 + index * 28
            bar = 560.0 * value / maximum
            parts.append(f'<rect x="300" y="{y}" width="{bar:.2f}" height="16" fill="#2f5d62"/>')
            parts.append(
                f'<text x="24" y="{y + 13}" font-family="Consolas, Segoe UI, sans-serif" font-size="12" fill="#1f2933">{escape(label[:42])}</text>'
            )
            parts.append(
                f'<text x="{308 + bar:.2f}" y="{y + 13}" font-family="Consolas, Segoe UI, sans-serif" font-size="12" fill="#1f2933">{value:.4f}</text>'
            )
    parts.append("</svg>")
    parts.append("")
    return "\n".join(parts)
