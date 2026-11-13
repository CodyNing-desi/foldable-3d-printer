import ast
import csv
import json
import subprocess
import sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

SIMULATION_DIR = Path(__file__).resolve().parents[1]
RESULTS = SIMULATION_DIR / "results"
EXPECTED_IDS = {f"F{i:02d}" for i in range(1, 15)} | {"SCZ"}


def main():
    checks = []

    def check(name, condition, evidence):
        checks.append({"name": name, "passed": bool(condition), "evidence": evidence})

    with (RESULTS / "screening_summary.json").open(encoding="utf-8") as handle:
        screening = json.load(handle)
    check("15 candidates", {row["id"] for row in screening} == EXPECTED_IDS, len(screening))
    check("four nominal passes after review corrections", sum(row["passed_screen"] for row in screening) == 4, [row["id"] for row in screening if row["passed_screen"]])
    trace_files = list((RESULTS / "traces").glob("*.csv"))
    check("15 trace files", len(trace_files) == 15, len(trace_files))
    for path in trace_files:
        with path.open(encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        check(f"{path.stem} has 201 states", len(rows) == 201, len(rows))
    sample_files = list((RESULTS / "repeatability_samples").glob("*.npz"))
    check("15 raw Monte Carlo files", len(sample_files) == 15, len(sample_files))
    for path in sample_files:
        with np.load(path) as data:
            check(f"{path.stem} has 10000 raw samples", len(data["radial_error_mm"]) == 10000, len(data["radial_error_mm"]))
    with (RESULTS / "selection.json").open(encoding="utf-8") as handle:
        selection = json.load(handle)
    check("two diverse robust recommendations", len(selection["recommended_ids"]) == 2, selection["recommended_ids"])
    check("recommendations exceed 80 percent robust frequency", all(row["robust_frequency"] >= 0.8 for row in selection["recommendations"]), [row["robust_frequency"] for row in selection["recommendations"]])
    gifs = list((SIMULATION_DIR / "animations").glob("*_fold.gif"))
    check("15 folding GIFs", len(gifs) == 15, len(gifs))
    for path in gifs:
        reader = imageio.get_reader(path)
        frames = sum(1 for _ in reader)
        reader.close()
        check(f"{path.stem} has 21 frames", frames == 21, frames)
    for name in ("screening_storage_comparison", "deep_tradeoff", "optimization_pareto", "sensitivity_storage_heatmap", "all_candidates_work_and_folded"):
        for suffix in ("png", "svg"):
            check(f"{name}.{suffix} exists", (SIMULATION_DIR / "figures" / f"{name}.{suffix}").is_file(), suffix)
    for candidate_id in selection["recommended_ids"]:
        manifest_path = SIMULATION_DIR / "cad" / candidate_id / f"{candidate_id.lower()}.manifest.json"
        with manifest_path.open(encoding="utf-8") as handle:
            manifest = json.load(handle)
        check(f"{candidate_id} valid STEP with at least two solids", manifest["is_valid"] and manifest["solid_count"] >= 2, manifest["solid_count"])
        check(f"{candidate_id} STEP and STL exist", all((manifest_path.parent / name).is_file() for name in (f"{candidate_id.lower()}.step", f"{candidate_id.lower()}.stl")), True)
        check(f"{candidate_id} snapshot exists", (manifest_path.parent / f"{candidate_id.lower()}_snapshot.png").is_file(), True)
    python_files = list((SIMULATION_DIR / "src").rglob("*.py")) + list((SIMULATION_DIR / "scripts").glob("*.py")) + list((SIMULATION_DIR / "tests").glob("*.py"))
    for path in python_files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            valid = True
        except SyntaxError:
            valid = False
        check(f"syntax {path.name}", valid, str(path.relative_to(SIMULATION_DIR)))
    report = (SIMULATION_DIR / "REPORT.md").read_text(encoding="utf-8")
    check("report states not physical validation", "不是实机验证" in report, True)
    check("report has CAD visual limitations", "没有铰链孔、槽轨、定位销或锁点细节" in report, True)
    external_diff = subprocess.run(["git", "diff", "--name-only", "--", "external"], cwd=SIMULATION_DIR.parent, text=True, capture_output=True)
    check("external unchanged", external_diff.returncode == 0 and not external_diff.stdout.strip(), external_diff.stdout.strip())
    for name in ("hinge-inner", "hinge-outer"):
        with (SIMULATION_DIR / "cad" / "reference" / f"{name}-facts.json").open(encoding="utf-8") as handle:
            facts = json.load(handle)
        check(f"{name} upstream STEP valid", facts["is_valid"] and facts["solid_count"] == 1, facts["solid_count"])
        check(f"{name} upstream snapshot exists", (SIMULATION_DIR / "cad" / "reference" / f"{name}-left.png").is_file(), True)
    check("environment recorded", (RESULTS / "environment.json").is_file(), True)
    output = {"passed": all(row["passed"] for row in checks), "check_count": len(checks), "checks": checks}
    with (RESULTS / "deliverable_validation.json").open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    failures = [row for row in checks if not row["passed"]]
    print(f"{len(checks) - len(failures)}/{len(checks)} deliverable checks passed")
    for failure in failures:
        print("FAIL", failure)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
