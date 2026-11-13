import argparse
import csv
import json
import sys
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.optimize import optimize_candidate
from foldsim.registry import load_candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pop-size", type=int, default=32)
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--candidate", action="append")
    args = parser.parse_args()
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    selected = args.candidate or list(candidates)
    results_dir = SIMULATION_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    all_results = []
    flat_rows = []
    for index, candidate_id in enumerate(selected):
        spec = candidates[candidate_id]
        if not spec["bounds"]:
            print(candidate_id, "fixed-topology reference; no optimization variables")
            continue
        result = optimize_candidate(
            spec,
            pop_size=args.pop_size,
            generations=args.generations,
            seed=20261113 + index,
        )
        all_results.append(result)
        for solution_index, solution in enumerate(result["solutions"]):
            metrics = solution["metrics"]
            flat_rows.append({
                "id": candidate_id,
                "solution_index": solution_index,
                "seed": result["seed"],
                **solution["parameters"],
                "storage_ratio": metrics["storage_ratio"],
                "tip_deflection_mm": metrics["tip_deflection_mm"],
                "peak_torque_Nmm": metrics["peak_torque_Nmm"],
                "peak_drive_force_N": metrics["peak_drive_force_N"],
                "cost_CNY": metrics["estimated_incremental_cost_CNY"],
                "max_cv": max(solution["constraints"]),
                "feasible": max(solution["constraints"]) <= 1e-8,
            })
        print(candidate_id, f"{len(result['solutions'])} Pareto/least-infeasible solutions")
    with (results_dir / "optimization_raw.json").open("w", encoding="utf-8") as handle:
        json.dump(all_results, handle, ensure_ascii=False, indent=2)
    fieldnames = sorted({key for row in flat_rows for key in row})
    with (results_dir / "optimization_solutions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)
    with (results_dir / "optimization_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump({
            "algorithm": "NSGA-II",
            "pop_size": args.pop_size,
            "generations": args.generations,
            "master_seed": 20261113,
            "objectives": ["system storage ratio", "repeatability surrogate mm", "tip deflection mm", "incremental cost / 1000 CNY"],
            "constraints": ["collision", "storage ratio <= 0.8", "workspace coverage", "drive force or family-specific geometry", "assembly reachability"],
            "note": "Failed fixed-topology candidates remain in screening data; no feasible solution is invented for them.",
        }, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
