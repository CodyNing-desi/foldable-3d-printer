import json
import sys
from pathlib import Path

import numpy as np
import pint
import sympy as sp
import uncertainties
from uncertainties import ufloat

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.mechanisms import scissor_state


def main():
    arm, span = sp.symbols("arm span", positive=True, real=True)
    height = sp.sqrt(4 * arm**2 - span**2)
    derivative = sp.simplify(sp.diff(height, span))
    numeric_height = sp.lambdify((arm, span), height, "numpy")
    numeric_derivative = sp.lambdify((arm, span), derivative, "numpy")
    reference = scissor_state(160.0, 180.0)
    assert abs(numeric_height(160.0, 180.0) - reference["height_mm"]) < 1e-10
    assert abs(numeric_derivative(160.0, 180.0) - reference["dH_dS"]) < 1e-10

    ureg = pint.UnitRegistry()
    torque = 2.0 * ureg.kg * 9.81 * ureg.m / ureg.s**2 * 100.0 * ureg.mm
    torque_nmm = torque.to("N*mm")
    assert abs(torque_nmm.magnitude - 1962.0) < 1e-9
    stiffness = (
        3 * 69000.0 * ureg.N / ureg.mm**2 * 7000.0 * ureg.mm**4 / (345.0 * ureg.mm)**3
    ).to("N/mm")

    arm_uncertain = ufloat(160.0, 0.03)
    span_uncertain = ufloat(180.0, 0.03)
    height_uncertain = (4 * arm_uncertain**2 - span_uncertain**2) ** 0.5
    rng = np.random.default_rng(20261113)
    arm_samples = rng.uniform(160.0 - 0.03 * np.sqrt(3), 160.0 + 0.03 * np.sqrt(3), 100000)
    span_samples = rng.uniform(180.0 - 0.03 * np.sqrt(3), 180.0 + 0.03 * np.sqrt(3), 100000)
    height_samples = np.sqrt(4 * arm_samples**2 - span_samples**2)
    output = {
        "scissor_height_expression": str(height),
        "scissor_dH_dS_expression": str(derivative),
        "numeric_crosscheck": reference,
        "torque_Nmm": torque_nmm.magnitude,
        "beam_stiffness_N_mm": stiffness.magnitude,
        "uncertainty_inputs": "arm=160±0.03 mm and span=180±0.03 mm standard uncertainty; rectangular Monte Carlo bounds use sqrt(3)",
        "gum_height_mm": height_uncertain.nominal_value,
        "gum_standard_uncertainty_mm": height_uncertain.std_dev,
        "monte_carlo_standard_uncertainty_mm": float(np.std(height_samples, ddof=1)),
        "monte_carlo_p95_mm": float(np.percentile(height_samples, 95)),
        "monte_carlo_seed": 20261113,
        "uncertainties_version": uncertainties.__version__,
        "pint_version": pint.__version__,
        "sympy_version": sp.__version__,
    }
    with (SIMULATION_DIR / "results" / "symbolic_and_unit_checks.json").open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
