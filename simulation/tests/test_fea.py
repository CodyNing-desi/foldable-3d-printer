import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.fea import solve_cantilever_beam  # noqa: E402


class BeamFeaTests(unittest.TestCase):
    def test_hex_fea_converges_to_euler_bernoulli(self):
        result = solve_cantilever_beam(
            length_mm=345.0,
            width_mm=20.0,
            height_mm=16.1,
            E_MPa=69000.0,
            poisson=0.33,
            tip_load_N=10.0,
            elements_along=160,
            elements_width=4,
            elements_height=4,
        )
        self.assertLess(abs(result["relative_error"]), 0.03)
        self.assertGreater(result["fea_tip_deflection_mm"], 0.0)
        self.assertEqual(result["dofs"], len(result["displacement_mm"]))


if __name__ == "__main__":
    unittest.main()
