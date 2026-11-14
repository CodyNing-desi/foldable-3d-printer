import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.optimize import CandidateProblem, optimize_candidate  # noqa: E402
from foldsim.registry import load_candidates  # noqa: E402


class OptimizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")

    def test_design_evaluation_has_scaled_objectives_and_constraints(self):
        spec = self.candidates["F07"]
        problem = CandidateProblem(spec)
        values = problem.evaluate_design([120.0, 0.0])
        self.assertEqual(len(values["objectives"]), 4)
        self.assertEqual(len(values["constraints"]), 5)
        self.assertLess(values["constraints"][0], 0.0)

    def test_nsga2_executes_with_fixed_seed(self):
        result = optimize_candidate(self.candidates["F07"], pop_size=6, generations=2, seed=77)
        self.assertGreaterEqual(len(result["solutions"]), 1)
        self.assertEqual(result["seed"], 77)
        self.assertEqual(result["algorithm"], "NSGA-II")


if __name__ == "__main__":
    unittest.main()
