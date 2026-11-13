import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

SIMULATION_DIR = Path(__file__).resolve().parents[1]
PACKAGES = [
    "numpy", "scipy", "sympy", "pandas", "matplotlib", "pymoo", "shapely",
    "trimesh", "build123d", "pillow", "imageio", "imageio-ffmpeg", "pyDOE3",
    "pint", "uncertainties", "cadquery-ocp-novtk",
]


def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SIMULATION_DIR.parent, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=SIMULATION_DIR.parent, text=True).strip())
    data = {
        "python": sys.version,
        "platform": platform.platform(),
        "source_commit_base": commit,
        "working_tree_dirty_at_run": dirty,
        "master_seed": 20261113,
        "packages": {name: importlib.metadata.version(name) for name in PACKAGES},
        "not_available": {
            "pybullet": "not used: local source build requires unavailable MSVC; no dynamics claim",
            "CalculiX": "not installed; no 3D FEA claim",
            "FreeCAD": "not installed; build123d/OpenCascade used instead",
        },
    }
    with (SIMULATION_DIR / "results" / "environment.json").open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
