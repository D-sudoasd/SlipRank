"""Wizard direction text must be accepted by the real Schmid parser.

The favored family is checked through evaluate. The active Schmid factor
from an earlier report is not copied into these assertions.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sliprank.schmid import evaluate, requests_from_mapping  # noqa: E402
from sliprank.wizard import WizardError, build_document, parse_direction  # noqa: E402


def _indices_and_frame(parsed):
    """Read indices and frame from a direction object or a load mapping."""
    if isinstance(parsed, dict):
        indices = parsed["indices"]
        frame = parsed["frame"]
    else:
        indices = parsed.indices
        frame = parsed.frame
    return [int(item) for item in indices], frame


class WizardDirectionTest(unittest.TestCase):
    def test_hcp_0001_is_miller_bravais(self):
        indices, frame = _indices_and_frame(parse_direction("hcp", "0001"))
        self.assertEqual(indices, [0, 0, 0, 1])
        self.assertEqual(frame, "miller_bravais")

    def test_compact_bracket_and_spaced_a_axis_share_indices(self):
        expected = [2, -1, -1, 0]
        for text in ("2-1-10", "[2-1-10]", "2 -1 -1 0"):
            with self.subTest(text=text):
                indices, frame = _indices_and_frame(parse_direction("hcp", text))
                self.assertEqual(indices, expected)
                self.assertEqual(frame, "miller_bravais")

    def test_compact_10_11_splits_each_digit(self):
        indices, frame = _indices_and_frame(parse_direction("hcp", "10-11"))
        self.assertEqual(indices, [1, 0, -1, 1])
        self.assertEqual(frame, "miller_bravais")

    def test_bcc_001_is_miller(self):
        for text in ("001", "0 0 1"):
            with self.subTest(text=text):
                indices, frame = _indices_and_frame(parse_direction("bcc", text))
                self.assertEqual(indices, [0, 0, 1])
                self.assertEqual(frame, "miller")

    def test_broken_zone_law_and_zero_vector_are_named(self):
        with self.assertRaises(WizardError) as zone:
            parse_direction("hcp", "1001")
        self.assertIn("u+v+t=0", str(zone.exception))
        with self.assertRaises(WizardError) as zero:
            parse_direction("hcp", "0000")
        self.assertIn("零矢量", str(zero.exception))


class WizardDocumentTest(unittest.TestCase):
    def test_c_axis_tension_without_crss_favors_all_six_twin_10_12(self):
        document = build_document(
            structure="hcp",
            loading="拉伸",
            direction="0001",
            stress_MPa=400,
            label="synthetic",
        )
        self.assertIsInstance(document, dict)
        self.assertNotIn("crss_MPa", document)
        self.assertEqual(document["label"], "synthetic")
        self.assertEqual(document["structure"], "hcp")
        self.assertEqual(document["loading"], "tension")
        self.assertEqual(document["applied_stress_MPa"], 400)
        request = requests_from_mapping(document)[0]
        self.assertEqual(request.crss_MPa, ())
        self.assertEqual(request.loading, "tension")
        self.assertEqual(request.load_frame, "miller_bravais")
        self.assertEqual(list(request.load_indices), [0, 0, 0, 1])
        self.assertEqual(request.applied_stress_MPa, 400)
        result = evaluate(request)
        self.assertGreater(len(result.systems), 0)
        self.assertEqual(len(result.favored), 6)
        self.assertTrue(all(score.family == "twin_10_12" for score in result.favored))
        for score in result.favored:
            self.assertGreater(score.active_schmid, 0.4)

    def test_compression_is_stored_as_compression(self):
        document = build_document(
            structure="hcp",
            loading="压缩",
            direction="0001",
            stress_MPa=400,
            label="synthetic",
        )
        self.assertEqual(document["loading"], "compression")
        self.assertNotIn("crss_MPa", document)
        request = requests_from_mapping(document)[0]
        self.assertEqual(request.loading, "compression")


if __name__ == "__main__":
    unittest.main()
