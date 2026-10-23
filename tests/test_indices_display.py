"""Display forms for Miller and Miller–Bravais indices."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sliprank.indices_display import both_forms, compact, spaced  # noqa: E402


class IndicesDisplayTest(unittest.TestCase):
    def test_spaced_wraps_components_with_spaces(self):
        self.assertEqual(spaced((1, 0, -1, 2), "()"), "(1 0 -1 2)")
        self.assertEqual(spaced((2, -1, -1, 0), "[]"), "[2 -1 -1 0]")

    def test_compact_joins_single_digits(self):
        self.assertEqual(compact((1, 0, -1, 2), "()"), "(10-12)")
        self.assertEqual(compact((2, -1, -1, 0), "[]"), "[2-1-10]")

    def test_both_forms_plane(self):
        self.assertEqual(both_forms((1, 0, -1, 2), "()"), "(10-12) = (1 0 -1 2)")

    def test_compact_rejects_two_digit_component(self):
        with self.assertRaises(ValueError) as caught:
            compact((10, 0, -1, 2), "()")
        self.assertIn("10", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
