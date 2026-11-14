import json
import sys
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
RESULTS = SIMULATION_DIR / "results"
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.metrics import repeatability_monte_carlo, structural_metrics
from foldsim.registry import load_candidates
from foldsim.third_option import CRITERIA, choose_third, score_options


def main():
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    with (RESULTS / "selection.json").open(encoding="utf-8") as handle:
        selection = json.load(handle)
    with (RESULTS / "convergence_validation.json").open(encoding="utf-8") as handle:
        convergence = json.load(handle)
    recommended_groups = {
        row["family_group"] for row in selection["candidate_front"]
        if row["id"] in selection["recommended_ids"]
    }
    learning_value = {"F08": 0.2, "SCZ": 1.0}
    rows = []
    for row in selection["candidate_front"]:
        if row["id"] in selection["recommended_ids"]:
            continue
        rows.append({
            "id": row["id"],
            "family_group": row["family_group"],
            "parameters": row["parameters"],
            "storage": row["storage"],
            "error": row["error"],
            "deflection": row["deflection"],
            "cost": row["cost"],
            "reliability": -row["reliability"],
            "robust": row["robust_frequency"],
            "diversity": 0.0 if row["family_group"] in recommended_groups else 1.0,
            "learning": learning_value.get(row["id"], 0.5),
        })
    info_choice = choose_third(rows, criterion="information")
    engineering_choice = choose_third(rows, criterion="engineering")
    selected = next(row for row in rows if row["id"] == info_choice)
    fallback = next(row for row in rows if row["id"] == engineering_choice)
    spec = candidates[info_choice]
    static = structural_metrics(spec, parameters=selected["parameters"])
    repeat = repeatability_monte_carlo(
        spec, parameters=selected["parameters"], samples=20000, seed=20261300,
    )
    output = {
        "decision_question": "Which third option should enter physical validation beyond F07 and F12?",
        "criteria_weights": CRITERIA,
        "weighted_scores": {
            "engineering": score_options(rows, "engineering"),
            "information": score_options(rows, "information"),
        },
        "candidate_metrics": rows,
        "information_choice": info_choice,
        "engineering_choice": engineering_choice,
        "selected_third_option": info_choice,
        "selection_basis": "Information-gain criterion: independent mechanism family and a documented high-risk evidence gap, while still passing 5001-state geometry validation. It is exploratory, not a promotion above F08 on pass likelihood.",
        "fallback_option": engineering_choice,
        "fallback_reason": "Highest engineering-pass likelihood among remaining candidates, but duplicates the root-fold family already represented by F07.",
        "selected": {
            "id": info_choice,
            "name": spec["name"],
            "family": spec["family"],
            "parameters": selected["parameters"],
            "robust_frequency": selected["robust"],
            "dense_5001_passed": convergence["optimized"][info_choice]["final_5001_passed"],
            "static_metrics": static,
            "repeatability_20000": repeat,
            "assumption": spec["assumption"],
            "key_risks": [
                "low-height geometric gain, backlash and left-right synchronization",
                "eight pin joints and multiple sliding contacts",
                "nonlinear Z mapping and homing repeatability",
                "lock stiffness and bed orthogonality after deployment",
            ],
        },
    }
    (RESULTS / "third_option_analysis.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print("information choice", info_choice, "engineering fallback", engineering_choice)
    print("selected metrics", static["storage_ratio"], repeat["p95_mm"], static["peak_drive_force_N"])


if __name__ == "__main__":
    main()
