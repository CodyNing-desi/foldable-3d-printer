import csv
import json
import sys
from pathlib import Path

import numpy as np

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.evaluate import evaluate_candidate
from foldsim.metrics import repeatability_monte_carlo, structural_metrics
from foldsim.registry import load_candidates
from foldsim.selection import choose_diverse, pareto_mask

RESULTS = SIMULATION_DIR / "results"


def _family_group(family):
    if family.startswith("root"):
        return "root"
    if family.startswith("guided"):
        return "guided"
    if family.startswith("telescope"):
        return "telescope"
    if family.startswith("external"):
        return "external"
    return family


def _normalize(values):
    values = np.asarray(values, dtype=float)
    low = np.min(values, axis=0)
    high = np.max(values, axis=0)
    span = np.where(high - low > 1e-12, high - low, 1.0)
    return (values - low) / span


def main():
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    with (RESULTS / "optimization_raw.json").open(encoding="utf-8") as handle:
        optimizations = json.load(handle)
    rows = []
    for optimization in optimizations:
        candidate_id = optimization["id"]
        spec = candidates[candidate_id]
        for solution_index, solution in enumerate(optimization["solutions"]):
            metrics = solution["metrics"]
            if max(solution["constraints"]) > 1e-8 or not metrics["passed_screen"]:
                continue
            rows.append({
                "id": candidate_id,
                "solution_index": solution_index,
                "parameters": solution["parameters"],
                "storage": metrics["storage_ratio"],
                "error": solution["objectives"][1],
                "deflection": metrics["tip_deflection_mm"],
                "reliability": -metrics["reliability_proxy_score"],
                "cost": metrics["estimated_incremental_cost_CNY"],
                "complexity": metrics["manufacturing_complexity_score"],
                "family_group": _family_group(spec["family"]),
            })
    if not rows:
        raise RuntimeError("No feasible optimized candidates; selection stopped without inventing a recommendation")
    metrics_names = ["storage", "error", "deflection", "reliability", "cost", "complexity"]
    normalized = _normalize([[row[name] for name in metrics_names] for row in rows])
    rng = np.random.default_rng(20261113)
    weight_sets = rng.uniform([0.15, 0.20, 0.08, 0.08, 0.05, 0.05], [0.35, 0.50, 0.25, 0.25, 0.20, 0.20], size=(100, 6))
    weight_sets /= weight_sets.sum(axis=1, keepdims=True)
    baseline_weights = np.array([0.25, 0.25, 0.15, 0.15, 0.10, 0.10])
    ids = sorted({row["id"] for row in rows})
    frequencies = {candidate_id: 0 for candidate_id in ids}
    weight_rows = []
    for iteration, weights in enumerate(weight_sets):
        scores = normalized @ weights
        best = {}
        for index, row in enumerate(rows):
            if row["id"] not in best or scores[index] < scores[best[row["id"]]]:
                best[row["id"]] = index
        ranking = sorted(best, key=lambda candidate_id: scores[best[candidate_id]])
        for candidate_id in ranking[:3]:
            frequencies[candidate_id] += 1
        weight_rows.append({"iteration": iteration, "top3": "|".join(ranking[:3]), **{f"w_{name}": weights[i] for i, name in enumerate(metrics_names)}})
    baseline_scores = normalized @ baseline_weights
    best_rows = []
    for candidate_id in ids:
        indices = [i for i, row in enumerate(rows) if row["id"] == candidate_id]
        best_index = min(indices, key=lambda i: baseline_scores[i])
        row = dict(rows[best_index])
        row["baseline_score"] = float(baseline_scores[best_index])
        row["robust_frequency"] = frequencies[candidate_id] / len(weight_sets)
        best_rows.append(row)
    mask = pareto_mask([[row["storage"], row["error"], row["deflection"], row["cost"], row["reliability"]] for row in best_rows])
    for row, is_pareto in zip(best_rows, mask):
        row["candidate_pareto"] = is_pareto
    robust_rows = []
    for row in best_rows:
        if row["robust_frequency"] < 0.8:
            continue
        dense = evaluate_candidate(candidates[row["id"]], parameters=row["parameters"], steps=1001)
        if not dense["passed_screen"]:
            continue
        row["dense_validation"] = {
            "states": 1001,
            "max_intersection_mm2": dense["max_intersection_mm2"],
            "storage_ratio": dense["storage_ratio"],
            "passed_screen": dense["passed_screen"],
        }
        robust_rows.append(row)
    recommended_ids = choose_diverse(robust_rows, count=3, fill_same_family=False)
    recommendations = []
    for index, candidate_id in enumerate(recommended_ids):
        row = next(row for row in best_rows if row["id"] == candidate_id)
        spec = candidates[candidate_id]
        static = structural_metrics(spec, parameters=row["parameters"])
        repeat = repeatability_monte_carlo(spec, parameters=row["parameters"], samples=20000, seed=20261200 + index)
        recommendations.append({
            **row,
            "name": spec["name"],
            "family": spec["family"],
            "assumption": spec["assumption"],
            "final_static_metrics": static,
            "final_repeatability": repeat,
        })
    output = {
        "method": "100 normalized weight perturbations; best solution per candidate; top-three frequency; family-diverse selection",
        "weight_seed": 20261113,
        "baseline_weights": dict(zip(metrics_names, baseline_weights.tolist())),
        "recommended_ids": recommended_ids,
        "recommendations": recommendations,
        "candidate_front": best_rows,
    }
    with (RESULTS / "selection.json").open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    with (RESULTS / "weight_sensitivity.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(weight_rows[0]))
        writer.writeheader()
        writer.writerows(weight_rows)
    print("Recommended:", ", ".join(recommended_ids))


if __name__ == "__main__":
    main()
