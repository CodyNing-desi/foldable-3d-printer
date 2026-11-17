"""F09_L82 / F07 shared gantry parts (demo 1:2). Local frames match kinematics_r1."""
from __future__ import annotations

import math
from pathlib import Path

from build123d import Box, Cylinder, Part, Pos, Rot, Compound, Location, export_stl

from common_r1 import (
    pin, clip, x_hole, y_hole, z_hole, export_part, export_assembly,
    save_manifest, CLR_ROT, CLR_SLD, CAD_VERSION,
)
import kinematics_r1 as K


def build_base() -> Part:
    p = Pos(157.5 / 2, 0, 5) * Box(157.5, 173.5, 10)
    # bed support walls (bed top z28: 2mm below nominal for folded-arm clearance)
    for x0 in (35.0, 121.0):
        p = p + Pos(x0 + 2, 0, 16.75) * Box(4, 90, 14.5)
    # tower mount holes + underside clip pockets (positions for y=0, +-65)
    for yc in (0.0, -65.0, 65.0):
        for dx in (-6.0, 6.0):
            for dy in (-14.0, 14.0):
                x, y = 10 + dx, yc + dy
                p = p - Pos(x, y, 5) * z_hole(3.0, 12, CLR_SLD)
                p = p - Pos(x, y, 1.5) * Box(10, 10, 3.02)
    # root-hinge tongue swing pockets (pivot z13, tongue R6 dips below base top)
    for yc in (0.0, -65.0, 65.0):
        p = p - Pos(22, yc, 8.25) * Box(20, 22, 3.52)
    p.label = "BASE"
    return p


def build_bed() -> Part:
    p = Pos(80, 0, 26) * Box(90, 90, 4)
    p.label = "BED"
    return p


def build_tower() -> Part:
    """Local origin (10, yc, 10). Foot + 2 guide posts (NO cap since V6.1).
    V2: foot notched for root tongue swing.
    V6.1: top cap split into separate CAP part (build_cap) so the carriage and
    SYNC can actually be threaded onto the posts; cap pinned at z65."""
    p = Pos(2, 0, 2) * Box(20, 36, 4)
    p = p - Pos(7, 0, 2) * Box(10.02, 22, 4.02)  # tongue swing notch (world x12..22)
    for dy in (-15.0, 15.0):
        p = p + Pos(0, dy, (4 + 67) / 2) * Cylinder(2.5, 63)
        p = p - Pos(0, dy, 48) * x_hole(3.0, 8, CLR_SLD)  # carriage lock cross-hole
        p = p - Pos(0, dy, 65) * x_hole(3.0, 8, CLR_SLD)  # V6.1 cap pin cross-hole
    for dx in (-6.0, 6.0):
        for dy in (-14.0, 14.0):
            p = p - Pos(dx, dy, 2) * z_hole(3.0, 6, CLR_SLD)
    p.label = "TWR"
    return p


def build_cap() -> Part:
    """V6.1 removable top cap, separate printable part. Same local frame as tower.
    Slips over post tops (post z4..67, cap z63..67) and pins through cap+post
    cross holes at z65 with 2x PIN3-L14. Keeps V2 clearance: world z73..77, x4..12."""
    p = Pos(-2, 0, 65) * Box(8, 36, 4)
    for dy in (-15.0, 15.0):
        p = p - Pos(0, dy, 65) * z_hole(5.0, 8, CLR_ROT)   # slip over post tops
        p = p - Pos(0, dy, 65) * x_hole(3.0, 10, CLR_SLD)  # cap pin
    p.label = "CAP"
    return p


def build_carriage() -> Part:
    """Local origin (6, yc, 10+lift). Body + bushings + root clevis + knob."""
    p = Pos(7.5, 0, 7) * Box(15, 38, 14)
    for dy in (-15.0, 15.0):
        p = p + Pos(4, dy, 7) * Cylinder(4.5, 14)
        p = p - Pos(4, dy, 7) * z_hole(5.0, 16, CLR_SLD)
        p = p - Pos(4, dy, 7) * x_hole(3.0, 12, CLR_SLD)  # post lock pin
    # tongue swing notch (20-thick tongue, full body height)
    p = p - Pos(11.25, 0, 7) * Box(8.5, 20.8, 14.02)
    # root clevis ears (gap 20.4 for 20-thick tongue / tube root)
    for sy in (-1, 1):
        ear = Pos(17, sy * 12.2, 7) * Box(18, 4, 14)
        p = p + ear
    p = p - Pos(14, 0, 3) * y_hole(5.0, 34, CLR_ROT)
    # root lock holes: 0 deg (14,.,11), 90 deg (22,.,3)
    p = p - Pos(14, 0, 11) * y_hole(3.0, 34, CLR_SLD)
    p = p - Pos(22, 0, 3) * y_hole(3.0, 34, CLR_SLD)
    # sync-bar bosses with horizontal pin holes (clip accessible outboard)
    for dx in (2.0, 5.0):
        for dy in (-10.0, 10.0):
            p = p + Pos(dx, dy, 17) * Cylinder(3.5, 6)
            p = p - Pos(dx, dy, 17) * x_hole(3.0, 10, CLR_SLD)
    # hand knob on rear face (overlapped into body for single-solid fusion)
    p = p + Pos(-3.5, 0, 7) * Rot(0, 90, 0) * Cylinder(5, 9)
    for a in (0, 120, 240):
        p = p + Pos(-3.5, 0, 7) * Rot(a, 0, 0) * Pos(0, 4.2, 0) * Rot(0, 90, 0) * Cylinder(1.2, 9)
    p.label = "CAR"
    return p


def build_column(with_arm_clevis: bool = True) -> Part:
    """Local origin = root pivot. Tongue + tube + frame holes.
    V6: F07 (single column) carries the arm clevis directly; F09 columns do NOT
    (the central X-arm hinges to the bridge beam's central clevis instead)."""
    # tongue (20 thick) with rounded root
    t = Rot(90, 0, 0) * Cylinder(6, 20)
    t = t + Pos(0, 0, 5.5) * Box(12, 20, 11)
    t = t - y_hole(5.0, 22, CLR_ROT)
    t = t - Pos(0, 0, 8) * y_hole(3.0, 22, CLR_SLD)
    p = t
    # tube (bottom at local z11 = carriage top face at full lift)
    tube = Pos(0, 0, (11 + 169.5) / 2) * Box(15, 20, 158.5)
    tube = tube - Pos(0, 0, (11 + 169.5) / 2) * Box(9, 14, 158.52)
    p = p + tube
    if with_arm_clevis:
        # arm tongue swing relief in tube front wall (quadrant x<7.5, z>137)
        p = p - Pos(4.5, 0, 143.25) * Box(6.02, 20.8, 12.5)
        # arm clevis (ears outboard of tube faces), pivot (16, 0, 137)
        for sy in (-1, 1):
            p = p + Pos(16, sy * 12.2, 136) * Box(24, 4, 15)
            p = p + Pos(6, sy * 12, 129.75) * Box(4, 4.4, 2.5)
        p = p - Pos(16, 0, 137) * y_hole(5.0, 32, CLR_ROT)
        for sy in (-1, 1):
            p = p - Pos(13, sy * 12.2, 140.5) * Box(6.02, 4.02, 6.02)
        p = p - Pos(24, 0, 137) * y_hole(3.0, 32, CLR_SLD)   # arm lock 0 deg
        p = p - Pos(16, 0, 129) * y_hole(3.0, 32, CLR_SLD)   # arm lock 90 deg
    # crossbar tenon pin holes (X) at z162
    p = p - Pos(0, 0, 162) * x_hole(3.0, 18, CLR_SLD)
    # bridge tenon notches + pin holes (Y, both walls) at z132 (V6 bridge height)
    for sy in (-1, 1):
        p = p - Pos(0, sy * 8.5, 132) * Box(8.8, 3.4, 15.2)
        p = p - Pos(0, sy * 8.5, 132) * y_hole(3.0, 6.5, CLR_SLD)
    p.label = "COL"
    return p


def build_arm() -> Part:
    """Local origin = arm pivot. Bar + root tongue (20 thick) + toolhead marker."""
    p = Pos(107.5 / 2, 0, 0) * Box(107.5, 16, 12)
    t = Pos(-6, 0, 0) * Box(12, 20, 12)
    t = t + Rot(90, 0, 0) * Cylinder(6, 20)
    p = p + t
    p = p - y_hole(5.0, 22, CLR_ROT)
    p = p - Pos(8, 0, 0) * y_hole(3.0, 22, CLR_SLD)  # lock hole: 0 & 90 deg
    # toolhead envelope marker
    p = p + Pos(55, 0, -19.75) * Box(25, 26, 27.5)
    p.label = "ARM"
    return p


def build_sync() -> Part:
    """Local origin (0,0,10+lift): beam on carriage tops, world x6..12.5, y+-58.
    Vertical clearance holes let tower posts (10, +-50) pass through."""
    p = Pos(9.25, 0, 18) * Box(6.5, 116, 8)
    for y in (-55.0, 55.0):
        p = p - Pos(9.25, y, 17) * x_hole(3.0, 8, CLR_SLD)
    for y in (-50.0, 50.0):
        p = p - Pos(10, y, 18) * z_hole(5.0, 10, CLR_SLD + 0.2)
    p.label = "SYNC"
    return p


def build_xbar() -> Part:
    """Local origin (20,0,13): top strap + tenons into column tops."""
    p = Pos(0, 0, 173.5) * Box(15, 166, 8)
    for sy in (-1, 1):
        p = p + Pos(0, sy * 65, 162) * Box(8.6, 13.6, 15)
        p = p - Pos(0, sy * 65, 162) * x_hole(3.0, 12, CLR_SLD)
    p.label = "XBAR"
    return p


def build_bridge() -> Part:
    """Local origin (20,0,13) = root frame. V6: mid beam carries the CENTRAL X-arm
    clevis at (16,0,137) so the y=0 arm physically hinges to the gantry.
    Body world z142.5..157.5; end tenons into column inner walls; full-height
    central notch clears the arm tongue/bar swing."""
    p = Pos(0, 0, 137) * Box(15, 110, 15)                  # body z129.5..144.5
    # central tongue/bar swing notch (full height, front-center)
    p = p - Pos(9, 0, 137) * Box(14.02, 20.8, 15.02)       # x2..16, y+-10.4
    # central arm clevis ears (pivot 16,0,137), tied to body at x4..7.5
    for sy in (-1, 1):
        p = p + Pos(16, sy * 12.2, 137) * Box(24, 4, 15)   # x4..28
    p = p - Pos(16, 0, 137) * y_hole(5.0, 32, CLR_ROT)     # arm pivot
    for sy in (-1, 1):
        p = p - Pos(13, sy * 12.2, 140.5) * Box(6.02, 4.02, 6.02)  # tongue relief
    p = p - Pos(24, 0, 137) * y_hole(3.0, 32, CLR_SLD)     # arm lock 0 deg
    p = p - Pos(16, 0, 129) * y_hole(3.0, 32, CLR_SLD)     # arm lock 90 deg
    # end tenons into column inner walls + pin holes at z132
    for sy in (-1, 1):
        p = p + Pos(0, sy * 61.5, 137) * Box(8.6, 13, 15)
        p = p - Pos(0, sy * 61.5, 132) * y_hole(3.0, 16, CLR_SLD)
    p.label = "BRG"
    return p


# ---------------- pin schedule ----------------
def gantry_pins(cand: str) -> list[tuple[str, Part, str, int]]:
    n_t = 2 if cand == "F09_L82" else 1
    items = [
        ("PIN5-L34", pin(5, 34), "PETG", n_t + 1),      # root hinge + arm hinge
        ("PIN3-L34", pin(3, 34), "PETG", n_t + 1),      # root + arm lock (moved between poses)
        ("PIN3-L26", pin(3, 26), "PETG", 2 * n_t),      # carriage-post top lock
        ("PIN3-L14", pin(3, 14), "PETG", 6 * n_t),      # tower mount(4/t) + cap pin(2/t)
        ("CLIP5", clip(5), "PETG", n_t + 1),
        ("CLIP3", clip(3), "PETG", n_t + 1 + 2 * n_t + 6 * n_t + (8 if cand == "F09_L82" else 0)),
    ]
    if cand == "F09_L82":
        items += [
            ("PIN3-L18", pin(3, 18), "PETG", 4 + 2),    # sync(4, X) + bridge(2, Y)
            ("PIN3-L22", pin(3, 22), "PETG", 2),        # xbar
        ]
    return items


def build_gantry_parts(cand: str) -> dict[str, Part]:
    parts = {"BASE": build_base(), "BED": build_bed(), "TWR": build_tower(),
             "CAP": build_cap(), "CAR": build_carriage(),
             "COL": build_column(with_arm_clevis=(cand == "F07")), "ARM": build_arm()}
    if cand == "F09_L82":
        parts.update(SYNC=build_sync(), XBAR=build_xbar(), BRG=build_bridge())
    return parts


def gantry_assembly(cand: str, parts: dict[str, Part], arm: float, lift: float, root: float):
    pl = K.gantry_placements(cand, arm, lift, root)
    out = []
    for pid, val in pl.items():
        if pid == "ARM":
            continue
        pos, rot = val
        base_id = pid.split("_")[0]
        out.append((pid, parts[base_id], Location(Pos(*pos) * Rot(0, rot, 0))))
    apos, arot = K.arm_placement(cand, arm, lift, root)
    out.append(("ARM", parts["ARM"], Location(Pos(*apos) * Rot(0, arot, 0))))
    return out
