"""Standard 3MF print-platform projects (geometry only, no slicer profile).
Bambu Studio / PrusaSlicer / Cura import standard 3MF. Parts auto-laid on 250x250.
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import trimesh

from validate_r1 import ROOT, CAND_DIRS

# print orientation: rotation (deg about X,Y,Z) applied before laying flat on z=0
ORIENT = {
    "BASE": (0, 0, 0), "BED": (0, 0, 0), "TWR": (0, 0, 0),
    "CAR": (0, -90, 0),          # knob axis up; bushing holes horizontal (bridge)
    "COL": (0, 0, 0),            # vertical tube, as modeled
    "ARM": (0, 0, 0),
    "SYNC": (0, 0, 0), "XBAR": (0, 0, 0), "BRG": (90, 0, 0),
    "SCZ-ARM": (90, 0, 0),       # 3mm thickness -> Z
    "SCZ-POST": (0, 0, 0), "SCZ-SLB": (0, 0, 0), "SCZ-SLT": (0, 0, 0),
    "SCZ-SHB": (0, 0, 90), "SCZ-SHT": (0, 0, 90),  # shaft along X
    "SCZ-PLAT": (0, 0, 0), "SCZ-BASE": (0, 0, 0),
    "F08-CARD": (0, 0, 0), "F08-SLIDER": (0, 0, 0), "F08-COL": (0, 0, 0),
    "F08-ARM": (0, 0, 0), "F08-FOOT": (0, 0, 0),
}


def orient_key(pid: str) -> str:
    if pid in ORIENT:
        return pid
    for k in ORIENT:
        if pid.startswith(k):
            return k
    return ""


def rot_matrix(rx, ry, rz):
    m = np.eye(4)
    for axis, ang in zip("xyz", (rx, ry, rz)):
        if ang == 0:
            continue
        r = np.radians(ang)
        c, s = np.cos(r), np.sin(r)
        R = np.eye(4)
        if axis == "x":
            R[1, 1], R[1, 2], R[2, 1], R[2, 2] = c, -s, s, c
        elif axis == "y":
            R[0, 0], R[0, 2], R[2, 0], R[2, 2] = c, s, -s, c
        else:
            R[0, 0], R[0, 1], R[1, 0], R[1, 1] = c, -s, s, c
        m = R @ m
    return m


def load_oriented(stl: Path, pid: str) -> trimesh.Trimesh:
    m = trimesh.load(stl, force="mesh")
    key = pid if pid in ORIENT else orient_key(pid.split("-", 1)[1])
    rx, ry, rz = ORIENT.get(key, (0, 0, 0))
    m.apply_transform(rot_matrix(rx, ry, rz))
    m.apply_translation([0, 0, -m.bounds[0][2]])
    return m


def shelf_pack(items: list[tuple[str, trimesh.Trimesh]], plate=248.0, gap=4.0):
    """items: (instance_name, mesh). Returns list of pages; page = list (name, mesh, x, y)."""
    pages = []
    cur = []
    x, y, shelf_h = gap, gap, 0.0
    for name, m in sorted(items, key=lambda it: -it[1].extents[1]):
        w, d = m.extents[0], m.extents[1]
        if x + w + gap > plate:
            x = gap
            y += shelf_h + gap
            shelf_h = 0.0
        if y + d + gap > plate:
            pages.append(cur)
            cur = []
            x, y, shelf_h = gap, gap, 0.0
        cur.append((name, m, x, y))
        x += w + gap
        shelf_h = max(shelf_h, d)
    if cur:
        pages.append(cur)
    return pages


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""
RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""


def write_3mf(path: Path, laid: list, title: str):
    objs = []
    items = []
    for i, (name, m, x, y) in enumerate(laid, start=1):
        v = m.vertices
        f = m.faces
        vs = "".join(f'<vertex x="{p[0]:.4f}" y="{p[1]:.4f}" z="{p[2]:.4f}"/>' for p in v)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
        objs.append(f'<object id="{i}" type="model" name="{name}"><mesh><vertices>{vs}</vertices>'
                    f'<triangles>{ts}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {x:.3f} {y:.3f} 0"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata>'
             f'<resources>{"".join(objs)}</resources>'
             f'<build>{"".join(items)}</build></model>')
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)


def build_candidate_3mf(cand: str):
    cdir = ROOT / CAND_DIRS[cand]
    man = json.loads((cdir / "VALIDATION" / "parts_manifest.json").read_text(encoding="utf-8"))
    items = []
    for r in man["parts"]:
        pid = r["part_id"]
        qty = r.get("qty", 1)
        m = load_oriented(cdir / r["stl"], pid)
        for q in range(qty):
            items.append((f"{pid}_{q+1}", m))
    laid_pages = shelf_pack(items)
    outs = []
    for i, laid in enumerate(laid_pages, start=1):
        suffix = f"_{i}" if len(laid_pages) > 1 else ""
        out = cdir / "3MF" / f"{cand}_plate{suffix}.3mf"
        write_3mf(out, laid, f"ROUND1 {cand} demo plate {i}/{len(laid_pages)} (geometry only)")
        outs.append(out)
        print(f"[{cand}] 3MF plate {i}: {len(laid)} instances -> {out}")
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cands", nargs="*", default=list(CAND_DIRS))
    args = ap.parse_args()
    for c in args.cands:
        build_candidate_3mf(c)


if __name__ == "__main__":
    main()
