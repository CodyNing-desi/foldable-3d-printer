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
    with (RESULTS / "third_option_analysis.json").open(encoding="utf-8") as handle:
        third = json.load(handle)
    with (RESULTS / "convergence_validation.json").open(encoding="utf-8") as handle:
        convergence = json.load(handle)
    with (RESULTS / "beam_fea.json").open(encoding="utf-8") as handle:
        beam_fea = json.load(handle)
    check("two diverse robust recommendations", len(selection["recommended_ids"]) == 2, selection["recommended_ids"])
    check("recommendations exceed 80 percent robust frequency", all(row["robust_frequency"] >= 0.8 for row in selection["recommendations"]), [row["robust_frequency"] for row in selection["recommendations"]])
    check("all nominal pass/fail states stable to 1001 states", all(row["status_stable"] for row in convergence["nominal"].values()), len(convergence["nominal"]))
    check("all optimized watchlist pass 5001 states", all(row["final_5001_passed"] for row in convergence["optimized"].values()), [row["id"] for row in convergence["optimized"].values() if not row["final_5001_passed"]])
    check("third option is SCZ and fallback is F08", third["selected_third_option"] == "SCZ" and third["fallback_option"] == "F08", [third["selected_third_option"], third["fallback_option"]])
    check("third option passes 5001 states", third["selected"]["dense_5001_passed"], third["selected"]["robust_frequency"])
    check("beam FEA finest relative error below 3 percent", abs(beam_fea["finest_relative_error"]) < 0.03, beam_fea["finest_relative_error"])
    check("beam FEA records local-only limitation", "not the T-slot" in beam_fea["limitation"], beam_fea["limitation"])
    gifs = list((SIMULATION_DIR / "animations").glob("*_fold.gif"))
    check("15 folding GIFs", len(gifs) == 15, len(gifs))
    for path in gifs:
        reader = imageio.get_reader(path)
        frames = sum(1 for _ in reader)
        reader.close()
        check(f"{path.stem} has 21 frames", frames == 21, frames)
    for name in ("screening_storage_comparison", "deep_tradeoff", "optimization_pareto", "sensitivity_storage_heatmap", "all_candidates_work_and_folded", "fea_convergence", "third_option_comparison"):
        for suffix in ("png", "svg"):
            check(f"{name}.{suffix} exists", (SIMULATION_DIR / "figures" / f"{name}.{suffix}").is_file(), suffix)
    cad_ids = set(selection["recommended_ids"]) | {third["selected_third_option"], third["fallback_option"]}
    for candidate_id in cad_ids:
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
    check("report states not physical validation", "不是实机或整机 FEA 验证" in report, True)
    check("report has CAD visual limitations", "没有销轴孔、轴承座、锁点或线缆细节" in report, True)
    check("report includes third option and physical plan", "探索型 SCZ" in report and "PHYSICAL_VALIDATION_PLAN.md" in report, True)
    check("report includes material BOM", "third_option_bom.csv" in report, True)
    process_review = (SIMULATION_DIR / "PROCESS_REVIEW.md").read_text(encoding="utf-8")
    check("process review records the F04 reversal", "F07 + F04" in process_review and "撤回推荐" in process_review, True)
    check("process review records final recommendation and validation", "F07 和 F12" in process_review and "138/138" in process_review, True)
    external_diff = subprocess.run(["git", "diff", "--name-only", "--", "external"], cwd=SIMULATION_DIR.parent, text=True, capture_output=True)
    check("external unchanged", external_diff.returncode == 0 and not external_diff.stdout.strip(), external_diff.stdout.strip())
    for name in ("hinge-inner", "hinge-outer"):
        with (SIMULATION_DIR / "cad" / "reference" / f"{name}-facts.json").open(encoding="utf-8") as handle:
            facts = json.load(handle)
        check(f"{name} upstream STEP valid", facts["is_valid"] and facts["solid_count"] == 1, facts["solid_count"])
        check(f"{name} upstream snapshot exists", (SIMULATION_DIR / "cad" / "reference" / f"{name}-left.png").is_file(), True)
    verification_dir = SIMULATION_DIR / "verification"
    with (verification_dir / "third_option_bom.csv").open(encoding="utf-8-sig") as handle:
        bom_rows = list(csv.DictReader(handle))
    check("physical BOM has at least 40 rows", len(bom_rows) >= 40, len(bom_rows))
    bom_groups = {row["group"] for row in bom_rows}
    check("BOM covers SCZ and F08", any(group.startswith("SCZ_") for group in bom_groups) and any(group.startswith("F08_") for group in bom_groups), sorted(bom_groups))
    scz_total = sum(int(row["qty"]) * float(row["unit_low_cny"]) for row in bom_rows if row["group"].startswith("SCZ_"))
    with (verification_dir / "bom_summary.json").open(encoding="utf-8") as handle:
        bom_summary = json.load(handle)
    check("BOM SCZ low subtotal matches summary", abs(scz_total - bom_summary["assembly_subtotals"]["SCZ_exploratory"]["low"]) < 1e-9, scz_total)
    check("third-option decision document exists", (verification_dir / "THIRD_OPTION_DECISION.md").is_file(), True)
    check("physical validation plan exists", (verification_dir / "PHYSICAL_VALIDATION_PLAN.md").is_file(), True)
    with (verification_dir / "physical_test_log.csv").open(encoding="utf-8-sig") as handle:
        header = handle.readline().strip()
    check("physical test log has required traceability header", all(label in header for label in ("test_id", "instrument_id", "calibration_status", "photo_video_path")), header)
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
