"""Self-contained P0-2 & P0-1 regression tests (no external dependency on simulation_v3/v3_1)."""

import math
import sys
import unittest
from pathlib import Path

FINAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FINAL_DIR / "src"))

import numpy as np
from foldsim_v3_1_final.geometry3d import OBB, obb_sat_distance, rot_y, swept_obb_vs_obb


def _legacy_v3_1_buggy_swept(m_a: OBB, m_b: OBB, obs: OBB) -> float:
    """Self-contained fixture reproducing V3.1's endpoint-AABB broad-phase bug (Counterexample A)
    and moving-vs-moving omission (Counterexample B)."""
    ca, cb = m_a.corners(), m_b.corners()
    swept_min = np.minimum(np.min(ca, axis=0), np.min(cb, axis=0)) - 1.0
    swept_max = np.maximum(np.max(ca, axis=0), np.max(cb, axis=0)) + 1.0
    obs_min, obs_max = obs.aabb()
    # BUG 1: endpoint-only AABB rejects 0->150 deg arc!
    if np.any(swept_max < obs_min) or np.any(obs_max < swept_min):
        return 0.0
    return 1.0


class P02SweptRegressionTests(unittest.TestCase):
    def test_counterexample_a_rotational_sweep_fails_legacy_and_passes_fix(self):
        """Counterexample A: rod rotates 0->150 deg around origin, hitting obstacle at 90 deg (~3mm pen)."""
        rod_0 = OBB.from_bounds("rod", -3.0, -3.0, 0.0, 3.0, 3.0, 100.0)
        rod_150 = rod_0.transformed(rotation=rot_y(150.0), origin=np.zeros(3))
        # At 90 deg, rod lies along +X from 0 to 100, z in [-3, 3]; obstacle at X=80, Z=0 (penetration ~3mm)
        obs = OBB.from_bounds("obs_at_90deg", 75.0, -5.0, -2.0, 85.0, 5.0, 2.0, group="fixed")

        # 1. Confirm legacy endpoint-AABB logic misses it (returns 0.0)!
        legacy_pen = _legacy_v3_1_buggy_swept(rod_0, rod_150, obs)
        self.assertEqual(legacy_pen, 0.0, "Legacy V3.1 logic should miss the 90-deg arc obstacle")

        # 2. Confirm fixed swept_obb_vs_obb catches it with FAIL!
        res = swept_obb_vs_obb(rod_0, rod_150, obs, obs, step_bound_mm=1.5, angle_bound_deg=3.0)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(res["colliding"])
        self.assertGreater(res["penetration_mm"], 2.0)

    def test_counterexample_b_moving_vs_moving_crossing_caught_by_fix(self):
        """Counterexample B: two moving OBBs swap X=0<->X=100 and overlap ~2mm mid-flight."""
        a0 = OBB.from_bounds("A", -5.0, -5.0, 0.0, 5.0, 5.0, 10.0)
        a1 = OBB.from_bounds("A", 95.0, -5.0, 0.0, 105.0, 5.0, 10.0)
        b0 = OBB.from_bounds("B", 95.0, -5.0, 0.0, 105.0, 5.0, 10.0)
        b1 = OBB.from_bounds("B", -5.0, -5.0, 0.0, 5.0, 5.0, 10.0)

        # Endpoints do not collide
        self.assertFalse(obb_sat_distance(a0, b0)[0])
        self.assertFalse(obb_sat_distance(a1, b1)[0])

        # Fixed relative swept check MUST catch mid-flight collision!
        res = swept_obb_vs_obb(a0, a1, b0, b1, step_bound_mm=1.5)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(res["colliding"])
        self.assertGreater(res["penetration_mm"], 5.0)

    def test_known_clear_case_passes_and_exceeded_cap_returns_unresolved(self):
        """Known clear motion returns PASS; capped substeps returns UNRESOLVED."""
        a0 = OBB.from_bounds("A", 0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
        a1 = OBB.from_bounds("A", 50.0, 0.0, 0.0, 60.0, 10.0, 10.0)
        obs = OBB.from_bounds("obs", 0.0, 20.0, 0.0, 60.0, 30.0, 10.0)
        res_pass = swept_obb_vs_obb(a0, a1, obs, obs, step_bound_mm=1.5)
        self.assertEqual(res_pass["status"], "PASS")
        self.assertGreater(res_pass["clearance_mm"], 9.0)

        # Force UNRESOLVED when max_substeps is too small to meet step_bound
        res_unres = swept_obb_vs_obb(a0, a1, obs, obs, step_bound_mm=1.5, max_substeps=4)
        self.assertEqual(res_unres["status"], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
