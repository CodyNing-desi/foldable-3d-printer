import csv
import json
import sys
import unittest
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))


class VerificationDocsTests(unittest.TestCase):
    def test_bom_subtotals_match_summary(self):
        bom_path = SIMULATION_DIR / "verification" / "third_option_bom.csv"
        with bom_path.open(encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        with (SIMULATION_DIR / "verification" / "bom_summary.json").open(encoding="utf-8") as handle:
            summary = json.load(handle)
        for prefix, key in (("SCZ_", "SCZ_exploratory"), ("F08_", "F08_fallback")):
            low = sum(int(row["qty"]) * float(row["unit_low_cny"]) for row in rows if row["group"].startswith(prefix))
            high = sum(int(row["qty"]) * float(row["unit_high_cny"]) for row in rows if row["group"].startswith(prefix))
            self.assertAlmostEqual(low, summary["assembly_subtotals"][key]["low"])
            self.assertAlmostEqual(high, summary["assembly_subtotals"][key]["high"])

    def test_physical_plan_does_not_claim_completed_measurements(self):
        plan = (SIMULATION_DIR / "verification" / "PHYSICAL_VALIDATION_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("待执行", plan)
        self.assertIn("不得用软件", plan)
        self.assertNotIn("实测通过", plan)

    def test_third_option_is_distinct_and_dense_validated(self):
        with (SIMULATION_DIR / "results" / "third_option_analysis.json").open(encoding="utf-8") as handle:
            third = json.load(handle)
        self.assertEqual(third["selected_third_option"], "SCZ")
        self.assertEqual(third["fallback_option"], "F08")
        self.assertTrue(third["selected"]["dense_5001_passed"])


if __name__ == "__main__":
    unittest.main()
