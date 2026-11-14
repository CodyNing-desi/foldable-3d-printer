import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.mechanisms import build_trace
from foldsim.metrics import repeatability_monte_carlo, structural_metrics
from foldsim.optimize import CandidateProblem, optimize_candidate
from foldsim.registry import load_candidates


class ReviewRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")

    def test_guided_route_has_real_slot_rail_and_roller(self):
        trace = build_trace(self.candidates["F04"], steps=31)
        for state in trace:
            self.assertIn("slot_rail", state["fixed"])
            self.assertIn("roller", state["moving"])
            self.assertGreater(state["slot_side_clearance_mm"], 0.0)
        self.assertNotEqual(trace[0]["pivot_z_mm"], trace[-1]["pivot_z_mm"])

    def test_arm_length_changes_error_and_deflection(self):
        spec = self.candidates["F02"]
        short = structural_metrics(spec, parameters={"arm_length_mm": 180.0})
        long = structural_metrics(spec, parameters={"arm_length_mm": 260.0})
        self.assertNotEqual(short["tip_deflection_mm"], long["tip_deflection_mm"])
        short_error = repeatability_monte_carlo(spec, parameters={"arm_length_mm": 180.0}, samples=500)
        long_error = repeatability_monte_carlo(spec, parameters={"arm_length_mm": 260.0}, samples=500)
        self.assertNotEqual(short_error["p95_mm"], long_error["p95_mm"])

    def test_telescope_and_drawer_drive_models_are_not_zero_torque_aliases(self):
        telescope = structural_metrics(self.candidates["F12"])
        drawer = structural_metrics(self.candidates["F13"])
        self.assertGreater(telescope["peak_drive_force_N"], self.candidates["F12"]["mass_kg"] * 9.81)
        self.assertGreater(drawer["peak_drive_force_N"], 0.0)
        self.assertIn("vertical telescope", telescope["drive_model"])
        self.assertIn("horizontal drawer", drawer["drive_model"])

    def test_external_combo_has_two_stage_rotation_and_double_gantry(self):
        trace = build_trace(self.candidates["F14"], steps=31)
        self.assertIn("column_right", trace[0]["moving"])
        self.assertGreater(trace[-1]["stow_angle_deg"], 0.0)
        self.assertGreater(abs(trace[-1]["angle_deg"]), abs(trace[20]["angle_deg"]))

    def test_case_has_moving_lid_and_self_collision_enabled(self):
        trace = build_trace(self.candidates["F11"], steps=31)
        self.assertIn("lid", trace[0]["moving"])
        self.assertTrue(trace[0]["check_self_collision"])
        self.assertNotEqual(trace[0]["moving"]["lid"].bounds, trace[-1]["moving"]["lid"].bounds)

    def test_guided_optimization_keeps_fixed_roller_parameter(self):
        problem = CandidateProblem(self.candidates["F04"])
        values = problem.evaluate_design([70.0, 20.0, 12.0])
        self.assertEqual(len(values["constraints"]), 5)

    def test_optimization_has_reachability_constraint_and_least_infeasible_record(self):
        spec = self.candidates["F07"]
        self.assertEqual(len(CandidateProblem(spec).evaluate_design([120.0, 0.0])["constraints"]), 5)
        result = optimize_candidate(self.candidates["F02"], pop_size=4, generations=1, seed=9)
        self.assertIn("least_infeasible", result)
        self.assertIn("constraints", result["least_infeasible"])


if __name__ == "__main__":
    unittest.main()
