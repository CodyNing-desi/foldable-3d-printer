import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.metrics import repeatability_monte_carlo, structural_metrics
from foldsim.registry import load_candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=10000)
    args = parser.parse_args()
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    results_dir = SIMULATION_DIR / "results"
    samples_dir = results_dir / "repeatability_samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, (candidate_id, spec) in enumerate(candidates.items()):
        static = structural_metrics(spec)
        repeat = repeatability_monte_carlo(
            spec, samples=args.samples, seed=20261113 + index, return_samples=True,
        )
        samples = repeat.pop("samples_mm")
        np.savez_compressed(
            samples_dir / f"{candidate_id}.npz",
            radial_error_mm=samples,
            seed=np.int64(repeat["seed"]),
        )
        row = dict(static)
        row.update(repeat)
        row["deepening_status"] = "L2_completed" if static["passed_screen"] else "L1_failed_indicative_L2_only"
        rows.append(row)
        print(candidate_id, row["deepening_status"], f"p95={repeat['p95_mm']:.4f} mm")
    with (results_dir / "deep_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
    keys = sorted({key for row in rows for key in row if key not in {"screen_reasons", "parameters", "input_distribution"}})
    with (results_dir / "deep_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in keys})
    metadata = {
        "samples_per_candidate": args.samples,
        "master_seed": 20261113,
        "distribution": "independent rectangular joint-clearance and datum-seat errors",
        "intervals": "p50/p95/p99 are Monte Carlo output percentiles, not confidence intervals or measured printer accuracy",
        "statics": "Euler-Bernoulli reduced-order beam plus linearized lock-contact stiffness; not 3D FEA",
    }
    with (results_dir / "deep_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
