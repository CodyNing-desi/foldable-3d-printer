from .evaluate import evaluate_candidate


def sweep_convergence(spec, parameters=None, step_counts=(201, 501, 1001)):
    rows = []
    for steps in sorted(set(step_counts)):
        result = evaluate_candidate(spec, parameters=parameters, steps=steps)
        trace = result["trace"]
        rows.append({
            "states": steps,
            "passed_screen": result["passed_screen"],
            "max_intersection_mm2": result["max_intersection_mm2"],
            "min_slot_side_clearance_mm": min(
                (state["slot_side_clearance_mm"] for state in trace), default=0.0,
            ),
            "reachable_fraction": result["reachable_fraction"],
            "storage_ratio": result["storage_ratio"],
            "screen_reasons": result["screen_reasons"],
        })
    return rows
