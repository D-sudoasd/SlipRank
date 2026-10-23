"""Short Chinese lines for the top of one SlipRank report."""

from __future__ import annotations

from sliprank.schmid import AnalysisResult, SystemScore

FAMILY_ZH = {
    "basal_a": "基面 <a> 滑移",
    "prismatic_a": "柱面 <a> 滑移",
    "pyramidal_a": "锥面 <a> 滑移",
    "pyramidal_ca_I": "一阶锥面 <c+a> 滑移",
    "pyramidal_ca_II": "二阶锥面 <c+a> 滑移",
    "twin_10_12": "{10-12} 拉伸孪晶",
    "twin_11_22": "{11-22} 压缩孪晶",
    "twin_10_11": "{10-11} 压缩孪晶",
    "slip_110": "{110}<111> 滑移",
    "slip_112": "{112}<111> 滑移",
    "slip_123": "{123}<111> 滑移",
}


def family_zh(family: str) -> str:
    return FAMILY_ZH.get(family, family)


def _mpa(value: float) -> str:
    return f"{value:.4f}"


def _loading_zh(loading: str) -> str:
    if loading == "tension":
        return "拉伸"
    if loading == "compression":
        return "压缩"
    return loading


def _header(result: AnalysisResult) -> str:
    loading = _loading_zh(result.loading)
    text = f"取向 {result.orientation_name}，结构 {result.structure}，载荷为{loading}"
    if result.applied_stress_MPa is not None:
        text += f"，施加应力 {_mpa(result.applied_stress_MPa)} MPa"
    text += "。"
    if result.label == "synthetic":
        return "合成示例。" + text
    return text


def _favored_line(result: AnalysisResult) -> str:
    if not result.favored:
        return f"在此{_loading_zh(result.loading)}方向上没有 m_active > 0 的变形系。"
    top = result.favored[0]
    count = len(result.favored)
    same_family = all(score.family == top.family for score in result.favored)
    if same_family:
        variant = f"{family_zh(top.family)}，{count} 个变体"
        if count > 1:
            variant += "并列"
    else:
        seen: list[str] = []
        for score in result.favored:
            if score.family not in seen:
                seen.append(score.family)
        variant = f"{family_zh(top.family)} 等 {len(seen)} 个家族，共 {count} 个变体并列"
    schmid = f"{top.active_schmid:.6f}"
    same_schmid = all(f"{score.active_schmid:.6f}" == schmid for score in result.favored)
    same_tau = True
    if top.tau_MPa is not None:
        tau_text = _mpa(top.tau_MPa)
        same_tau = all(score.tau_MPa is not None and _mpa(score.tau_MPa) == tau_text for score in result.favored)
    detail = f"active Schmid 因子 {schmid}（无量纲）"
    if not same_schmid or not same_tau:
        detail = "首个变体 " + detail
    if top.tau_MPa is not None:
        detail += f"，τ = {_mpa(top.tau_MPa)} MPa"
    return f"优先变形系为{variant}，{detail}。"


def _sachs_line(result: AnalysisResult) -> str:
    if result.sachs_yield_MPa is not None:
        return f"单晶 Sachs 估计为 {_mpa(result.sachs_yield_MPa)} MPa，由所给 CRSS 得到。"
    comparable = any(
        isinstance(score, SystemScore) and score.sense_ok and score.crss_MPa is not None for score in result.systems
    )
    if comparable:
        return "未给出单晶 Sachs 估计。"
    return "没有可以开动、且已给出 CRSS 的变形系，因此没有单晶 Sachs 估计。"


def _lowest_crss(result: AnalysisResult) -> float | None:
    values = [score.crss_MPa for score in result.systems if score.crss_MPa is not None]
    if not values:
        return None
    return min(values)


def _families_at_lowest(result: AnalysisResult, lowest: float) -> list[str]:
    families: list[str] = []
    for score in result.systems:
        if score.crss_MPa == lowest and score.family not in families:
            families.append(score.family)
    return families


def _family_is_inactive(result: AnalysisResult, family: str) -> bool:
    systems = [score for score in result.systems if score.family == family]
    return bool(systems) and all(not score.sense_ok for score in systems)


def _crss_line(result: AnalysisResult) -> str:
    # A low CRSS enters the Sachs estimate only if that family has some sense_ok system.
    lowest = _lowest_crss(result)
    if lowest is None:
        return "未提供 CRSS，因此只按 Schmid 因子排序，没有 Sachs 应力。"
    families = _families_at_lowest(result, lowest)
    inactive = [family for family in families if _family_is_inactive(result, family)]
    if inactive:
        named = "、".join(f"{family_zh(family)}（{_mpa(lowest)} MPa）" for family in inactive)
        return f"所给 CRSS 最低的{named}在此方向不可开动，其低 CRSS 不进入 Sachs 估计。"
    named = "、".join(family_zh(family) for family in families)
    return f"所给 CRSS 最低的是{named}（{_mpa(lowest)} MPa），此方向有 m_active > 0 的变体。"


def verdict_lines(result: AnalysisResult) -> list[str]:
    lines = [_header(result), _favored_line(result), _sachs_line(result), _crss_line(result)]
    if result.applied_stress_MPa is None:
        lines.append("未给出施加应力，因此不计算 τ。")
    return lines
