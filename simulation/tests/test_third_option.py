import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.third_option import choose_third  # noqa: E402


class ThirdOptionTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"id": "SAFE", "storage": 0.52, "error": 0.61, "deflection": 0.32, "cost": 337, "reliability": 74.3, "robust": 1.0, "diversity": 0.0, "learning": 0.2},
            {"id": "DIVERSE", "storage": 0.47, "error": 1.04, "deflection": 0.31, "cost": 850, "reliability": 24.6, "robust": 0.0, "diversity": 1.0, "learning": 1.0},
        ]

    def test_engineering_criterion_prefers_robust_option(self):
        self.assertEqual(choose_third(self.rows, criterion="engineering"), "SAFE")

    def test_information_criterion_prefers_distinct_option(self):
        self.assertEqual(choose_third(self.rows, criterion="information"), "DIVERSE")


if __name__ == "__main__":
    unittest.main()
