import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.metrics import (  # noqa: E402
    flip_torque_nmm,
    repeatability_monte_carlo,
    structural_metrics,
)
from foldsim.registry import load_candidates  # noqa: E402


class MetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")

    def test_flip_torque_uses_newtons_and_millimetres(self):
        self.assertAlmostEqual(flip_torque_nmm(2.0, 100.0), 1962.0)

    def test_structural_metrics_are_finite_for_every_candidate(self):
        for candidate_id, spec in self.candidates.items():
            with self.subTest(candidate=candidate_id):
                result = structural_metrics(spec)
                self.assertGreater(result["lock_stiffness_N_mm"], 0.0)
                self.assertGreaterEqual(result["peak_torque_Nmm"], 0.0)
                self.assertGreater(result["tip_deflection_mm"], 0.0)

    def test_repeatability_monte_carlo_is_seeded_and_ordered(self):
        spec = self.candidates["F07"]
        first = repeatability_monte_carlo(spec, samples=500, seed=123)
        second = repeatability_monte_carlo(spec, samples=500, seed=123)
        self.assertEqual(first["p95_mm"], second["p95_mm"])
        self.assertLessEqual(first["p50_mm"], first["p95_mm"])
        self.assertGreater(first["p95_mm"], 0.0)


if __name__ == "__main__":
    unittest.main()
