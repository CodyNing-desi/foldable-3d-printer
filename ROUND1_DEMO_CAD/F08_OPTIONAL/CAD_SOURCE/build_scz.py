"""SCZ scissor Z-axis demo (1:2). Mirrored classic scissor: fixed right pivot,
left slider input, platform pinned top-right -> 1 DOF, platform stays horizontal.
Local frames match kinematics_r1.scz_placements."""
from __future__ import annotations

from build123d import Box, Cylinder, Part, Pos, Rot, Location

from common_r1 import pin, clip, x_hole, y_hole, z_hole, CLR_ROT, CLR_SLD
import kinematics_r1 as K

L = K.SCZ["L"]          # 77 half-length
FIX = K.SCZ["fix_x"]    # 155
LOW = K.SCZ["low_z"]    # 12
YA, YB = K.SCZ["yA"], K.SCZ["yB"]


def build_arm() -> Part:
    """Local origin = bottom hole. Holes at 0 / 77 / 154 (2L span)."""
    p = Pos(77, 0, 0) * Box(160, 3, 10)
    for x in (0.0, 77.0, 154.0):
        p = p - Pos(x, 0, 0) * y_hole(4.0, 5, CLR_ROT)
    p.label = "SCZ-ARM"
    return p


def build_post() -> Part:
    """Local origin (155, +-71, 0). V5: clevis post (ears flank arm B, base plate
    ties ears below arm swing); arm B bottom pivot at world z18."""
    p = Pos(0, 0, 11.5) * Box(10, 12, 3)                   # base plate z10..13
    for sy in (-1, 1):
        p = p + Pos(0, sy * 3.7, 18) * Box(10, 4, 12)      # ears z12..24 (overlap plate)
    p = p - Pos(0, 0, 18) * y_hole(4.0, 14, CLR_ROT)       # arm B fixed pin
    for dx in (-3.0, 3.0):
        for dy in (-3.6, 3.6):
            p = p - Pos(dx, dy, 11.5) * z_hole(3.0, 5, CLR_SLD)
    p.label = "SCZ-POST"
    return p


def build_slider_bottom() -> Part:
    """Local origin = arm A bottom hole (sx, +-62.5, 16).
    V3: clevis ears flank arm A; base plate strips; hanger (=tongue) reaches down
    to cross-shaft at world z4 inside the base shaft window."""
    p = Pos(0, 0, -4) * Box(14, 12, 4)                     # base plate world z10..14
    p = p - Pos(0, 0, -4) * Box(14.02, 3.4, 4.02)          # arm clearance slot
    for sy in (-1, 1):
        p = p + Pos(0, sy * 3.7, 0) * Box(12, 4, 12)       # ears world z10..22
    p = p - Pos(0, 0, 0) * y_hole(4.0, 14, CLR_ROT)        # arm A pin
    p = p + Pos(0, 0, -11) * Box(6, 6, 10)                 # hanger/tongue world z0..10
    p = p - Pos(0, 0, -12) * y_hole(4.0, 8, 0.0)           # shaft press-fit world z4
    p = p - Pos(0, 0, -9) * z_hole(2.5, 14, CLR_SLD)       # shaft cross pin (from below)
    p = p - Pos(4, 3.7, -2) * z_hole(3.0, 22, CLR_SLD)     # lock pin through ear+base
    p = p - Pos(4, -3.7, -2) * z_hole(3.0, 22, CLR_SLD)    # (either ear)
    p.label = "SCZ-SLB"
    return p


def build_slider_top() -> Part:
    """Local origin = arm B top hole (sx, +-71, hz).
    V3: clevis ears flank arm B; slotted top plate + tongue carry cross-shaft
    at local z8 (world hz+8, inside platform channel)."""
    p = Pos(0, 0, 4) * Box(14, 12, 4)                      # top plate local z2..6
    p = p - Pos(0, 0, 4) * Box(14.02, 3.4, 4.02)           # arm clearance slot
    for sy in (-1, 1):
        p = p + Pos(0, sy * 3.7, -2) * Box(12, 4, 8)       # ears local z-6..2
    p = p - Pos(0, 0, 0) * y_hole(4.0, 14, CLR_ROT)        # arm B top pin
    p = p + Pos(0, 0, 9) * Box(8, 6, 6)                    # tongue local z6..12
    p = p - Pos(0, 0, 9) * y_hole(4.0, 8, 0.0)             # shaft press-fit local z9
    p = p - Pos(0, 0, 9) * z_hole(2.5, 10, CLR_SLD)        # shaft cross pin
    p.label = "SCZ-SLT"
    return p


def build_scz_base() -> Part:
    """SCZ-dedicated base: tongue slots + transverse shaft window + corner feet.
    Window x0..85, z0..6 lets the bottom cross-shaft (z4) and knob pass; feet raise
    the base 6mm so the knob clears the table."""
    p = Pos(157.5 / 2, 0, 5) * Box(157.5, 173.5, 10)
    for x0 in (35.0, 121.0):
        p = p + Pos(x0 + 2, 0, 16.75) * Box(4, 90, 14.5)
    # tongue guide slots (top plate z6..10)
    for ys in (-62.5, 62.5):
        p = p - Pos(45, ys, 8) * Box(90.02, 6.4, 4.02)
    # transverse shaft window (through z0..6)
    p = p - Pos(42.5, 0, 3) * Box(85.02, 173.52, 6.02)
    # corner feet (all outside shaft window x0..85; overlapped into plate)
    for x in (93.5, 149.5):
        for y in (-79.0, 79.0):
            p = p + Pos(x, y, -2.5) * Box(15, 15, 7)
    # fixed-post mount holes
    for ys in (-71.0, 71.0):
        for dx in (-3.0, 3.0):
            for dy in (-3.6, 3.6):
                x, y = 155 + dx, ys + dy
                p = p - Pos(x, y, 5) * z_hole(3.0, 12, CLR_SLD)
                p = p - Pos(x, y, 1.5) * Box(9, 9, 3.02)
    # slider lock holes (through ear at y+-66.2)
    import kinematics_r1 as _K
    for H in (_K.SCZ["h_fold"], _K.SCZ["h_max"]):
        xs = _K.SCZ["fix_x"] - _K.scz_span(H) + 4.0
        for ys in (-66.2, -58.8, 58.8, 66.2):
            p = p - Pos(xs, ys, 5) * z_hole(3.0, 12, CLR_SLD)
            p = p - Pos(xs, ys, 1.5) * Box(9, 9, 3.02)
    p.label = "SCZ-BASE"
    return p


def build_shaft_bottom() -> Part:
    """Along Y, local origin at center. Knob at middle, clips outboard posts."""
    p = Rot(-90, 0, 0) * Cylinder(2, 164)
    p = p + Cylinder(7, 8)
    for a in (0, 120, 240):
        p = p + Rot(0, 0, a) * Pos(0, 6, 0) * Cylinder(1.2, 8)
    for sy in (-1, 1):
        g = Pos(0, sy * 79.6, 0) * Rot(-90, 0, 0) * (
            Cylinder(2.01, 1.2) - Cylinder(1.7, 1.22))
        p = p - g
    p.label = "SCZ-SHB"
    return p


def build_shaft_top() -> Part:
    p = Rot(-90, 0, 0) * Cylinder(2, 164)
    for sy in (-1, 1):
        g = Pos(0, sy * 79.6, 0) * Rot(-90, 0, 0) * (
            Cylinder(2.01, 1.2) - Cylinder(1.7, 1.22))
        p = p - g
    p.label = "SCZ-SHT"
    return p


def build_platform() -> Part:
    """Local origin = arm A top pin (155, 0, hz). Plate + channels + clevises + TH marker."""
    p = Pos(-77.5, 0, 9) * Box(165, 152, 6)
    for sy in (-1, 1):
        p = p - Pos(-113, sy * 71, 9) * Box(90.02, 6.4, 6.02)   # slider channels (through)
        p = p - Pos(-113, sy * 75.6, 9) * Box(90.02, 4.6, 6.02)  # shaft edge notch
        # arm A top clevis
        for sy2 in (-1, 1):
            p = p + Pos(0, sy * 62.5 + sy2 * 3.7, 0) * Box(10, 4, 12)
        p = p - Pos(0, sy * 62.5, 0) * y_hole(4.0, 12, CLR_ROT)
    # toolhead park marker (world x ~ 19)
    p = p + Pos(-136, 0, -3.75) * Box(25, 26, 19.5)
    p.label = "SCZ-PLAT"
    return p


def scz_plat_extra(H: float):
    """Center-pin placements (arm A <-> arm B crossing), world."""
    Sp = K.scz_span(H)
    cx, cz = FIX - Sp / 2, LOW + H / 2
    out = []
    for sy in (-1, 1):
        out.append((f"CPIN_{ 'L' if sy < 0 else 'R'}",
                    Location(Pos(cx, sy * YA - 3, cz) * Rot(-90, 0, 0))))
    return out


def scz_pins() -> list[tuple[str, Part, str, int]]:
    return [
        ("PIN4-L18", pin(4, 18), "PETG", 4),   # arm A bottom(2) + arm A top(2)
        ("PIN4-L16", pin(4, 16), "PETG", 6),   # arm B bottom(2) + top(2) + center(2)
        ("CLIP4", clip(4), "PETG", 14),        # 10 pins + 4 shaft ends
        ("PIN3-L24", pin(3, 24), "PETG", 2),   # fold / max lock (clip in base pocket)
        ("PIN3-L13", pin(3, 13), "PETG", 4),   # post mount (clip in base pocket)
        ("PIN25-L10", pin(2.5, 10), "PETG", 4),  # shaft cross pins (custom small)
        ("CLIP3", clip(3), "PETG", 6),
    ]
