"""F07 folded concept assembly.

Process: conceptual assembly; load-bearing joints require machined metal after measurement.
Material: aluminium extrusion and unspecified metal joint hardware.
Interfaces: every pivot, slot, lock and accessory dimension is an unchecked concept assumption.
先竖直抬升枢轴再翻折；抬升只发生在折叠过程，不增加工作高度。
"""
from build123d import *

POLYGONS_MM = [('base', 347.0, [(315.0, 0.0), (315.0, 20.0), (0.0, 20.0), (0.0, 0.0)]), ('bed', 180.0, [(250.0, 40.0), (250.0, 60.0), (70.0, 60.0), (70.0, 40.0)]), ('column', 40.0, [(39.99953, 90.00005), (384.99953, 90.00005), (384.99953, 110.00005), (39.99953, 110.00005)])]
EXPECTED_BOUNDS_MM = (0.0, 0.0, 384.99953091572456, 110.00004520634599)


def interfaces() -> list[dict]:
    return []


def checks() -> list[dict]:
    min_x, min_z, max_x, max_z = EXPECTED_BOUNDS_MM
    return [
        {"feature": "expected folded X extent", "bbox_x": {"min": min_x - 0.1, "max": max_x + 0.1}},
        {"feature": "expected folded Z extent", "bbox_z": {"min": min_z - 0.1, "max": max_z + 0.1}},
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
