import sys
import unittest
from pathlib import Path

SIM_V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_V3 / "src"))

from foldsim_v3.evaluate3d import evaluate_candidate_3d
from foldsim_v3.fea3d import evaluate_candidate_fea3d
from foldsim_v3.metrics_v3 import repeatability_monte_carlo_v3, structural_metrics_v3
from foldsim_v3.registry import load_candidates


class Round3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cands = load_candidates(SIM_V3 / "config" / "candidates_v3.json")

    def test_accessory_participates_in_collision_and_avoids_overlap(self):
        for cid in ["F07", "F09", "SCZ", "F12", "F08"]:
            res = evaluate_candidate_3d(self.cands[cid], steps=31, swept_check=True)
            self.assertEqual(res["max_penetration_mm"], 0.0, f"{cid} collided: {res['worst_collision_pair']}")

    def test_scz_continuous_parking_has_no_jump_and_passes(self):
        res = evaluate_candidate_3d(self.cands["SCZ"], steps=51, swept_check=True)
        self.assertTrue(res["passed_screen"])
        # Toolhead x smoothly transitions at t <= 0.15
        th_t0 = [o for o in res["trace"][0]["moving"] if o.name == "toolhead"][0].center[0]
        th_t1 = [o for o in res["trace"][-1]["moving"] if o.name == "toolhead"][0].center[0]
        self.assertAlmostEqual(th_t0, 157.5, places=1)
        self.assertAlmostEqual(th_t1, 38.0, places=1)

    def test_f09_uses_3d_space_frame_fea_and_converges(self):
        f8 = evaluate_candidate_fea3d("F09", self.cands["F09"], n_sub=8)
        f16 = evaluate_candidate_fea3d("F09", self.cands["F09"], n_sub=16)
        self.assertGreater(f8["dofs"], 100)
        self.assertLess(abs(f16["tip_lateral_deflection_mm"] - f8["tip_lateral_deflection_mm"]) / f16["tip_lateral_deflection_mm"], 0.05)

    def test_f12_ablation_separates_layout_from_structure(self):
        ptfe = structural_metrics_v3(self.cands["F12"], parameters={"motor_side_mounted": 0, "radial_clearance_mm": 0.08}, steps=21)
        preload = structural_metrics_v3(self.cands["F12"], steps=21)
        self.assertFalse(ptfe["passed_screen"])
        self.assertTrue(preload["passed_screen"])
        self.assertLess(preload["clearance_play_mm"], ptfe["clearance_play_mm"])

    def test_metrics_separate_deflection_error_backlash_and_risk(self):
        m = structural_metrics_v3(self.cands["SCZ"], steps=21)
        mc = repeatability_monte_carlo_v3(self.cands["SCZ"], samples=500, seed=7)
        self.assertIn("elastic_deflection_mm", m)
        self.assertIn("backlash_z_mm", m)
        self.assertIn("p95_mm", mc)
        self.assertIn("print_accuracy_risk", mc)


if __name__ == "__main__":
    unittest.main()
