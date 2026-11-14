"""Post-fix verification tests for V3.1 (all V3 bugs resolved)."""

import sys
import unittest
from pathlib import Path

SIM_V31 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_V31 / "src"))

import numpy as np
from foldsim_v3_1.evaluate3d import evaluate_candidate_3d
from foldsim_v3_1.fea3d import evaluate_candidate_fea3d
from foldsim_v3_1.geometry3d import OBB, rot_y, swept_obb_vs_obstacle
from foldsim_v3_1.registry import load_candidates


class V31FixVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cands = load_candidates(SIM_V31 / "config" / "candidates_v3_1.json")

    def test_swept_catches_x25_translation_and_thin_wall(self):
        """Post-fix: moving X=0->100 catches 0.5mm thin wall at X=25."""
        obs = OBB.from_bounds("thin_wall", 24.75, -10.0, 0.0, 25.25, 10.0, 10.0, group="fixed")
        m_a = OBB.from_bounds("slider", -5.0, -5.0, 0.0, 5.0, 5.0, 10.0)
        m_b = OBB.from_bounds("slider", 95.0, -5.0, 0.0, 105.0, 5.0, 10.0)
        col, pen, _, n_sub = swept_obb_vs_obstacle(m_a, m_b, obs, step_bound_mm=2.0, inflate=True)
        self.assertTrue(col)
        self.assertGreater(pen, 0.2)
        self.assertGreaterEqual(n_sub, 40)

    def test_swept_catches_rotation_and_combined_motion(self):
        """Post-fix: rotating + translating arm catches obstacle along arc."""
        obs = OBB.from_bounds("post", 48.0, -5.0, 48.0, 52.0, 5.0, 52.0, group="fixed")
        arm_a = OBB.from_bounds("arm", -2.0, -2.0, 0.0, 2.0, 2.0, 80.0)
        arm_b = arm_a.transformed(rotation=rot_y(90.0), origin=np.array([0.0, 0.0, 0.0]), translation=np.array([10.0, 0.0, 0.0]))
        col, pen, _, _ = swept_obb_vs_obstacle(arm_a, arm_b, obs, step_bound_mm=2.0, inflate=True)
        self.assertTrue(col)
        self.assertGreater(pen, 0.0)

    def test_f09_uses_215mm_cantilever_load_and_three_axes(self):
        """Post-fix: F09 FEA loads 215mm X-arm tip, NOT crossbar center (0.030mm)."""
        r_comp = evaluate_candidate_fea3d("F09", self.cands["F09"], n_sub=16, ideal_rigid_joints=False)
        r_ideal = evaluate_candidate_fea3d("F09", self.cands["F09"], n_sub=16, ideal_rigid_joints=True)
        self.assertGreater(r_comp["tip_y_deflection_mm"], 0.12)
        self.assertLess(r_ideal["tip_y_deflection_mm"], r_comp["tip_y_deflection_mm"])
        self.assertGreater(r_comp["tip_z_deflection_mm"], 0.0)
        self.assertGreater(r_comp["tip_x_deflection_mm"], 0.0)

    def test_scz_fea_dofs_scale_with_nsub(self):
        """Post-fix: SCZ FEA DOFs genuinely scale with n_sub."""
        dofs = [evaluate_candidate_fea3d("SCZ", self.cands["SCZ"], n_sub=n)["dofs"] for n in (1, 2, 4, 8)]
        self.assertEqual(dofs, [60, 132, 276, 564])

    def test_f07_and_f08_pass_with_positive_clearance(self):
        """Post-fix: F07 (lift=75, shift_x=0) and F08 (lift=25, shift_x=-75) pass swept 3D check."""
        r07 = evaluate_candidate_3d(self.cands["F07"], parameters={"lift_mm": 75.0, "shift_x_mm": 0.0}, steps=101, swept_check=True, step_bound_mm=0.5)
        r08 = evaluate_candidate_3d(self.cands["F08"], parameters={"lift_mm": 25.0, "shift_x_mm": -75.0}, steps=101, swept_check=True, step_bound_mm=0.5)
        self.assertTrue(r07["passed_screen"], r07["screen_reasons"])
        self.assertTrue(r08["passed_screen"], r08["screen_reasons"])
        self.assertEqual(r07["max_penetration_mm"], 0.0)
        self.assertEqual(r08["max_penetration_mm"], 0.0)


if __name__ == "__main__":
    unittest.main()
