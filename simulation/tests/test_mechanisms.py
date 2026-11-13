import math
import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.mechanisms import build_trace, scissor_state  # noqa: E402
from foldsim.registry import load_candidates  # noqa: E402
from foldsim.evaluate import evaluate_candidate  # noqa: E402


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")

    def test_all_required_candidates_are_present_once(self):
        expected = {f"F{i:02d}" for i in range(1, 15)} | {"SCZ"}
        self.assertEqual(set(self.candidates), expected)
        self.assertEqual(len(self.candidates), 15)

    def test_every_candidate_has_executable_trace_and_units(self):
        for candidate_id, spec in self.candidates.items():
            with self.subTest(candidate=candidate_id):
                self.assertEqual(spec["units"]["length"], "mm")
                trace = build_trace(spec, steps=11)
                self.assertEqual(len(trace), 11)
                self.assertTrue(all(math.isfinite(p["pivot_x_mm"]) for p in trace))
                result = evaluate_candidate(spec, steps=11)
                for key in (
                    "folded_volume_mm3", "storage_ratio", "max_intersection_mm2",
                    "workspace_coverage", "reachable_fraction", "passed_screen",
                ):
                    self.assertIn(key, result)


class KinematicsTests(unittest.TestCase):
    def test_scissor_height_and_jacobian_match_finite_difference(self):
        state = scissor_state(150.0, 180.0)
        self.assertAlmostEqual(state["height_mm"], math.sqrt(4 * 150.0**2 - 180.0**2))
        step = 1e-4
        finite = (
            scissor_state(150.0, 180.0 + step)["height_mm"]
            - scissor_state(150.0, 180.0 - step)["height_mm"]
        ) / (2 * step)
        self.assertAlmostEqual(state["dH_dS"], finite, places=7)

    def test_scissor_rejects_unreachable_span(self):
        with self.assertRaises(ValueError):
            scissor_state(100.0, 201.0)

    def test_root_fold_collision_and_raised_fold_clearance_differ(self):
        candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
        pure = evaluate_candidate(candidates["F01"], steps=31)
        raised = evaluate_candidate(candidates["F07"], steps=31)
        self.assertGreater(pure["max_intersection_mm2"], 1.0)
        self.assertLess(raised["max_intersection_mm2"], 1e-6)

    def test_scissor_raised_pins_clear_the_base(self):
        candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
        result = evaluate_candidate(candidates["SCZ"], steps=31)
        self.assertLess(result["max_intersection_mm2"], 1e-6)

    def test_telescoping_three_stage_is_not_taller_than_two_stage(self):
        candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
        two = evaluate_candidate(candidates["F05"], steps=11)
        three = evaluate_candidate(candidates["F12"], steps=11)
        self.assertLess(three["folded_height_mm"], two["folded_height_mm"])
        self.assertEqual(two["workspace_coverage"], 1.0)
        self.assertEqual(three["workspace_coverage"], 1.0)


if __name__ == "__main__":
    unittest.main()
