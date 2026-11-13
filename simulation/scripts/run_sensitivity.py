import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.metrics import structural_metrics
from foldsim.registry import load_candidates
from foldsim.sensitivity import latin_samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=48)
    args = parser.parse_args()
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    results_dir = SIMULATION_DIR / "results"
    raw_rows = []
    sensitivity_rows = []
    for index, (candidate_id, spec) in enumerate(candidates.items()):
        designs = latin_samples(spec, args.samples, 20261113 + index)
        candidate_rows = []
        for run, parameters in enumerate(designs):
            metrics = structural_metrics(spec, parameters=parameters)
            row = {
                "id": candidate_id,
                "run": run,
                "seed": 20261113 + index,
                **parameters,
                "storage_ratio": metrics["storage_ratio"],
                "tip_deflection_mm": metrics["tip_deflection_mm"],
                "peak_drive_force_N": metrics["peak_drive_force_N"],
                "cost_CNY": metrics["estimated_incremental_cost_CNY"],
                "max_intersection_mm2": metrics["max_intersection_mm2"],
                "passed_screen": metrics["passed_screen"],
            }
            raw_rows.append(row)
            candidate_rows.append(row)
        for name in spec["bounds"]:
            for output in ("storage_ratio", "tip_deflection_mm", "peak_drive_force_N", "cost_CNY"):
                x = [row[name] for row in candidate_rows]
                y = [row[output] for row in candidate_rows]
                correlation = spearmanr(x, y).statistic if len(set(x)) > 1 and len(set(y)) > 1 else np.nan
                sensitivity_rows.append({
                    "id": candidate_id,
                    "parameter": name,
                    "output": output,
                    "spearman_rho": correlation,
                    "samples": len(candidate_rows),
                })
        print(candidate_id, f"{len(designs)} Latin-hypercube evaluations")
    with (results_dir / "sensitivity_raw.json").open("w", encoding="utf-8") as handle:
        json.dump(raw_rows, handle, ensure_ascii=False, indent=2)
    with (results_dir / "sensitivity_rank_correlations.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sensitivity_rows[0]))
        writer.writeheader()
        writer.writerows(sensitivity_rows)
    with (results_dir / "sensitivity_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump({
            "design": "Latin hypercube over declared engineering-assumption bounds",
            "samples_per_variable_candidate": args.samples,
            "master_seed": 20261113,
            "analysis": "Spearman rank correlation; deterministic computer experiments, no causal physical claim or p-value-driven selection",
        }, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
