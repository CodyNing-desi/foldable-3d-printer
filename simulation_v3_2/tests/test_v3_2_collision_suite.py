"""V3.2 Regression Counterexample Suite (A-E) for Continuous Swept OBB Collision."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from foldsim_v3_2.geometry3d import (
    OBB,
    obb_sat_distance,
    rot_axis_angle,
    rot_z,
    swept_obb_vs_obb,
    verify_interval_collision,
)


def test_counterexample_a_120deg_rotation_miss() -> None:
    """A: 100 mm slender OBB rotates 120 deg around pivot (0,0,0), hitting obstacle at ~90 deg."""
    arm_base = OBB.from_bounds("arm", 0.0, -3.0, -3.0, 100.0, 3.0, 3.0)
    obs = OBB.from_bounds("obs_90", -4.0, 70.0, -4.0, 4.0, 95.0, 4.0)

    def pose_arm(t: float) -> OBB:
        return arm_base.transformed(rotation=rot_z(120.0 * t))

    res = verify_interval_collision(pose_arm, lambda t: obs)
    assert res["status"] == "FAIL", f"Expected FAIL for 120-deg sweep hitting 90-deg obstacle, got {res}"
    assert res["colliding"] is True
    assert 0.5 < res["t_collision"] < 0.95

    res_ep = swept_obb_vs_obb(pose_arm(0.0), pose_arm(1.0), obs, obs)
    assert res_ep["status"] == "FAIL", f"Expected FAIL from swept_obb_vs_obb for 120-deg sweep, got {res_ep}"


def test_counterexample_b_180deg_and_wrap() -> None:
    """B: 180 deg rotation requires explicit trajectory; +180 vs -180 direction & wraparound."""
    arm_base = OBB.from_bounds("arm", 10.0, -3.0, -3.0, 100.0, 3.0, 3.0)
    obs_plus90 = OBB.from_bounds("obs_plus90", -4.0, 50.0, -4.0, 4.0, 70.0, 4.0)

    res_plus = verify_interval_collision(
        lambda t: arm_base.transformed(rotation=rot_z(180.0 * t)),
        lambda t: obs_plus90,
    )
    assert res_plus["status"] == "FAIL", f"Expected FAIL for +180 deg sweep, got {res_plus}"

    res_minus = verify_interval_collision(
        lambda t: arm_base.transformed(rotation=rot_z(-180.0 * t)),
        lambda t: obs_plus90,
    )
    assert res_minus["status"] == "PASS", f"Expected PASS for -180 deg sweep, got {res_minus}"

    obs_180 = OBB.from_bounds("obs_180", -80.0, -4.0, -4.0, -50.0, 4.0, 4.0)
    res_wrap = verify_interval_collision(
        lambda t: arm_base.transformed(rotation=rot_z(179.0 + 2.0 * t)),
        lambda t: obs_180,
    )
    assert res_wrap["status"] == "FAIL", f"Expected FAIL for +179->+181 wrap, got {res_wrap}"

    res_unres = swept_obb_vs_obb(arm_base, arm_base.transformed(rotation=rot_z(180.0)), obs_plus90, obs_plus90)
    assert res_unres["status"] == "UNRESOLVED", f"Expected UNRESOLVED for 180-deg endpoint-only, got {res_unres}"


def test_counterexample_c_two_moving_obbs_crossing() -> None:
    """C: Two moving OBBs whose endpoints are all clear, but they cross at t=0.5."""
    box_a = OBB.from_bounds("a", -5.0, -5.0, -5.0, 5.0, 5.0, 5.0)
    box_b = OBB.from_bounds("b", -5.0, -5.0, -5.0, 5.0, 5.0, 5.0)

    def pose_a(t: float) -> OBB:
        return box_a.transformed(translation=np.array([-60.0 + 120.0 * t, 0.0, 0.0]))

    def pose_b(t: float) -> OBB:
        return box_b.transformed(translation=np.array([0.0, -60.0 + 120.0 * t, 0.0]))

    assert not obb_sat_distance(pose_a(0.0), pose_b(0.0))[0]
    assert not obb_sat_distance(pose_a(1.0), pose_b(1.0))[0]

    res = verify_interval_collision(pose_a, pose_b)
    assert res["status"] == "FAIL", f"Expected FAIL for crossing moving OBBs, got {res}"
    assert abs(res["t_collision"] - 0.5) < 0.1


def test_counterexample_d_clear_paths_pass() -> None:
    """D: Known clear paths (translation, 120-deg rotation, moving-vs-moving) must return PASS."""
    arm = OBB.from_bounds("arm", 10.0, -3.0, -3.0, 100.0, 3.0, 3.0)
    obs_far = OBB.from_bounds("obs", -4.0, -90.0, -4.0, 4.0, -50.0, 4.0)

    res_rot = verify_interval_collision(
        lambda t: arm.transformed(rotation=rot_z(120.0 * t)),
        lambda t: obs_far,
    )
    assert res_rot["status"] == "PASS", f"Expected PASS for clear 120-deg rotation, got {res_rot}"
    assert res_rot["clearance_mm"] > 1.0

    box_a = OBB.from_bounds("a", -5.0, -5.0, -5.0, 5.0, 5.0, 5.0)
    box_b = OBB.from_bounds("b", -5.0, -5.0, 15.0, 5.0, 5.0, 25.0)
    res_mv = verify_interval_collision(
        lambda t: box_a.transformed(translation=np.array([-50.0 + 100.0 * t, 0.0, 0.0])),
        lambda t: box_b.transformed(translation=np.array([0.0, -50.0 + 100.0 * t, 0.0])),
    )
    assert res_mv["status"] == "PASS", f"Expected PASS for Z-offset moving OBBs, got {res_mv}"
    assert res_mv["clearance_mm"] > 0.0


def test_counterexample_e_boundary_and_precision() -> None:
    """E: 0.01/0.1/1.0 mm gaps, flush contact, thin wall, degenerate SAT axes, combined rot+trans."""
    base = OBB.from_bounds("base", 0.0, 0.0, 0.0, 20.0, 20.0, 20.0)

    for gap in (0.01, 0.1, 1.0):
        other = OBB.from_bounds("other", 20.0 + gap, 0.0, 0.0, 40.0 + gap, 20.0, 20.0)
        res = verify_interval_collision(
            lambda t, b=base: b.transformed(translation=np.array([0.0, 10.0 * t, 0.0])),
            lambda t, o=other: o,
        )
        assert res["status"] == "PASS", f"Expected PASS for gap={gap} mm, got {res}"
        assert res["clearance_mm"] > 0.0

    flush = OBB.from_bounds("flush", 20.0, 0.0, 0.0, 40.0, 20.0, 20.0)
    res_flush = verify_interval_collision(lambda t: base, lambda t: flush, max_depth=8)
    assert res_flush["status"] != "PASS", f"Flush contact must not return PASS, got {res_flush}"

    wall = OBB.from_bounds("wall", 49.75, -20.0, -20.0, 50.25, 20.0, 20.0)
    pin = OBB.from_bounds("pin", -2.0, -2.0, -2.0, 2.0, 2.0, 2.0)
    res_wall = verify_interval_collision(
        lambda t: pin.transformed(translation=np.array([100.0 * t, 0.0, 0.0])),
        lambda t: wall,
    )
    assert res_wall["status"] == "FAIL", f"Expected FAIL crossing 0.5 mm thin wall, got {res_wall}"

    a_rot = base.transformed(rotation=rot_axis_angle(np.array([0.0, 0.0, 1.0]), 45.0))
    b_rot = OBB.from_bounds("b_rot", 35.0, 0.0, 0.0, 55.0, 20.0, 20.0).transformed(
        rotation=rot_axis_angle(np.array([0.0, 0.0, 1.0]), 45.0)
    )
    col, _, clr = obb_sat_distance(a_rot, b_rot)
    assert not col and clr > 5.0

    obs_mid = OBB.from_bounds("obs_mid", 25.0, 35.0, -5.0, 35.0, 45.0, 5.0)
    rod = OBB.from_bounds("rod", 0.0, -2.0, -2.0, 50.0, 2.0, 2.0)
    res_comb = verify_interval_collision(
        lambda t: rod.transformed(rotation=rot_z(90.0 * t), translation=np.array([30.0 * t, 0.0, 0.0])),
        lambda t: obs_mid,
    )
    assert res_comb["status"] == "FAIL", f"Expected FAIL for combined rot+trans, got {res_comb}"


def run_all() -> None:
    tests = [
        ("A_120deg_rotation_miss", test_counterexample_a_120deg_rotation_miss),
        ("B_180deg_and_wrap", test_counterexample_b_180deg_and_wrap),
        ("C_two_moving_obbs_crossing", test_counterexample_c_two_moving_obbs_crossing),
        ("D_clear_paths_pass", test_counterexample_d_clear_paths_pass),
        ("E_boundary_and_precision", test_counterexample_e_boundary_and_precision),
    ]
    for name, fn in tests:
        fn()
        print(f"[PASS] {name}")
    print("ALL 5 REGRESSION COUNTEREXAMPLES PASSED.")


if __name__ == "__main__":
    run_all()
