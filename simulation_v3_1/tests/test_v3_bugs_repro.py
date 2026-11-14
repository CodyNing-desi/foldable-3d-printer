"""Pre-fix failure reproduction tests against simulation_v3 (evidence for AUDIT.md)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation_v3" / "src"))

import numpy as np
from foldsim_v3.evaluate3d import _swept_segment_collision
from foldsim_v3.fea3d import evaluate_candidate_fea3d
from foldsim_v3.geometry3d import OBB
from foldsim_v3.registry import load_candidates


class V3BugReproductionTests(unittest.TestCase):
    def test_v3_swept_collision_misses_x25_obstacle(self):
        """V3 bug: moving box X=0->100 misses obstacle at X=25."""
        obs = OBB.from_bounds("wall", 24.5, -10.0, 0.0, 25.5, 10.0, 10.0, group="fixed")
        m_a = OBB.from_bounds("slider", -5.0, -5.0, 0.0, 5.0, 5.0, 10.0, group="moving")
        m_b = OBB.from_bounds("slider", 95.0, -5.0, 0.0, 105.0, 5.0, 10.0, group="moving")
        pen, pair = _swept_segment_collision({"moving": [m_a], "fixed": [obs]}, {"moving": [m_b], "fixed": [obs]})
        # V3 returns 0.0 (BUG!)
        self.assertEqual(pen, 0.0, f"Expected V3 bug to miss X=25 obstacle, got pen={pen}")

    def test_v3_scz_fea_has_constant_dofs_across_nsub(self):
        """V3 bug: SCZ FEA ignores n_sub and keeps 60 DOFs."""
        cands = load_candidates(ROOT / "simulation_v3" / "config" / "candidates_v3.json")
        r4 = evaluate_candidate_fea3d("SCZ", cands["SCZ"], n_sub=4)
        r16 = evaluate_candidate_fea3d("SCZ", cands["SCZ"], n_sub=16)
        self.assertEqual(r4["dofs"], 60)
        self.assertEqual(r16["dofs"], 60)


if __name__ == "__main__":
    unittest.main()
