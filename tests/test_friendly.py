"""Plain-language verdict lines for one Schmid ranking."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sliprank.friendly import family_zh, verdict_lines  # noqa: E402
from sliprank.schmid import AnalysisResult, SystemScore  # noqa: E402


def _score(**overrides) -> SystemScore:
    fields = {
        "family": "twin_10_12",
        "kind": "twin",
        "polarity": "unidirectional",
        "plane": "(10-12)",
        "direction": "[-1011]",
        "plane_indices": (1, 0, -1, 2),
        "direction_indices": (-1, 0, 1, 1),
        "schmid_tension": 0.5,
        "active_schmid": 0.5,
        "sense_ok": True,
        "tau_MPa": 200.0,
        "crss_MPa": 100.0,
        "tau_over_crss": 2.0,
        "sachs_yield_MPa": 200.0,
    }
    fields.update(overrides)
    return SystemScore(**fields)


def _result(
    systems: tuple[SystemScore, ...],
    favored: tuple[SystemScore, ...],
    **overrides,
) -> AnalysisResult:
    fields = {
        "label": "synthetic",
        "description": "unit test",
        "orientation_name": "c-axis",
        "structure": "hcp",
        "c_over_a": 1.587,
        "c_over_a_is_default": False,
        "loading": "tension",
        "applied_stress_MPa": 400.0,
        "load_frame": "miller_bravais",
        "load_indices": (0, 0, 0, 1),
        "load_xyz": None,
        "load_cartesian": (0.0, 0.0, 1.587),
        "systems": systems,
        "favored": favored,
        "sachs_yield_MPa": 200.0,
    }
    fields.update(overrides)
    return AnalysisResult(**fields)


def _text(result: AnalysisResult) -> str:
    lines = verdict_lines(result)
    if isinstance(lines, str):
        return lines
    return "\n".join(lines)


class FriendlyVerdictTest(unittest.TestCase):
    def test_family_zh_tension_twin_and_unknown_key(self):
        self.assertEqual(family_zh("twin_10_12"), "{10-12} 拉伸孪晶")
        self.assertEqual(family_zh("not_a_family"), "not_a_family")

    def test_synthetic_favored_twin_quotes_schmid_and_stress(self):
        twin = _score()
        text = _text(_result((twin,), (twin,)))
        self.assertIn("合成示例", text)
        self.assertIn("拉伸孪晶", text)
        self.assertIn("0.500000", text)
        self.assertIn("200.0000", text)
        self.assertIn("MPa", text)

    def test_empty_favored_says_no_system_operates_and_skips_sachs(self):
        idle = _score(
            sense_ok=False,
            active_schmid=0.0,
            schmid_tension=0.0,
            tau_MPa=None,
            crss_MPa=None,
            tau_over_crss=None,
            sachs_yield_MPa=None,
        )
        text = _text(
            _result(
                (idle,),
                (),
                label="user",
                applied_stress_MPa=None,
                sachs_yield_MPa=None,
            )
        )
        self.assertTrue(
            (
                "m_active" in text
                and any(token in text for token in ("没有", "无", "不存在", "不能", "无法"))
            )
            or any(
                phrase in text
                for phrase in (
                    "不能开动",
                    "无法开动",
                    "没有开动",
                    "未能开动",
                    "没有变形系能够开动",
                    "没有系统能够开动",
                    "没有系统可以开动",
                    "没有变形系可以开动",
                )
            ),
            text,
        )
        self.assertNotRegex(text, r"Sachs[^。\n]*\d")
        self.assertNotRegex(text, r"\d[^。\n]*Sachs")
        self.assertNotRegex(text, re.compile(r"\d+(?:\.\d+)?\s*MPa"))

    def test_soft_prismatic_with_wrong_sense_is_inactive(self):
        twin = _score()
        prism = _score(
            family="prismatic_a",
            kind="slip",
            polarity="bidirectional",
            plane="(10-10)",
            direction="[1-210]",
            plane_indices=(1, 0, -1, 0),
            direction_indices=(1, -2, 1, 0),
            schmid_tension=0.0,
            active_schmid=0.0,
            sense_ok=False,
            tau_MPa=0.0,
            crss_MPa=50.0,
            tau_over_crss=0.0,
            sachs_yield_MPa=None,
        )
        text = _text(_result((prism, twin), (twin,)))
        self.assertIn("柱面", text)
        self.assertTrue(
            any(
                token in text
                for token in (
                    "不活动",
                    "未开动",
                    "不能开动",
                    "没有开动",
                    "不进入",
                    "不会进入",
                    "未进入",
                    "不参与",
                    "未参与",
                    "不计入",
                    "不纳入",
                    "不起作用",
                    "未激活",
                    "不能启动",
                    "未启动",
                    "m_active = 0",
                    "m_active=0",
                    "m_active 为 0",
                )
            ),
            text,
        )


if __name__ == "__main__":
    unittest.main()
