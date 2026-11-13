import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize

from .metrics import repeatability_surrogate, structural_metrics


class CandidateProblem(ElementwiseProblem):
    def __init__(self, spec):
        self.spec = spec
        self.names = list(spec["bounds"])
        lower = [spec["bounds"][name][0] for name in self.names]
        upper = [spec["bounds"][name][1] for name in self.names]
        super().__init__(n_var=len(self.names), n_obj=4, n_ieq_constr=5, xl=lower, xu=upper)

    def parameters(self, x):
        return {name: float(value) for name, value in zip(self.names, x)}

    def evaluate_design(self, x):
        parameters = self.parameters(x)
        metrics = structural_metrics(self.spec, parameters=parameters)
        error_surrogate = repeatability_surrogate(self.spec, parameters)
        objectives = [
            metrics["storage_ratio"],
            error_surrogate,
            metrics["tip_deflection_mm"],
            metrics["estimated_incremental_cost_CNY"] / 1000.0,
        ]
        special_constraint = metrics["peak_drive_force_N"] - 500.0
        if self.spec["family"] in {"telescope_2", "telescope_3"}:
            stages = 2 if self.spec["family"] == "telescope_2" else 3
            overlap = parameters["overlap_mm"]
            extended = self.spec["common"]["column_top_mm"] - self.spec["common"]["column_bottom_mm"]
            stage_height = (extended + (stages - 1) * overlap) / stages
            special_constraint = 0.25 - overlap / stage_height
        if self.spec["family"] in {"guided_single", "guided_double"}:
            special_constraint = 0.25 - (parameters["slot_width_mm"] - self.spec["parameters"]["roller_diameter_mm"]) / 2
        if self.spec["family"] == "drawer_y":
            special_constraint = 35.0 - parameters["cable_bend_radius_mm"]
        constraints = [
            metrics["max_intersection_mm2"] - 1e-6,
            metrics["storage_ratio"] - 0.8,
            1.0 - metrics["workspace_coverage"],
            special_constraint,
            1.0 - metrics["reachable_fraction"],
        ]
        return {"objectives": objectives, "constraints": constraints, "metrics": metrics}

    def _evaluate(self, x, out, *args, **kwargs):
        values = self.evaluate_design(x)
        out["F"] = values["objectives"]
        out["G"] = values["constraints"]


def optimize_candidate(spec, pop_size=32, generations=20, seed=20261113):
    if not spec["bounds"]:
        raise ValueError(f"{spec['id']} has no continuous optimization variables")
    problem = CandidateProblem(spec)
    result = minimize(
        problem,
        NSGA2(pop_size=pop_size, eliminate_duplicates=True),
        ("n_gen", generations),
        seed=seed,
        save_history=True,
        verbose=False,
    )
    x_values = np.empty((0, problem.n_var)) if result.X is None else np.atleast_2d(result.X)
    solutions = []
    for x in x_values:
        values = problem.evaluate_design(x)
        solutions.append({
            "parameters": problem.parameters(x),
            "objectives": values["objectives"],
            "constraints": values["constraints"],
            "metrics": values["metrics"],
        })
    population = result.algorithm.pop
    population_x = population.get("X")
    population_g = population.get("G")
    worst_index = int(np.argmax(np.max(population_g, axis=1)))
    least_index = int(np.argmin(np.max(population_g, axis=1)))
    least_values = problem.evaluate_design(population_x[least_index])
    least_infeasible = {
        "parameters": problem.parameters(population_x[least_index]),
        "objectives": least_values["objectives"],
        "constraints": least_values["constraints"],
        "max_constraint_violation": float(np.max(population_g[least_index])),
        "population_size": len(population_x),
        "worst_constraint_violation": float(np.max(population_g[worst_index])),
    }
    history = []
    for generation, algorithm in enumerate(result.history, start=1):
        if algorithm.opt is not None and len(algorithm.opt) > 0:
            history.append({
                "generation": generation,
                "best_storage_ratio": float(np.min(algorithm.opt.get("F")[:, 0])),
                "best_error_surrogate_mm": float(np.min(algorithm.opt.get("F")[:, 1])),
            })
    return {
        "id": spec["id"],
        "algorithm": "NSGA-II",
        "seed": seed,
        "pop_size": pop_size,
        "generations": generations,
        "solutions": solutions,
        "least_infeasible": least_infeasible,
        "history": history,
    }
