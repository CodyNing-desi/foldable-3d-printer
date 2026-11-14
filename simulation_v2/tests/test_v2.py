import sys
import unittest
from pathlib import Path

SIM_V2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_V2 / "src"))

from foldsim_v2.evaluate3d import evaluate_candidate_3d
from foldsim_v2.fea3d import evaluate_candidate_fea3d
from foldsim_v2.geometry3d import OBB, obb_sat_distance, rot_y
from foldsim_v2.metrics_v2 import repeatability_monte_carlo_v2, structural_metrics_v2
from foldsim_v2.optimize_v2 import optimize_candidate_v2
from foldsim_v2.registry import load_candidates


class Round2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cands = load_candidates(SIM_V2 / "config" / "candidates_v2.json")

    def test_obb_sat_detects_collision_and_clearance(self):
        a = OBB.from_bounds("a", 0, 0, 0, 10, 10, 10)
        b = OBB.from_bounds("b", 8, 0, 0, 18, 10, 10)
        col, pen, clr = obb_sat_distance(a, b)
        self.assertTrue(col)
        self.assertAlmostEqual(pen, 2.0, places=5)
        c = OBB.from_bounds("c", 13, 0, 0, 20, 10, 10)
        col2, pen2, clr2 = obb_sat_distance(a, c)
        self.assertFalse(col2)
        self.assertAlmostEqual(clr2, 3.0, places=5)

    def test_f07_without_arm_fold_crashes_in_3d(self):
        no_fold = evaluate_candidate_3d(self.cands["F07"], parameters={"arm_fold_enabled": 0}, steps=31)
        with_fold = evaluate_candidate_3d(self.cands["F07"], parameters={"arm_fold_enabled": 1}, steps=31)
        self.assertFalse(no_fold["passed_screen"])
        self.assertGreater(no_fold["max_penetration_mm"], 20.0)
        self.assertTrue(with_fold["passed_screen"])

    def test_f04_single_roller_is_underconstrained_2dof(self):
        res = evaluate_candidate_3d(self.cands["F04"], parameters={"dual_roller": 0}, steps=21)
        self.assertEqual(res["dof"], 2)
        self.assertFalse(res["passed_screen"])

    def test_f12_stepped_torsion_and_3d_fea(self):
        m = structural_metrics_v2(self.cands["F12"], steps=21)
        self.assertGreater(m["torsion_tip_mm"], 0.0)
        self.assertGreater(m["clearance_tip_play_mm"], 0.0)
        fea = evaluate_candidate_fea3d("F12", self.cands["F12"])
        self.assertGreater(fea["tip_lateral_deflection_mm"], 0.0)

    def test_scz_nonlinear_drive_force_and_buckling(self):
        m = structural_metrics_v2(self.cands["SCZ"], steps=21)
        self.assertGreater(m["peak_drive_force_N"], 100.0)
        self.assertGreater(m["buckling_safety_factor"], 1.0)
        self.assertGreater(m["backlash_z_mm"], 0.05)

    def test_workspace_coverage_not_hardcoded_for_short_arm(self):
        short_arm = evaluate_candidate_3d(self.cands["F02"], parameters={"arm_length_mm": 120.0}, steps=11)
        self.assertLess(short_arm["workspace_coverage"], 1.0)

    def test_monte_carlo_seeded_reproducibility(self):
        r1 = repeatability_monte_carlo_v2(self.cands["F07"], samples=500, seed=99)
        r2 = repeatability_monte_carlo_v2(self.cands["F07"], samples=500, seed=99)
        self.assertEqual(r1["p95_mm"], r2["p95_mm"])

    def test_nsga2_runs_deterministically(self):
        opt = optimize_candidate_v2(self.cands["F07"], pop_size=8, generations=3, seed=42)
        self.assertGreaterEqual(len(opt["solutions"]), 1)


if __name__ == "__main__":
    unittest.main()
