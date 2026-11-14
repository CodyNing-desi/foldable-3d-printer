import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

SIMULATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.fea import solve_cantilever_beam

LENGTH_MM = 345.0
WIDTH_MM = 20.0
HEIGHT_MM = 16.1
E_MPA = 69000.0
POISSON = 0.33
TIP_LOAD_N = 10.0
LEVELS = (20, 40, 80, 160)


def main():
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font_path)).get_name()
    plt.rcParams["axes.unicode_minus"] = False
    rows = []
    for elements_along in LEVELS:
        result = solve_cantilever_beam(
            LENGTH_MM, WIDTH_MM, HEIGHT_MM, E_MPA, POISSON, TIP_LOAD_N,
            elements_along=elements_along, elements_width=4, elements_height=4,
        )
        rows.append({
            "elements_along": elements_along,
            "elements": result["elements"],
            "dofs": result["dofs"],
            "fea_tip_deflection_mm": result["fea_tip_deflection_mm"],
            "euler_bernoulli_tip_deflection_mm": result["euler_bernoulli_tip_deflection_mm"],
            "relative_error": result["relative_error"],
            "second_moment_mm4": result["second_moment_mm4"],
        })
        print(elements_along, result["fea_tip_deflection_mm"], result["relative_error"])
    output = {
        "simulation_level": "L3_linear_elastic_hex_fea_for_equivalent_beam_only",
        "model": {
            "length_mm": LENGTH_MM,
            "width_mm": WIDTH_MM,
            "height_mm": HEIGHT_MM,
            "E_MPa": E_MPA,
            "poisson": POISSON,
            "tip_load_N": TIP_LOAD_N,
            "second_moment_mm4": WIDTH_MM * HEIGHT_MM**3 / 12,
        },
        "mesh_convergence": rows,
        "finest_relative_error": rows[-1]["relative_error"],
        "limitation": "Equivalent solid rectangular cantilever with I=7000 mm^4; this validates the reduced beam formula and FE workflow, not the T-slot profile, joint stiffness, full-frame load path, plasticity, buckling, fatigue, or physical printer accuracy.",
    }
    (SIMULATION_DIR / "results" / "beam_fea.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(7.5, 5), layout="constrained")
    ax.plot(
        [row["elements"] for row in rows],
        [row["fea_tip_deflection_mm"] for row in rows],
        marker="o", color="#0072B2", label="三维六面体线弹性 FEA",
    )
    ax.axhline(rows[-1]["euler_bernoulli_tip_deflection_mm"], color="#D55E00", linestyle="--", label="Euler–Bernoulli 解")
    ax.set_xscale("log")
    ax.set_xlabel("单元数")
    ax.set_ylabel("10 N 端部挠度 / mm")
    ax.set_title("等效悬臂梁网格收敛｜不是整机或铰链有限元")
    ax.legend()
    ax.grid(alpha=0.2)
    target = SIMULATION_DIR / "figures" / "fea_convergence"
    fig.savefig(target.with_suffix(".png"), dpi=180, facecolor="white")
    fig.savefig(target.with_suffix(".svg"), facecolor="white")
    plt.close(fig)
    svg = target.with_suffix(".svg")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    print("wrote results/beam_fea.json and figures/fea_convergence.*")


if __name__ == "__main__":
    main()
