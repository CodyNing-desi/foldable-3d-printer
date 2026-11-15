"""Build & export all ROUND1 demo candidates. Run with the project venv python."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build123d import Pos, Rot, Location, Compound, export_stl

import common_r1 as C
import kinematics_r1 as K
import build_gantry as G
import build_scz as Z
import build_f08 as E

ROOT = C.deliverable_root()

CAND_DIRS = {"F09_L82": "F09_L82", "F07": "F07", "SCZ": "SCZ", "F08_OPTIONAL": "F08_OPTIONAL"}
PREFIX = {"F09_L82": "F09", "F07": "F07", "SCZ": "SCZ", "F08_OPTIONAL": "F08"}


def export_candidate(cand: str):
    out = ROOT / CAND_DIRS[cand]
    out.mkdir(parents=True, exist_ok=True)
    pfx = PREFIX[cand]
    records = []

    if cand in ("F09_L82", "F07"):
        parts = G.build_gantry_parts(cand)
        mat = {k: "PLA" for k in parts}
        mat["ARM"] = "PLA"
        qty = {"TWR": 2, "CAR": 2, "COL": 2} if cand == "F09_L82" else {}
        for pid, part in parts.items():
            full = f"{pfx}-{pid}"
            r = C.export_part(part, out, full, mat[pid])
            r["qty"] = qty.get(pid, 1)
            records.append(r)
        for pid, part, m, qty in G.gantry_pins(cand):
            full = f"{pfx}-{pid}"
            r = C.export_part(part, out, full, m)
            r["qty"] = qty
            records.append(r)
        # assemblies at key phase states
        (out / "ASSEMBLY").mkdir(parents=True, exist_ok=True)
        for name, t in (("open", 0.0), ("armfold", 0.20), ("lifted", 0.42),
                        ("midfold", 0.70), ("folded", 1.0)):
            pv = K.phase_values(cand, t)
            asm = G.gantry_assembly(cand, parts, pv["arm"], pv["lift"], pv["root"])
            comp = C.export_assembly(asm, out / "STEP" / f"{pfx}_asm_{name}.step", f"{pfx}_asm_{name}")
            C.safe_export_stl(comp, out / "ASSEMBLY" / f"{pfx}_asm_{name}.stl", tolerance=0.1)

    elif cand == "SCZ":
        parts = {"ARM": Z.build_arm(), "POST": Z.build_post(),
                 "SLB": Z.build_slider_bottom(), "SLT": Z.build_slider_top(),
                 "SHB": Z.build_shaft_bottom(), "SHT": Z.build_shaft_top(),
                 "PLAT": Z.build_platform()}
        # SCZ-dedicated base (shaft window + feet); bed shared
        parts["BASE"] = Z.build_scz_base()
        parts["BED"] = G.build_bed()
        qty = {"ARM": 4, "POST": 2, "SLB": 2, "SLT": 2}
        for pid, part in parts.items():
            full = f"{pfx}-{pid}"
            m = "PLA" if pid in ("BASE", "BED", "PLAT", "POST") else "PETG"
            r = C.export_part(part, out, full, m)
            r["qty"] = qty.get(pid, 1)
            records.append(r)
        for pid, part, m, qty in Z.scz_pins():
            full = f"{pfx}-{pid}"
            r = C.export_part(part, out, full, m)
            r["qty"] = qty
            records.append(r)
        for name, t in (("open", 0.0), ("mid", 0.55), ("folded", 1.0)):
            pv = K.phase_values(cand, t)
            pl = K.scz_placements(pv["H"])
            asm = []
            for pid, (pos, rot) in pl.items():
                asm.append((pid, parts[pid.split("_")[0]], Location(Pos(*pos) * Rot(0, rot, 0))))
            for pid, loc in Z.scz_plat_extra(pv["H"]):
                asm.append((pid, C.pin(4, 16), loc))
            comp = C.export_assembly(asm, out / "STEP" / f"{pfx}_asm_{name}.step", f"{pfx}_asm_{name}")
            (out / "ASSEMBLY").mkdir(parents=True, exist_ok=True)
            C.safe_export_stl(comp, out / "ASSEMBLY" / f"{pfx}_asm_{name}.stl", tolerance=0.1)

    elif cand == "F08_OPTIONAL":
        parts = {"CARD": E.build_card(), "SLIDER": E.build_slider(),
                 "COL": E.build_column(), "ARM": E.build_arm(), "FOOT": E.build_foot()}
        for pid, part in parts.items():
            full = f"{pfx}-{pid}"
            m = "PLA" if pid in ("CARD", "COL", "ARM") else "PETG"
            records.append(C.export_part(part, out, full, m))
        for pid, part, m, qty in E.f08_pins():
            full = f"{pfx}-{pid}"
            r = C.export_part(part, out, full, m)
            r["qty"] = qty
            records.append(r)
        for name, t in (("open", 0.0), ("liftshift", 0.42), ("folded", 1.0)):
            pv = K.phase_values(cand, t)
            pl = K.f08_placements(pv["arm"], pv["lift"], pv["shift"], pv["root"])
            asm = [(pid, parts[pid], Location(Pos(*pos) * Rot(0, 0, rot)))
                   for pid, (pos, rot) in pl.items()]
            comp = C.export_assembly(asm, out / "STEP" / f"{pfx}_asm_{name}.step", f"{pfx}_asm_{name}")
            (out / "ASSEMBLY").mkdir(parents=True, exist_ok=True)
            C.safe_export_stl(comp, out / "ASSEMBLY" / f"{pfx}_asm_{name}.stl", tolerance=0.1)

    C.save_manifest(records, out / "VALIDATION" / "parts_manifest.json")
    print(f"[{cand}] exported {len(records)} unique parts -> {out}")
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cands", nargs="*", default=list(CAND_DIRS))
    args = ap.parse_args()
    all_recs = {}
    for cand in args.cands:
        all_recs[cand] = export_candidate(cand)
    with (ROOT / "build_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(all_recs, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
