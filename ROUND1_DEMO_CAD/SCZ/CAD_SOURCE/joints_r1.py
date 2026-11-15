"""V6 P0-3: assembly constraint-closure checks.

Defines joint datums in PART-LOCAL frames (matching the actual CAD hole centres)
and verifies, across the full stroke, that the placed parts keep every joint
closed: pin-axis coincidence / collinearity, slider-in-guide, rigid relative
pose invariance. A separate CAD face audit confirms the holes physically exist
at the datums (so this is not merely an animation check).
"""
from __future__ import annotations

import math
import numpy as np

import kinematics_r1 as K
from validate_r1 import placements, base_name

Y = np.array([0.0, 1.0, 0.0])
Z = np.array([0.0, 0.0, 1.0])
X = np.array([1.0, 0.0, 0.0])


def _j(kind, a, pa, b, pb, axis, **kw):
    return dict(kind=kind, a=a, pa=np.array(pa, float), b=b, pb=np.array(pb, float),
                axis=np.array(axis, float), **kw)


def joints(cand: str) -> list[dict]:
    J = []
    if cand in ("F09_L82", "F07"):
        ys = K.TOWER_Y[cand]
        lift_max = K.LIFT[cand]
        for i, yc in enumerate(ys):
            J.append(_j("R", f"CAR_{i}", (14, 0, 3), f"COL_{i}", (0, 0, 0), Y,
                        name=f"root_{i}", pin=5.0, hole=5.3, point=True))
            J.append(_j("P", f"CAR_{i}", (4, 15, 7), f"TWR_{i}", (0, 15, 48), Z,
                        name=f"lift_{i}", range=(0, lift_max),
                        guide_pt_b=(0, 15, 30), guide_axis=Z))
        if cand == "F07":
            J.append(_j("R", "COL_0", (16, 0, 137), "ARM", (0, 0, 0), Y,
                        name="arm", pin=5.0, hole=5.3, point=True))
        else:
            J.append(_j("R", "BRG", (16, 0, 137), "ARM", (0, 0, 0), Y,
                        name="arm", pin=5.0, hole=5.3, point=True))
            J.append(_j("RIGID", "COL_0", (0, 0, 162), "XBAR", (0, -65, 162), X, name="col0_xbar"))
            J.append(_j("RIGID", "COL_1", (0, 0, 162), "XBAR", (0, 65, 162), X, name="col1_xbar"))
            J.append(_j("RIGID", "COL_0", (0, -8.5, 132), "BRG", (0, -61.5, 132), Y, name="col0_brg"))
            J.append(_j("RIGID", "COL_1", (0, 8.5, 132), "BRG", (0, 61.5, 132), Y, name="col1_brg"))
            J.append(_j("RIGID", "CAR_0", (2, 10, 17), "SYNC", (8, 55, 17), X, name="car0_sync"))
            J.append(_j("RIGID", "CAR_1", (2, -10, 17), "SYNC", (8, -55, 17), X, name="car1_sync"))
        for i in range(len(ys)):
            J.append(_j("RIGID", f"TWR_{i}", (0, 0, 0), "BASE", (10, ys[i], 10), Z, name=f"twr{i}_base"))
        J.append(_j("RIGID", "BED", (80, 0, 26), "BASE", (80, 0, 26), Z, name="bed_base"))
    elif cand == "SCZ":
        for side, sy in (("L", -1), ("R", 1)):
            yA, yB = sy * K.SCZ["yA"], sy * K.SCZ["yB"]
            J.append(_j("R", f"SLB_{side}", (0, 0, 0), f"ARM_A_{side}", (0, 0, 0), Y,
                        name=f"armA_bot_{side}", pin=4.0, hole=4.3, point=True))
            J.append(_j("R", f"POST_{side}", (0, 0, 18), f"ARM_B_{side}", (0, 0, 0), Y,
                        name=f"armB_bot_{side}", pin=4.0, hole=4.3, point=True))
            J.append(_j("R", f"ARM_A_{side}", (77, 0, 0), f"ARM_B_{side}", (77, 0, 0), Y,
                        name=f"center_{side}", pin=4.0, hole=4.3, point=False))
            J.append(_j("R", "PLAT", (0, yA, 0), f"ARM_A_{side}", (154, 0, 0), Y,
                        name=f"armA_top_{side}", pin=4.0, hole=4.3, point=True))
            J.append(_j("R", f"SLT_{side}", (0, 0, 0), f"ARM_B_{side}", (154, 0, 0), Y,
                        name=f"armB_top_{side}", pin=4.0, hole=4.3, point=True))
            J.append(_j("P", f"SLB_{side}", (0, 0, -10), "BASE", (0, yA, 8), X,
                        name=f"slide_bot_{side}", range=(2.0, 82.0),
                        guide_pt_b=(45, yA, 8), guide_axis=X))
            J.append(_j("P", f"SLT_{side}", (0, 0, 9), "PLAT", (-113, yB, 9), X,
                        name=f"slide_top_{side}", range=(-156.0, -70.0),
                        guide_pt_b=(-113, yB, 9), guide_axis=X, relative=True))
            J.append(_j("RIGID", "SHB", (0, yA, 0), f"SLB_{side}", (0, 0, -12), Y, name=f"shb_slb_{side}"))
            J.append(_j("RIGID", "SHT", (0, yB, 0), f"SLT_{side}", (0, 0, 9), Y, name=f"sht_slt_{side}"))
            J.append(_j("RIGID", f"POST_{side}", (0, 0, 11.5), "BASE", (155, yB, 11.5), Z, name=f"post_{side}_base"))
        J.append(_j("RIGID", "BED", (80, 0, 26), "BASE", (80, 0, 26), Z, name="bed_base"))
    else:  # F08 card (planar, Z pins, layered -> line-type)
        J.append(_j("R", "SLIDER", (0, 0, 9), "COL", (0, 0, 7.5), Z, name="root",
                    pin=3.0, hole=3.3, point=False, holes_on=("b",)))  # pin on slider, hole on col
        J.append(_j("R", "COL", (7.5, 137.5, 7.5), "ARM", (0, 0, 10.5), Z, name="arm", pin=3.0, hole=3.3, point=False))
        J.append(_j("PATH", "SLIDER", (0, 0, 1.5), "CARD", (0, 0, 1.5), Z, name="root_slot",
                    path=[(20, 13), (20, 25.5), (-17.5, 25.5)]))
        J.append(_j("RIGID", "FOOT", (0, 0, 4.5), "CARD", (-30, 3, 4.5), Z, name="foot_card"))
    return J


def _T(pos, R):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = pos
    return T


def closure_check(cand: str, n=2001) -> dict:
    J = joints(cand)
    ts = np.linspace(0, 1, n)
    stats = {j["name"]: dict(max_point=0.0, max_radial=0.0, max_axis_deg=0.0,
                             max_rigid=0.0, max_slide_dev=0.0) for j in J}
    rigid_ref = {}
    for t in ts:
        pl = placements(cand, float(t))
        Ts = {pid: _T(pos, R) for pid, (pos, R) in pl.items()}
        for j in J:
            if j["a"] not in Ts or j["b"] not in Ts:
                continue
            Ta, Tb = Ts[j["a"]], Ts[j["b"]]
            s = stats[j["name"]]
            if j["kind"] == "R":
                wa = (Ta @ np.append(j["pa"], 1))[:3]
                wb = (Tb @ np.append(j["pb"], 1))[:3]
                aa = Ta[:3, :3] @ j["axis"]
                ab = Tb[:3, :3] @ j["axis"]
                aa /= np.linalg.norm(aa); ab /= np.linalg.norm(ab)
                ang = math.degrees(math.acos(min(1.0, abs(float(aa @ ab)))))
                d = wa - wb
                axial = float(d @ aa)
                radial = float(np.linalg.norm(d - axial * aa))
                s["max_point"] = max(s["max_point"], float(np.linalg.norm(d)))
                s["max_radial"] = max(s["max_radial"], radial)
                s["max_axis_deg"] = max(s["max_axis_deg"], ang)
            elif j["kind"] == "RIGID":
                rel = np.linalg.inv(Ta) @ Tb
                if j["name"] not in rigid_ref:
                    rigid_ref[j["name"]] = rel
                dev = float(np.max(np.abs(rel - rigid_ref[j["name"]])))
                s["max_rigid"] = max(s["max_rigid"], dev)
            elif j["kind"] == "P":
                # slider datum must stay on the guide axis line (guide part frame)
                wa = (Ta @ np.append(j["pa"], 1))[:3]
                wb = (Tb @ np.append(j["guide_pt_b"], 1))[:3]
                ax = Tb[:3, :3] @ j["guide_axis"]
                ax = ax / np.linalg.norm(ax)
                d = wa - wb
                dev = float(np.linalg.norm(d - float(d @ ax) * ax))
                s["max_slide_dev"] = max(s["max_slide_dev"], dev)
            elif j["kind"] == "PATH":
                wa = (Ta @ np.append(j["pa"], 1))[:3]
                pts = [np.array([p[0], p[1], wa[2]]) for p in j["path"]]
                best = 1e9
                for u, v in zip(pts[:-1], pts[1:]):
                    seg = v - u
                    tt = max(0.0, min(1.0, float((wa - u) @ seg) / float(seg @ seg)))
                    best = min(best, float(np.linalg.norm(wa - (u + tt * seg))))
                s["max_slide_dev"] = max(s["max_slide_dev"], best)
    # acceptance
    fails = []
    for j in J:
        s = stats[j["name"]]
        if j["kind"] == "R":
            if s["max_axis_deg"] > 0.01 or s["max_radial"] > 0.05:
                fails.append((j["name"], "axis/radial", s))
            if j.get("point") and s["max_point"] > 0.05:
                fails.append((j["name"], "axial", s))
        elif j["kind"] == "RIGID":
            if s["max_rigid"] > 1e-6:
                fails.append((j["name"], "rigid", s))
        elif j["kind"] in ("P", "PATH"):
            if s["max_slide_dev"] > 0.05:
                fails.append((j["name"], "slide", s))
    return dict(steps=n, n_joints=len(J), stats=stats, fails=fails,
                passed=not fails)


def pin_interface_audit(cand: str) -> list[dict]:
    """Static pin/hole interface table for R joints (diameter clearance + engagement)."""
    rows = []
    for j in joints(cand):
        if j["kind"] != "R":
            continue
        pin = j.get("pin"); hole = j.get("hole")
        if pin is None:
            continue
        rows.append(dict(joint=j["name"], pin_d=pin, hole_d=hole,
                         diametral_clearance=round(hole - pin, 3),
                         ok=0.15 <= hole - pin <= 0.6))
    return rows


def _part_cylinders(part) -> list[dict]:
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    out = []
    for f in part.faces():
        if "CYLINDER" not in str(f.geom_type):
            continue
        s = BRepAdaptor_Surface(f.wrapped)
        cyl = s.Cylinder(); ax = cyl.Axis(); d = ax.Direction(); loc = ax.Location()
        out.append(dict(r=cyl.Radius(),
                        dir=np.array([d.X(), d.Y(), d.Z()]),
                        loc=np.array([loc.X(), loc.Y(), loc.Z()])))
    return out


def _build_parts(cand: str) -> dict:
    import build_gantry as G
    import build_scz as Z
    import build_f08 as E
    if cand in ("F09_L82", "F07"):
        return G.build_gantry_parts(cand)
    if cand == "SCZ":
        return {"ARM": Z.build_arm(), "POST": Z.build_post(), "SLB": Z.build_slider_bottom(),
                "SLT": Z.build_slider_top(), "SHB": Z.build_shaft_bottom(),
                "SHT": Z.build_shaft_top(), "PLAT": Z.build_platform(),
                "BASE": Z.build_scz_base(), "BED": G.build_bed()}
    return {"CARD": E.build_card(), "SLIDER": E.build_slider(), "COL": E.build_column(),
            "ARM": E.build_arm(), "FOOT": E.build_foot()}


def cad_hole_audit(cand: str) -> dict:
    """Confirm each R-joint datum hole physically exists in the CAD part:
    a cylindrical face of the right radius, parallel axis, passing through the datum."""
    parts = _build_parts(cand)
    cyls = {pid: _part_cylinders(p) for pid, p in parts.items()}
    rows = []
    for j in joints(cand):
        if j["kind"] != "R" or j.get("hole") is None:
            continue
        holes_on = j.get("holes_on", ("a", "b"))
        for key, pid, pt in (("a", j["a"], j["pa"]), ("b", j["b"], j["pb"])):
            if key not in holes_on:
                continue
            base = base_name(pid)
            target_r = j["hole"] / 2
            best = None
            for c in cyls.get(base, []):
                if abs(c["r"] - target_r) > 0.06:
                    continue
                ax = c["dir"] / np.linalg.norm(c["dir"])
                if abs(float(ax @ j["axis"])) < 0.999:
                    continue
                d = pt - c["loc"]
                radial = float(np.linalg.norm(d - float(d @ ax) * ax))
                if best is None or radial < best:
                    best = radial
            rows.append(dict(joint=j["name"], part=pid, hole_d=j["hole"],
                             axis_offset_mm=round(best, 4) if best is not None else None,
                             found=best is not None and best < 0.06))
    missing = [r for r in rows if not r["found"]]
    return dict(n_checks=len(rows), missing=missing, passed=not missing)
