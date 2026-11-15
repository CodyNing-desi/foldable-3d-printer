"""ROUND1分级验证引擎: L1 参数/几何, L2 全行程运动+碰撞, L3 可制造性.

证据等级声明:
- L2 采用 2001 步密集采样 + 精确网格布尔穿透体积 + 关节解析限位 + 关键相位扫掠凸包
  (保守上界)。**不是**解析连续碰撞认证; 采样间穿透理论上仍可能漏检, 凸包检查对关键对
  提供保守覆盖。所有结果如实输出, 不虚构 PASS。
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import trimesh

import kinematics_r1 as K

import common_r1 as C
ROOT = C.deliverable_root()
CAND_DIRS = {"F09_L82": "F09_L82", "F07": "F07", "SCZ": "SCZ", "F08_OPTIONAL": "F08_OPTIONAL"}
PREFIX = {"F09_L82": "F09", "F07": "F07", "SCZ": "SCZ", "F08_OPTIONAL": "F08"}

# 允许的接触/配合对 (运动副作用: 销-孔, 滑块-槽, 舌-叉耳 等名义接触)
ALLOW_CONTACT = {
    "F09_L82": {
        ("CAR", "TWR"), ("CAR", "COL"), ("COL", "CAR"), ("COL", "XBAR"), ("COL", "BRG"),
        ("XBAR", "COL"), ("BRG", "COL"), ("SYNC", "CAR"), ("CAR", "SYNC"),
        ("TWR", "BASE"), ("COL", "BASE"), ("ARM", "BRG"), ("BED", "BASE"),
        ("CAR", "BASE"), ("SYNC", "BASE"), ("XBAR", "BASE"), ("BRG", "BASE"),
    },
    "F07": {
        ("CAR", "TWR"), ("CAR", "COL"), ("COL", "CAR"), ("TWR", "BASE"),
        ("COL", "BASE"), ("ARM", "COL"), ("BED", "BASE"), ("CAR", "BASE"),
    },
    "SCZ": {
        ("ARM", "SLB"), ("ARM", "PLAT"), ("ARM", "POST"), ("ARM", "SLT"), ("ARM", "ARM"),
        ("SLB", "BASE"), ("POST", "BASE"), ("SLT", "PLAT"),
        ("SHB", "SLB"), ("SHT", "SLT"),
        ("SHT", "PLAT"), ("BED", "BASE"),
        ("SHB", "BASE"), ("ARM", "BASE"),
    },
    "F08_OPTIONAL": {
        ("COL", "SLIDER"), ("SLIDER", "COL"), ("COL", "CARD"), ("ARM", "COL"),
        ("COL", "ARM"), ("SLIDER", "CARD"), ("FOOT", "CARD"), ("ARM", "CARD"),
    },
}


def base_name(pid: str) -> str:
    return pid.split("_")[0]


def allowed(cand: str, a: str, b: str) -> bool:
    ba, bb = base_name(a), base_name(b)
    return (ba, bb) in ALLOW_CONTACT[cand] or (bb, ba) in ALLOW_CONTACT[cand]


def load_parts(cand: str) -> dict[str, trimesh.Trimesh]:
    d = ROOT / CAND_DIRS[cand] / "STL"
    parts = {}
    for f in sorted(d.glob("*.stl")):
        pid = f.stem.split("-", 1)[1]
        if pid.startswith(("PIN", "CLIP")):
            continue
        parts[pid] = trimesh.load(f, force="mesh")
    return parts


def placements(cand: str, t: float) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """pid -> (translation, rotation matrix) world."""
    pv = K.phase_values(cand, t)
    out = {}
    if cand in ("F09_L82", "F07"):
        pl = K.gantry_placements(cand, pv["arm"], pv["lift"], pv["root"])
        for pid, val in pl.items():
            if pid == "ARM":
                continue
            pos, rot = val
            out[pid] = (np.array(pos), rot_y(rot))
        apos, arot = K.arm_placement(cand, pv["arm"], pv["lift"], pv["root"])
        out["ARM"] = (np.array(apos), rot_y(arot))
    elif cand == "SCZ":
        for pid, (pos, rot) in K.scz_placements(pv["H"]).items():
            out[pid] = (np.array(pos), rot_y(rot))
    else:
        for pid, (pos, rot) in K.f08_placements(pv["arm"], pv["lift"], pv["shift"], pv["root"]).items():
            out[pid] = (np.array(pos), rot_z(rot))
    return out


def rot_y(deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def placed_mesh(mesh: trimesh.Trimesh, pos, R) -> trimesh.Trimesh:
    m = mesh.copy()
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = pos
    m.apply_transform(T)
    return m


def intersection_volume(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    try:
        inter = trimesh.boolean.intersection([a, b], engine="manifold")
        if inter is None or len(inter.faces) == 0:
            return 0.0
        return float(abs(inter.volume))
    except Exception:
        return -1.0  # unresolved


def aabb_overlap(a: trimesh.Trimesh, b: trimesh.Trimesh, tol=0.05) -> bool:
    return bool(np.all(a.bounds[1] + tol >= b.bounds[0]) and np.all(b.bounds[1] + tol >= a.bounds[0]))


def sweep_check(cand: str, parts, n=2001):
    ids = list(placements(cand, 0.0).keys())
    worst = {}
    unresolved = []
    penetrations = []
    ts = np.linspace(0, 1, n)
    for i, t in enumerate(ts):
        pl = placements(cand, float(t))
        meshes = {pid: placed_mesh(parts[base_name(pid)], pos, R) for pid, (pos, R) in pl.items()}
        for ia in range(len(ids)):
            for ib in range(ia + 1, len(ids)):
                a, b = ids[ia], ids[ib]
                if allowed(cand, a, b):
                    continue
                ma, mb = meshes[a], meshes[b]
                if not aabb_overlap(ma, mb):
                    continue
                v = intersection_volume(ma, mb)
                key = tuple(sorted((a, b)))
                if v < 0:
                    unresolved.append((float(t), key))
                elif v > 1e-6:
                    penetrations.append(dict(t=round(float(t), 5), pair=list(key), vol_mm3=round(v, 4)))
                    ks = "/".join(key)
                    if ks not in worst or v > worst[ks]["vol_mm3"]:
                        worst[ks] = dict(vol_mm3=round(v, 4), t=round(float(t), 5))
        if i % 400 == 0:
            print(f"  [{cand}] sweep {i}/{n} t={t:.3f} penetrations={len(penetrations)}")
    return dict(steps=n, penetrations=penetrations[:200], worst_by_pair=worst,
                unresolved=unresolved[:50], n_penetrations=len(penetrations))


def hull_of_points(pts: np.ndarray) -> trimesh.Trimesh:
    from scipy.spatial import ConvexHull
    h = ConvexHull(pts)
    m = trimesh.Trimesh(vertices=pts, faces=h.simplices, process=False)
    trimesh.repair.fix_normals(m)
    return m


def sweep_hull_checks(cand: str, parts, n_sample=61):
    """保守连续覆盖: 关键相位内运动件顶点集凸包 vs 静态件。
    凸包不相交 => 该相位内该对连续无碰撞(保守证明); 相交而采样无穿透 => 标记需细化。"""
    results = []
    if cand in ("F09_L82", "F07"):
        phases = []
        for i in range(6):
            phases.append((f"arm_fold_{i}", 0.20 * i / 6, 0.20 * (i + 1) / 6, ["ARM"]))
        # root fold split into sub-phases: smaller swept hulls = less conservatism
        for i in range(12):
            ta = 0.45 + 0.50 * i / 12
            tb = 0.45 + 0.50 * (i + 1) / 12
            movers = ["COL_0", "COL_1", "XBAR", "BRG", "ARM"] if cand == "F09_L82" else ["COL_0", "ARM"]
            phases.append((f"root_fold_{i}", ta, tb, movers))
        statics = ["BASE", "BED"] + [f"TWR_{i}" for i in range(len(K.TOWER_Y[cand]))] \
                  + [f"CAR_{i}" for i in range(len(K.TOWER_Y[cand]))]
        if cand == "F09_L82":
            statics.append("SYNC")
    elif cand == "SCZ":
        phases = []
        for i in range(6):
            ta = 0.15 + 0.85 * i / 6
            tb = 0.15 + 0.85 * (i + 1) / 6
            phases.append((f"scissor_{i}", ta, tb,
                           ["ARM_A_L", "ARM_A_R", "ARM_B_L", "ARM_B_R", "PLAT"]))
        statics = ["BASE", "BED", "POST_L", "POST_R"]
    else:
        return results
    for pname, ta, tb, movers in phases:
        # static meshes at phase-end pose (statics don't move within phase)
        pl_end = placements(cand, tb)
        smeshes = {}
        for s in statics:
            if s not in pl_end:
                continue
            pos, R = pl_end[s]
            smeshes[s] = placed_mesh(parts[base_name(s)], pos, R)
        for mv in movers:
            pts = []
            for t in np.linspace(ta, tb, n_sample):
                pl = placements(cand, float(t))
                if mv not in pl:
                    continue
                pos, R = pl[mv]
                m = placed_mesh(parts[base_name(mv)], pos, R)
                pts.append(m.vertices)
            if not pts:
                continue
            hull = hull_of_points(np.concatenate(pts))
            for s, sm in smeshes.items():
                if allowed(cand, mv, s):
                    continue
                v = intersection_volume(hull, sm)
                status = "CLEAR_CONSERVATIVE" if v == 0 else ("UNRESOLVED_NEEDS_REFINEMENT" if v > 0 else "ERROR")
                rec = dict(phase=pname, moving=mv, static=s,
                           hull_volume_mm3=round(float(hull.volume), 1),
                           hull_intersects=bool(v > 1e-6),
                           intersection_mm3=round(v, 4) if v >= 0 else None,
                           status=status)
                if status == "UNRESOLVED_NEEDS_REFINEMENT":
                    # targeted fine sampling of the flagged pair within the sub-phase
                    worst = 0.0
                    for t in np.linspace(ta, tb, 2001):
                        pl = placements(cand, float(t))
                        if mv not in pl or s not in pl:
                            continue
                        pm, pr = pl[mv]
                        sm2, sr = pl[s]
                        ma = placed_mesh(parts[base_name(mv)], pm, pr)
                        mb = placed_mesh(parts[base_name(s)], sm2, sr)
                        if not aabb_overlap(ma, mb):
                            continue
                        vv = intersection_volume(ma, mb)
                        if vv > worst:
                            worst = vv
                    rec["fine_sample_pen_mm3"] = round(worst, 5)
                    rec["status"] = "CLEAR_BY_REFINEMENT" if worst <= 1e-6 else "PENETRATION_FOUND"
                results.append(rec)
    return results


def joint_limits(cand: str):
    rows = []
    for t in np.linspace(0, 1, 101):
        pv = K.phase_values(cand, float(t))
        rows.append(pv)
    if cand == "SCZ":
        Hs = [r["H"] for r in rows]
        ok = all(K.SCZ["h_fold"] - 1e-6 <= h <= K.SCZ["h_max"] + 1e-6 for h in Hs)
        gain_fold = K.scz_span(K.SCZ["h_fold"]) / K.SCZ["h_fold"]
        gain_max = K.scz_span(K.SCZ["h_max"]) / K.SCZ["h_max"]
        return dict(range_ok=bool(ok), H_min=min(Hs), H_max=max(Hs),
                    dH_dS_fold=round(-gain_fold, 3), dH_dS_max=round(-gain_max, 3),
                    note="低位 |dH/dS| 大 => 水平输入大/垂直输出小, 推力放大; 非自锁证明")
    arms = [r["arm"] for r in rows]
    lifts = [r["lift"] for r in rows]
    roots = [r["root"] for r in rows]
    lift_max = K.LIFT.get(cand, 12.5)
    ok = (all(0 <= a <= 90 + 1e-6 for a in arms)
          and all(-1e-6 <= l <= lift_max + 1e-6 for l in lifts)
          and all(abs(r) <= 90 + 1e-6 for r in roots))
    # phase order: arm done before lift starts; lift done before root starts
    order_ok = True
    for r in rows:
        if r["lift"] > 1e-6 and r["arm"] < 90 - 1e-6:
            order_ok = False
        if abs(r["root"]) > 1e-6 and r["lift"] < lift_max - 1e-6:
            order_ok = False
    return dict(range_ok=bool(ok), phase_order_ok=bool(order_ok),
                arm_max=max(arms), lift_max=max(lifts), root_max=max(abs(r) for r in roots))


def l1_part_checks(cand: str):
    d = ROOT / CAND_DIRS[cand] / "STL"
    man = json.loads((ROOT / CAND_DIRS[cand] / "VALIDATION" / "parts_manifest.json").read_text(encoding="utf-8"))
    mrec = {r["part_id"].split("-", 1)[1]: r for r in man["parts"]}
    rows = []
    for f in sorted(d.glob("*.stl")):
        pid = f.stem.split("-", 1)[1]
        m = trimesh.load(f, force="mesh")
        rec = mrec.get(pid, {})
        vol_brep = rec.get("volume_cm3", 0) * 1000
        n_bodies = len(m.split(only_watertight=False))
        rows.append(dict(
            part_id=f.stem, watertight=bool(m.is_watertight),
            winding_consistent=bool(m.is_winding_consistent),
            n_bodies=n_bodies,
            volume_mm3=round(float(m.volume), 1),
            brep_volume_mm3=round(vol_brep, 1),
            vol_dev_pct=round(100 * abs(m.volume - vol_brep) / max(vol_brep, 1e-9), 2) if vol_brep else None,
            bbox_mm=[round(float(x), 2) for x in m.extents],
            n_faces=len(m.faces),
        ))
    return rows


def l3_manufacturability(cand: str):
    man = json.loads((ROOT / CAND_DIRS[cand] / "VALIDATION" / "parts_manifest.json").read_text(encoding="utf-8"))
    rows = []
    for r in man["parts"]:
        bb = r["bbox_mm"]
        fits = all(b <= 250 for b in bb)
        rows.append(dict(part_id=r["part_id"], material=r["material"], bbox_mm=bb,
                         plate_250_ok=fits, mass_est_g=r["mass_est_g"],
                         volume_cm3=r["volume_cm3"]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cands", nargs="*", default=list(CAND_DIRS))
    ap.add_argument("--steps", type=int, default=2001)
    ap.add_argument("--skip-sweep", action="store_true")
    args = ap.parse_args()
    for cand in args.cands:
        out = ROOT / CAND_DIRS[cand] / "VALIDATION"
        out.mkdir(parents=True, exist_ok=True)
        print(f"== {cand} L1 ==")
        l1 = l1_part_checks(cand)
        (out / "L1_parts.json").write_text(json.dumps(l1, ensure_ascii=False, indent=2), encoding="utf-8")
        bad = [r for r in l1 if not r["watertight"] or (r["vol_dev_pct"] or 0) > 3 or r.get("n_bodies", 1) != 1]
        print(f"  parts={len(l1)} issues={len(bad)}")
        print(f"== {cand} L2 limits ==")
        lim = joint_limits(cand)
        (out / "L2_joint_limits.json").write_text(json.dumps(lim, ensure_ascii=False, indent=2), encoding="utf-8")
        if not args.skip_sweep:
            print(f"== {cand} L2 sweep ({args.steps}) ==")
            parts = load_parts(cand)
            sw = sweep_check(cand, parts, n=args.steps)
            (out / "L2_sweep.json").write_text(json.dumps(sw, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  penetrations={sw['n_penetrations']} unresolved={len(sw['unresolved'])}")
            print(f"== {cand} L2 hull checks ==")
            try:
                sw["hull_checks"] = sweep_hull_checks(cand, parts)
            except Exception as e:
                sw["hull_checks"] = []
                sw["hull_error"] = str(e)
                print(f"  hull check error: {e}")
            (out / "L2_sweep.json").write_text(json.dumps(sw, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  hull_flags={sum(1 for h in sw['hull_checks'] if h['status'] != 'CLEAR_CONSERVATIVE')}")
        print(f"== {cand} L3 ==")
        l3 = l3_manufacturability(cand)
        (out / "L3_manufacturability.json").write_text(json.dumps(l3, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"== {cand} L2b assembly closure ==")
        import joints_r1 as JJ
        clo = JJ.closure_check(cand, n=args.steps)
        pins = JJ.pin_interface_audit(cand)
        try:
            holes = JJ.cad_hole_audit(cand)
        except Exception as e:
            holes = dict(error=str(e), passed=False)
        l2b = dict(closure=clo, pin_interfaces=pins, cad_hole_audit=holes)
        (out / "L2b_closure.json").write_text(json.dumps(l2b, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  joints={clo['n_joints']} closure_fails={len(clo['fails'])} "
              f"hole_missing={len(holes.get('missing', []))} pin_ok={all(p['ok'] for p in pins)}")
    print("DONE")


if __name__ == "__main__":
    main()
