import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.convergence import sweep_convergence  # noqa: E402
from foldsim.registry import load_candidates  # noqa: E402


class ConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")

    def test_recommended_geometry_is_stable_from_201_to_1001_states(self):
        rows = sweep_convergence(
            self.candidates["F07"],
            parameters={"lift_mm": 80.0, "shift_x_mm": 0.0},
            step_counts=(201, 501, 1001),
        )
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["passed_screen"] for row in rows))
        self.assertTrue(all(row["max_intersection_mm2"] == 0.0 for row in rows))

    def test_pure_root_failure_persists_under_denser_sampling(self):
        rows = sweep_convergence(self.candidates["F01"], step_counts=(201, 1001))
        self.assertTrue(all(not row["passed_screen"] for row in rows))
        self.assertTrue(all(row["max_intersection_mm2"] > 1.0 for row in rows))


if __name__ == "__main__":
    unittest.main()
