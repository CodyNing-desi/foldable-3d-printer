import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.evaluate import evaluate_candidate
from foldsim.registry import load_candidates


def _git_commit():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=SIMULATION_DIR.parent, text=True,
    ).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=201)
    args = parser.parse_args()
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    results_dir = SIMULATION_DIR / "results"
    traces_dir = results_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    manifest_rows = []
    for candidate_id, spec in candidates.items():
        result = evaluate_candidate(spec, steps=args.steps)
        trace_rows = result.pop("trace_rows")
        trace = result.pop("trace")
        summaries.append(result)
        with (traces_dir / f"{candidate_id}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(trace_rows[0]))
            writer.writeheader()
            writer.writerows(trace_rows)
        manifest_rows.append({
            "id": candidate_id,
            "states": len(trace),
            "passed": result["passed_screen"],
            "parameters": result["parameters"],
            "assumption": spec["assumption"],
        })
        print(candidate_id, "PASS" if result["passed_screen"] else "FAIL", result["screen_reasons"])
    with (results_dir / "screening_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, ensure_ascii=False, indent=2)
    keys = sorted({key for row in summaries for key in row if key != "parameters"})
    with (results_dir / "screening_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in summaries:
            writer.writerow({key: row.get(key) for key in keys})
    manifest = {
        "seed": 20261113,
        "source_commit": _git_commit(),
        "steps_per_candidate": args.steps,
        "candidate_count": len(summaries),
        "passed_count": sum(row["passed_screen"] for row in summaries),
        "simulation_level": "L1: 2.5D rigid-body kinematics, Shapely intersection area and extruded envelope volume",
        "not_validated": ["full 3D assembly collision", "physical printer accuracy", "cable fatigue", "long-term reliability"],
        "candidates": manifest_rows,
    }
    with (results_dir / "screening_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
