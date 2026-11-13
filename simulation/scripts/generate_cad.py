import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from build123d import Unit, export_step, export_stl

SIMULATION_DIR = Path(__file__).resolve().parents[1]
RESULTS = SIMULATION_DIR / "results"
CAD = SIMULATION_DIR / "cad"
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.evaluate import evaluate_candidate
from foldsim.registry import load_candidates


def _polygons(geometry):
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _polygons(part)


def _width(name):
    if name == "base":
        return 347.0
    if name in {"bed", "y_module"}:
        return 180.0
    if "column" in name or "stage" in name:
        return 40.0
    if name in {"crossbar", "top_frame"}:
        return 300.0
    return 30.0


def _model_source(candidate_id, shapes, bounds, assumption):
    min_x, min_z, max_x, max_z = bounds
    return f'''"""{candidate_id} folded concept assembly.

Process: conceptual assembly; load-bearing joints require machined metal after measurement.
Material: aluminium extrusion and unspecified metal joint hardware.
Interfaces: every pivot, slot, lock and accessory dimension is an unchecked concept assumption.
{assumption}
"""
from build123d import *

POLYGONS_MM = {shapes!r}
EXPECTED_BOUNDS_MM = ({min_x}, {min_z}, {max_x}, {max_z})


def interfaces() -> list[dict]:
    return []


def checks() -> list[dict]:
    min_x, min_z, max_x, max_z = EXPECTED_BOUNDS_MM
    return [
        {{"feature": "expected folded X span", "bbox_x": {{"min": 0.0, "max": max_x - min_x + 0.1}}}},
        {{"feature": "expected folded Z span", "bbox_z": {{"min": 0.0, "max": max_z - min_z + 0.1}}}},
    ]


def build() -> Part:
    with BuildPart() as assembly:
        for name, width_mm, points_mm in POLYGONS_MM:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    Polyline(points_mm + [points_mm[0]])
                make_face()
            extrude(amount=width_mm)
    return assembly.part
'''


def main():
    with (RESULTS / "selection.json").open(encoding="utf-8") as handle:
        selection = json.load(handle)
    third_path = RESULTS / "third_option_analysis.json"
    entries = [
        (recommendation["id"], recommendation["parameters"], "recommended")
        for recommendation in selection["recommendations"]
    ]
    if third_path.is_file():
        with third_path.open(encoding="utf-8") as handle:
            third = json.load(handle)
        entries.append((third["selected_third_option"], third["selected"]["parameters"], "third_exploratory"))
        if third["fallback_option"] != third["selected_third_option"]:
            fallback = next(row for row in third["candidate_metrics"] if row["id"] == third["fallback_option"])
            entries.append((fallback["id"], fallback["parameters"], "third_fallback"))
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    manifest = []
    for candidate_id, parameters, role in entries:
        spec = candidates[candidate_id]
        evaluated = evaluate_candidate(spec, parameters=parameters, steps=31)
        state = evaluated["trace"][-1]
        shapes = []
        for name, geometry in list(state["fixed"].items()) + list(state["moving"].items()):
            for polygon in _polygons(geometry):
                simplified = polygon.simplify(0.5, preserve_topology=True)
                points = [(round(x, 5), round(z, 5)) for x, z in simplified.exterior.coords[:-1]]
                if len(points) >= 3:
                    shapes.append((name, _width(name), points))
        all_geometries = list(state["fixed"].values()) + list(state["moving"].values())
        min_x = min(geometry.bounds[0] for geometry in all_geometries)
        min_z = min(geometry.bounds[1] for geometry in all_geometries)
        max_x = max(geometry.bounds[2] for geometry in all_geometries)
        max_z = max(geometry.bounds[3] for geometry in all_geometries)
        outdir = CAD / candidate_id
        outdir.mkdir(parents=True, exist_ok=True)
        model_path = outdir / f"{candidate_id.lower()}_model.py"
        source = _model_source(candidate_id, shapes, (min_x, min_z, max_x, max_z), spec["assumption"])
        model_path.write_text(source, encoding="utf-8")
        module_spec = importlib.util.spec_from_file_location(f"{candidate_id.lower()}_model", model_path)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        part = module.build()
        step_path = outdir / f"{candidate_id.lower()}.step"
        stl_path = outdir / f"{candidate_id.lower()}.stl"
        export_step(part, str(step_path), unit=Unit.MM)
        export_stl(part, str(stl_path))
        bbox = part.bounding_box()
        record = {
            "id": candidate_id,
            "role": role,
            "parameters": parameters,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "is_valid": part.is_valid,
            "solid_count": len(part.solids()),
            "volume_mm3": part.volume,
            "bbox_mm": [bbox.min.X, bbox.min.Y, bbox.min.Z, bbox.max.X, bbox.max.Y, bbox.max.Z],
            "interfaces": "all custom and unchecked; no vendor or measured interface claimed",
            "files": [step_path.name, stl_path.name, model_path.name],
        }
        (outdir / f"{candidate_id.lower()}.manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append(record)
        print(candidate_id, "STEP/STL", "valid" if record["is_valid"] else "INVALID", record["solid_count"], "solids")
    (CAD / "cad_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
