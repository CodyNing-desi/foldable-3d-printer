"""ROUND1_DEMO_CAD shared parametric kernel (build123d).

All dimensions in mm. Demo link geometry = V3.2.1 full-scale * SCALE (1:2).
Pins / hinge bosses are locally enlarged for FDM assembly (documented deviation).
Source of full-scale parameters: repo PR#1 (sync/v2-to-v3_2_1)
  simulation_v3_2_1/config/candidates_v3_2_1.json
  simulation_v3_2_1/scripts/run_v3_2_1_verification.py  (frozen lineup overrides)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from build123d import (
    Axis, Box, Cylinder, Part, Pos, Rot, Compound, Location,
    export_step, export_stl, fillet, chamfer,
)

CAD_VERSION = "R1-V5"
SCALE = 0.5  # link geometry scale vs V3.2.1 full size

# ---------------- fits / materials ----------------
CLR_ROT = 0.30    # diametral clearance, rotating pin-in-hole
CLR_SLD = 0.40    # diametral clearance, sliding fits
CLR_SNAP = 0.15   # snap / press features (PETG)

DENSITY = {"PLA": 1.24, "PETG": 1.27}  # g/cm^3 solid
# effective solid fraction for mass estimate: 3 walls + 20% infill typical Bambu default
INFILL_FACTOR = 0.60

PLATE = (256.0, 256.0, 256.0)  # Bambu A1 / P1 / X1 class envelope
PLATE_SAFE = (250.0, 250.0, 250.0)

PIN_STD = {
    5.0: dict(head_d=8.0, head_h=2.0, groove_d=4.4, groove_w=1.4),
    4.0: dict(head_d=7.0, head_h=1.8, groove_d=3.4, groove_w=1.2),
    3.0: dict(head_d=5.5, head_h=1.5, groove_d=2.5, groove_w=1.0),
    2.5: dict(head_d=4.5, head_h=1.2, groove_d=2.0, groove_w=0.8),
}


def pin(d: float, length: float) -> Part:
    """Headed pin along +Z, head at z=0..head_h, retention groove near tail."""
    s = PIN_STD[d]
    p = Pos(0, 0, s["head_h"] / 2) * Cylinder(s["head_d"] / 2, s["head_h"])
    shaft = Pos(0, 0, s["head_h"] + (length - s["head_h"]) / 2) * Cylinder(d / 2, length - s["head_h"])
    p = p + shaft
    g0 = length - s["groove_w"] - 1.0
    ring = Pos(0, 0, g0 + s["groove_w"] / 2) * (
        Cylinder(d / 2 + 0.01, s["groove_w"]) - Cylinder(s["groove_d"] / 2, s["groove_w"] + 0.02)
    )
    p = p - ring
    p.label = f"PIN{d:g}-L{length:g}"
    return p


def clip(d: float) -> Part:
    """C-clip (E-clip style) for pin groove d, flat in XY, thickness along Z. PETG."""
    s = PIN_STD[d]
    t = {5.0: 2.0, 4.0: 1.8, 3.0: 1.6}[d]
    r_in = s["groove_d"] / 2 + 0.05
    r_out = r_in + 2.2
    ring = Cylinder(r_out, t) - Cylinder(r_in, t + 0.02)
    # opening wedge toward +X (mouth slightly wider than groove for snap-in)
    mouth = s["groove_d"] * 0.92
    wedge = Pos(r_out, 0, 0) * Box(2 * r_out + 2, mouth, t + 0.04)
    # taper the mouth entry
    c = ring - wedge
    c.label = f"CLIP{d:g}"
    return c


def hole_cyl(d: float, length: float, clearance: float = CLR_ROT) -> Part:
    return Cylinder((d + clearance) / 2, length)


def y_hole(d: float, length: float, clearance: float = CLR_ROT) -> Part:
    """Hole along Y axis, centered."""
    return Rot(90, 0, 0) * hole_cyl(d, length, clearance)


def x_hole(d: float, length: float, clearance: float = CLR_ROT) -> Part:
    return Rot(0, 90, 0) * hole_cyl(d, length, clearance)


def z_hole(d: float, length: float, clearance: float = CLR_ROT) -> Part:
    return hole_cyl(d, length, clearance)


def rounded_slot_x(length: float, width: float, height: float) -> Part:
    """Slot along X, centered, stadium profile (for sliders / card slots)."""
    r = width / 2
    body = Box(length - width, width, height)
    e1 = Pos((length - width) / 2, 0, 0) * Cylinder(r, height)
    e2 = Pos(-(length - width) / 2, 0, 0) * Cylinder(r, height)
    return body + e1 + e2


def label_part(p: Part, label: str) -> Part:
    p.label = label
    return p


# ---------------- export helpers ----------------
import shutil
import tempfile


def safe_export_stl(part, path, tolerance: float = 0.05, angular_tolerance: float = 0.2):
    """OCP mesher silently fails on non-ASCII absolute paths; fall back to ASCII temp + move."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = export_stl(part, str(path), tolerance=tolerance, angular_tolerance=angular_tolerance)
    if not ok or not path.exists() or path.stat().st_size == 0:
        tmp = Path(tempfile.gettempdir()) / f"r1_stl_{abs(hash(str(path))) % 10**10}.stl"
        ok2 = export_stl(part, str(tmp), tolerance=tolerance, angular_tolerance=angular_tolerance)
        if not ok2 or not tmp.exists():
            raise RuntimeError(f"STL export failed: {path}")
        shutil.move(str(tmp), str(path))
    return True


def export_part(part: Part, cand_dir: Path, part_id: str, material: str,
                subdir_stl: str = "STL", subdir_step: str = "STEP") -> dict:
    stl_dir = cand_dir / subdir_stl
    step_dir = cand_dir / subdir_step
    stl_dir.mkdir(parents=True, exist_ok=True)
    step_dir.mkdir(parents=True, exist_ok=True)
    part.label = part_id
    stl_path = stl_dir / f"{part_id}.stl"
    step_path = step_dir / f"{part_id}.step"
    safe_export_stl(part, stl_path)
    export_step(part, str(step_path))
    bb = part.bounding_box()
    vol = part.volume
    rec = dict(
        part_id=part_id, material=material, cad_version=CAD_VERSION,
        volume_cm3=round(vol / 1000.0, 3),
        mass_est_g=round(vol / 1000.0 * DENSITY[material] * INFILL_FACTOR, 1),
        bbox_mm=[round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
        stl=str(stl_path.relative_to(cand_dir)), step=str(step_path.relative_to(cand_dir)),
    )
    return rec


def export_assembly(parts: list[tuple[str, Part, Location]], path: Path, name: str):
    children = []
    for label, p, loc in parts:
        q = loc * p
        q.label = label
        children.append(q)
    comp = Compound(children=children)
    comp.label = name
    path.parent.mkdir(parents=True, exist_ok=True)
    export_step(comp, str(path))
    return comp


def save_manifest(records: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(dict(cad_version=CAD_VERSION, scale=SCALE, parts=records), f,
                  ensure_ascii=False, indent=2)
