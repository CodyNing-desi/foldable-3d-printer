import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.registry import load_candidates  # noqa: E402
from foldsim.sensitivity import latin_samples  # noqa: E402


class SensitivityTests(unittest.TestCase):
    def test_latin_hypercube_is_seeded_and_within_bounds(self):
        candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
        spec = candidates["F07"]
        first = latin_samples(spec, count=12, seed=42)
        second = latin_samples(spec, count=12, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 12)
        for row in first:
            for name, value in row.items():
                low, high = spec["bounds"][name]
                self.assertGreaterEqual(value, low)
                self.assertLessEqual(value, high)


if __name__ == "__main__":
    unittest.main()
