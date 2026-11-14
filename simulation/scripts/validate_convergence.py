import json
import sys
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
RESULTS = SIMULATION_DIR / "results"
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.convergence import sweep_convergence
from foldsim.registry import load_candidates


def main():
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    with (RESULTS / "selection.json").open(encoding="utf-8") as handle:
        selection = json.load(handle)
    nominal = {}
    for candidate_id, spec in candidates.items():
        rows = sweep_convergence(spec, step_counts=(201, 501, 1001))
        nominal[candidate_id] = {
            "status_stable": len({row["passed_screen"] for row in rows}) == 1,
            "max_intersection_spread_mm2": max(row["max_intersection_mm2"] for row in rows)
            - min(row["max_intersection_mm2"] for row in rows),
            "sweeps": rows,
        }
        print("nominal", candidate_id, [row["passed_screen"] for row in rows])
    optimized = {}
    recommended = set(selection["recommended_ids"])
    for row in selection["candidate_front"]:
        candidate_id = row["id"]
        spec = candidates[candidate_id]
        rows = sweep_convergence(
            spec, parameters=row["parameters"], step_counts=(201, 501, 1001, 2001, 5001),
        )
        optimized[candidate_id] = {
            "role": "recommended" if candidate_id in recommended else "third_option_watchlist",
            "parameters": row["parameters"],
            "status_stable": len({item["passed_screen"] for item in rows}) == 1,
            "final_5001_passed": rows[-1]["passed_screen"],
            "max_intersection_spread_mm2": max(item["max_intersection_mm2"] for item in rows)
            - min(item["max_intersection_mm2"] for item in rows),
            "sweeps": rows,
        }
        print("optimized", candidate_id, rows[-1]["passed_screen"], rows[-1]["max_intersection_mm2"])
    output = {
        "purpose": "sampling-density convergence and 5001-state validation of optimized watchlist",
        "nominal_step_counts": [201, 501, 1001],
        "optimized_step_counts": [201, 501, 1001, 2001, 5001],
        "nominal": nominal,
        "optimized": optimized,
        "limitation": "discrete rigid-body states; not a continuous swept-volume proof or physical test",
    }
    with (RESULTS / "convergence_validation.json").open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    print("wrote results/convergence_validation.json")


if __name__ == "__main__":
    main()
