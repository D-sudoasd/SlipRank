"""Independent checks of the shipped Schmid ranking.

The expected numbers are closed forms, not snapshots of an earlier run:

- Basal (0001)[2-1-10] with a load at 45 degrees between [2-1-10] and [0001]
  has m = cos(45) cos(45) = 1/2.
- BCC (101)[11-1] loaded along [001] has |m| = 1/sqrt(6).
- HCP {10-12} tension along [0001] reduces to
  m = 1/sqrt(2 + (c/a)^2/3 + 3/(c/a)^2).
  The reduction is written in the test docstring below.
"""

from __future__ import annotations

import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sliprank.catalog import systems_for  # noqa: E402
from sliprank.geometry import norm, zone_integer  # noqa: E402
from sliprank.report import format_mpa, format_ratio, format_schmid  # noqa: E402
from sliprank.schmid import (  # noqa: E402
    SlipRankError,
    evaluate,
    plane_normal_and_shear,
    requests_from_mapping,
)
from sliprank.cli import main  # noqa: E402

GAMMA = 1.587
EXAMPLE = ROOT / "examples" / "c_axis_tension.json"
BCC_EXAMPLE = ROOT / "examples" / "bcc_001_tension.json"
BAD_EXAMPLE = ROOT / "examples" / "bad_zero_load.json"

HCP_COUNTS = {
    "basal_a": 3,
    "prismatic_a": 3,
    "pyramidal_a": 6,
    "pyramidal_ca_I": 12,
    "pyramidal_ca_II": 6,
    "twin_10_12": 6,
    "twin_11_22": 6,
    "twin_10_11": 6,
}
BCC_COUNTS = {"slip_110": 12, "slip_112": 12, "slip_123": 24}


def twin_10_12_c_axis(gamma: float) -> float:
    """Schmid factor of (10-12)[-1011] for tension along [0001].

    n = (1, 1/sqrt(3), 2/gamma)
    s = (-3/2, -sqrt(3)/2, gamma)
    l = (0, 0, 1)
    m = (n·l)(s·l) / (|n| |s|) = 1/sqrt(2 + gamma^2/3 + 3/gamma^2)
    """
    return 1.0 / math.sqrt(2.0 + (gamma ** 2) / 3.0 + 3.0 / (gamma ** 2))


def twin_11_22_c_axis_magnitude(gamma: float) -> float:
    """Absolute Schmid factor of (11-22)[11-2-3] along [0001].

    m_tension = -1/sqrt(2 + gamma^2 + 1/gamma^2)
    Compression therefore has m_active = 1/sqrt(2 + gamma^2 + 1/gamma^2).
    """
    return 1.0 / math.sqrt(2.0 + gamma ** 2 + 1.0 / (gamma ** 2))


def hcp_request(**overrides):
    payload = {
        "label": "synthetic",
        "description": "unit test",
        "structure": "hcp",
        "c_over_a": GAMMA,
        "loading": "tension",
        "orientation_name": "test",
        "load": {"frame": "miller_bravais", "indices": [0, 0, 0, 1]},
    }
    payload.update(overrides)
    return requests_from_mapping(payload)[0]


class SchmidReferenceTest(unittest.TestCase):
    def test_catalog_counts_and_zone_law(self):
        self.assertEqual(Counter(system.family for system in systems_for("hcp")), HCP_COUNTS)
        self.assertEqual(Counter(system.family for system in systems_for("bcc")), BCC_COUNTS)
        for structure, gamma in (("hcp", GAMMA), ("bcc", None)):
            for system in systems_for(structure):
                self.assertEqual(zone_integer(system.plane, system.direction), 0, system)
                normal, shear = plane_normal_and_shear(system, gamma)
                cosine = abs(sum(a * b for a, b in zip(normal, shear))) / (norm(normal) * norm(shear))
                self.assertLess(cosine, 1e-9, system)

    def test_hcp_embedding_components_for_tension_twin(self):
        system = next(
            item
            for item in systems_for("hcp")
            if item.plane == (1, 0, -1, 2) and item.direction == (-1, 0, 1, 1)
        )
        normal, shear = plane_normal_and_shear(system, GAMMA)
        self.assertAlmostEqual(normal[0], 1.0, delta=1e-12)
        self.assertAlmostEqual(normal[1], 1.0 / math.sqrt(3.0), delta=1e-12)
        self.assertAlmostEqual(normal[2], 2.0 / GAMMA, delta=1e-12)
        self.assertAlmostEqual(shear[0], -1.5, delta=1e-12)
        self.assertAlmostEqual(shear[1], -math.sqrt(3.0) / 2.0, delta=1e-12)
        self.assertAlmostEqual(shear[2], GAMMA, delta=1e-12)

    def test_basal_forty_five_degrees_is_one_half(self):
        request = hcp_request(load={"frame": "cartesian", "xyz": [1.0, 0.0, 1.0]})
        result = evaluate(request)
        row = next(
            score
            for score in result.systems
            if score.family == "basal_a" and score.plane == "(0001)" and score.direction == "[2-1-10]"
        )
        self.assertAlmostEqual(row.schmid_tension, 0.5, delta=1e-12)
        self.assertAlmostEqual(row.active_schmid, 0.5, delta=1e-12)

    def test_c_axis_tension_twin_matches_closed_form(self):
        result = evaluate(hcp_request())
        expected = twin_10_12_c_axis(GAMMA)
        rows = [score for score in result.systems if score.family == "twin_10_12"]
        self.assertEqual(len(rows), 6)
        for score in rows:
            self.assertAlmostEqual(score.schmid_tension, expected, delta=1e-12)
            self.assertAlmostEqual(score.active_schmid, expected, delta=1e-12)
            self.assertTrue(score.sense_ok)
        basal = [score for score in result.systems if score.family == "basal_a"]
        self.assertTrue(all(score.active_schmid == 0.0 for score in basal))

    def test_c_axis_compression_reverses_twin_polarity(self):
        result = evaluate(hcp_request(loading="compression"))
        tension = twin_10_12_c_axis(GAMMA)
        compression = twin_11_22_c_axis_magnitude(GAMMA)
        for score in result.systems:
            if score.family == "twin_10_12":
                self.assertAlmostEqual(score.schmid_tension, tension, delta=1e-12)
                self.assertEqual(score.active_schmid, 0.0)
                self.assertFalse(score.sense_ok)
            if score.family == "twin_11_22":
                self.assertAlmostEqual(score.active_schmid, compression, delta=1e-12)
                self.assertTrue(score.sense_ok)

    def test_bcc_001_matches_one_over_sqrt_six(self):
        document = json.loads(BCC_EXAMPLE.read_text(encoding="utf-8"))
        result = evaluate(requests_from_mapping(document)[0])
        expected = 1.0 / math.sqrt(6.0)
        row = next(score for score in result.systems if score.plane == "(101)" and score.direction == "[11-1]")
        self.assertAlmostEqual(row.schmid_tension, -expected, delta=1e-12)
        self.assertAlmostEqual(row.active_schmid, expected, delta=1e-12)
        self.assertTrue(all(score.family == "slip_110" for score in result.favored))
        self.assertEqual(len(result.favored), 8)
        crss = document["crss_MPa"]["slip_110"]
        self.assertAlmostEqual(result.sachs_yield_MPa, crss * math.sqrt(6.0), delta=1e-9)

    def test_shipped_hcp_example_matches_closed_form(self):
        document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        result = evaluate(requests_from_mapping(document)[0])
        expected = twin_10_12_c_axis(document["c_over_a"])
        self.assertEqual(document["label"], "synthetic")
        self.assertTrue(all(score.family == "twin_10_12" for score in result.favored))
        self.assertEqual(len(result.favored), 6)
        for score in result.favored:
            self.assertAlmostEqual(score.active_schmid, expected, delta=1e-12)
        crss = document["crss_MPa"]["twin_10_12"]
        stress = document["applied_stress_MPa"]
        self.assertAlmostEqual(result.sachs_yield_MPa, crss / expected, delta=1e-9)
        self.assertAlmostEqual(result.favored[0].tau_MPa, expected * stress, delta=1e-9)

    def test_orientation_array_keeps_each_load(self):
        document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        document["orientations"] = [
            {"orientation_name": "c-axis", "load": {"frame": "miller_bravais", "indices": [0, 0, 0, 1]}},
            {"orientation_name": "a-axis", "load": {"frame": "miller_bravais", "indices": [2, -1, -1, 0]}},
        ]
        requests = requests_from_mapping(document)
        self.assertEqual([item.orientation_name for item in requests], ["c-axis", "a-axis"])
        c_result = evaluate(requests[0])
        a_result = evaluate(requests[1])
        self.assertAlmostEqual(c_result.favored[0].active_schmid, twin_10_12_c_axis(GAMMA), delta=1e-12)
        self.assertEqual(len(a_result.systems), sum(HCP_COUNTS.values()))
        self.assertEqual(a_result.load_cartesian[2], 0.0)
        self.assertGreater(c_result.load_cartesian[2], 0.0)

    def test_bad_inputs_name_the_problem(self):
        with self.assertRaises(SlipRankError) as zero_vector:
            evaluate(hcp_request(load={"frame": "miller_bravais", "indices": [0, 0, 0, 0]}))
        self.assertIn("零矢量", str(zero_vector.exception))
        with self.assertRaises(SlipRankError) as zone:
            evaluate(hcp_request(load={"frame": "miller_bravais", "indices": [1, 0, 0, 1]}))
        message = str(zone.exception)
        self.assertIn("u+v+t=0", message)
        self.assertIn("[1, 0, 0, 1]", message)
        with self.assertRaises(SlipRankError) as crss:
            evaluate(hcp_request(crss_MPa={"prismatic_a": -5}))
        self.assertIn("prismatic_a", str(crss.exception))
        self.assertIn("MPa", str(crss.exception))
        with self.assertRaises(SlipRankError) as stress:
            evaluate(hcp_request(applied_stress_MPa=0))
        self.assertIn("applied_stress_MPa", str(stress.exception))

    def test_cli_example_saves_reference_values_and_repeats(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = Path(first_dir)
            second = Path(second_dir)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(EXAMPLE), "--out", str(first)]), 0)
                self.assertEqual(main([str(EXAMPLE), "--out", str(second)]), 0)
            names = ("report.md", "systems.csv", "summary.json", "ranking.svg")
            for name in names:
                self.assertGreater((first / name).stat().st_size, 0)
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            document = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            expected = twin_10_12_c_axis(document["c_over_a"])
            crss = document["crss_MPa"]["twin_10_12"]
            stress = document["applied_stress_MPa"]
            report = (first / "report.md").read_text(encoding="utf-8")
            self.assertIn(format_schmid(expected), report)
            self.assertIn(format_mpa(crss / expected), report)
            self.assertIn(format_mpa(expected * stress), report)
            self.assertIn(format_ratio(expected * stress / crss), report)
            self.assertIn("MPa", report)
            self.assertIn("无量纲", report)
            self.assertIn("合成示例", report)
            summary = json.loads((first / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["units"]["schmid_factor"], "dimensionless")
            self.assertEqual(summary["units"]["sachs_yield_stress"], "MPa")
            self.assertEqual(summary["data_class"], "synthetic")
            favored = summary["orientations"][0]["favored"]
            self.assertEqual(len(favored), 6)
            self.assertAlmostEqual(favored[0]["active_schmid"], expected, delta=1e-12)
            self.assertIn("<svg", (first / "ranking.svg").read_text(encoding="utf-8"))

    def test_cli_bad_file_names_zero_vector_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out"
            with redirect_stderr(io.StringIO()):
                code = main([str(BAD_EXAMPLE), "--out", str(out)])
            self.assertEqual(code, 2)
            self.assertFalse(out.exists())
        completed = subprocess.run(
            [sys.executable, "-m", "sliprank", str(BAD_EXAMPLE), "--out", str(Path(directory) / "unused")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("零矢量", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
