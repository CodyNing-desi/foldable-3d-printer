import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.selection import pareto_mask, choose_diverse  # noqa: E402


class SelectionTests(unittest.TestCase):
    def test_pareto_mask_excludes_dominated_point(self):
        self.assertEqual(pareto_mask([[0.2, 0.3], [0.4, 0.5], [0.3, 0.2]]), [True, False, True])

    def test_recommendations_do_not_share_family_group(self):
        rows = [
            {"id": "A", "family_group": "root", "robust_frequency": 1.0, "baseline_score": 0.1},
            {"id": "B", "family_group": "root", "robust_frequency": 0.9, "baseline_score": 0.2},
            {"id": "C", "family_group": "scissor", "robust_frequency": 0.8, "baseline_score": 0.3},
            {"id": "D", "family_group": "case", "robust_frequency": 0.7, "baseline_score": 0.4},
        ]
        self.assertEqual(choose_diverse(rows, count=3), ["A", "C", "D"])
        self.assertEqual(choose_diverse(rows[:3], count=3, fill_same_family=False), ["A", "C"])


if __name__ == "__main__":
    unittest.main()
