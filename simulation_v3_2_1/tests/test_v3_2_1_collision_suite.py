"""V3.2.1 Regression Counterexample Suite (A-H) for Certified Continuous Swept OBB Collision."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from foldsim_v3_2_1.geometry3d import (
    LipschitzTrajectory,
    OBB,
    StaticTrajectory,
    obb_sat_distance,
    rot_axis_angle,
    rot_z,
    swept_obb_vs_obb,
    verify_interval_collision,
)


def _rot_traj(obb: OBB, deg_total: float, origin: np.ndarray | None = None, name_suffix: str = "") -> LipschitzTrajectory:
    orig = np.zeros(3) if origin is None else origin
    d_pivot = float(np.linalg.norm(obb.center - orig))
    omega = abs(math.radians(deg_total))
    return LipschitzTrajectory(
        pose_fn=lambda t: obb.transformed(rotation=rot_z(deg_total * t), origin=orig),
        v_center_max=d_pivot * omega,
        omega_max_rad=omega,
        r_obb=obb.bounding_radius,
        label=f"Rot({deg_total}deg){name_suffix}",
    )


def test_a_120deg_rotation_miss() -> dict:
    """A: 100 mm slender OBB rotates 120 deg around pivot (0,0,0), hitting obstacle at ~90 deg."""
    arm_base = OBB.from_bounds("arm", 0.0, -3.0, -3.0, 100.0, 3.0, 3.0)
    obs = OBB.from_bounds("obs_90", -4.0, 70.0, -4.0, 4.0, 95.0, 4.0)
    res = verify_interval_collision(_rot_traj(arm_base, 120.0), StaticTrajectory(obs))
    assert res["status"] == "FAIL", f"Expected FAIL for A, got {res}"
    assert res["colliding"] is True
    assert 0.5 < res["t_collision"] < 0.95
    res_ep = swept_obb_vs_obb(arm_base, arm_base.transformed(rotation=rot_z(120.0)), obs, obs)
    assert res_ep["status"] == "FAIL", f"Expected FAIL from swept_obb_vs_obb for A, got {res_ep}"
    return res


def test_b_180deg_and_wrap() -> dict:
    """B: 180 deg rotation requires explicit trajectory; +180 vs -180 direction & wraparound."""
    arm_base = OBB.from_bounds("arm", 10.0, -3.0, -3.0, 100.0, 3.0, 3.0)
    obs_plus90 = OBB.from_bounds("obs_plus90", -4.0, 50.0, -4.0, 4.0, 70.0, 4.0)

    res_plus = verify_interval_collision(_rot_traj(arm_base, 180.0), StaticTrajectory(obs_plus90))
    assert res_plus["status"] == "FAIL", f"Expected FAIL for +180 deg, got {res_plus}"

    res_minus = verify_interval_collision(_rot_traj(arm_base, -180.0), StaticTrajectory(obs_plus90))
    assert res_minus["status"] == "PASS", f"Expected PASS for -180 deg, got {res_minus}"

    obs_180 = OBB.from_bounds("obs_180", -80.0, -4.0, -4.0, -50.0, 4.0, 4.0)
    d_pivot = float(np.linalg.norm(arm_base.center))
    omega_wrap = abs(math.radians(2.0))
    traj_wrap = LipschitzTrajectory(
        pose_fn=lambda t: arm_base.transformed(rotation=rot_z(179.0 + 2.0 * t)),
        v_center_max=d_pivot * omega_wrap,
        omega_max_rad=omega_wrap,
        r_obb=arm_base.bounding_radius,
        label="Wrap(+179->+181)",
    )
    res_wrap = verify_interval_collision(traj_wrap, StaticTrajectory(obs_180))
    assert res_wrap["status"] == "FAIL", f"Expected FAIL for wrap, got {res_wrap}"

    res_unres = swept_obb_vs_obb(arm_base, arm_base.transformed(rotation=rot_z(180.0)), obs_plus90, obs_plus90)
    assert res_unres["status"] == "UNRESOLVED", f"Expected UNRESOLVED for 180-deg endpoint-only, got {res_unres}"
    return res_minus


def test_c_two_moving_obbs_crossing() -> dict:
    """C: Two moving OBBs whose endpoints are all clear, but they cross at t=0.5."""
    box_a = OBB.from_bounds("a", -5.0, -5.0, -5.0, 5.0, 5.0, 5.0)
    box_b = OBB.from_bounds("b", -5.0, -5.0, -5.0, 5.0, 5.0, 5.0)
    traj_a = LipschitzTrajectory(
        pose_fn=lambda t: box_a.transformed(translation=np.array([-60.0 + 120.0 * t, 0.0, 0.0])),
        v_center_max=120.0, omega_max_rad=0.0, r_obb=box_a.bounding_radius, label="LinearX(120mm)",
    )
    traj_b = LipschitzTrajectory(
        pose_fn=lambda t: box_b.transformed(translation=np.array([0.0, -60.0 + 120.0 * t, 0.0])),
        v_center_max=120.0, omega_max_rad=0.0, r_obb=box_b.bounding_radius, label="LinearY(120mm)",
    )
    res = verify_interval_collision(traj_a, traj_b)
    assert res["status"] == "FAIL", f"Expected FAIL for C, got {res}"
    assert abs(res["t_collision"] - 0.5) < 0.05
    return res


def test_d_clear_paths_pass() -> dict:
    """D: Known clear paths (120-deg rotation, Z-offset moving-vs-moving) return PASS."""
    arm = OBB.from_bounds("arm", 10.0, -3.0, -3.0, 100.0, 3.0, 3.0)
    obs_far = OBB.from_bounds("obs", -4.0, -90.0, -4.0, 4.0, -50.0, 4.0)
    res_rot = verify_interval_collision(_rot_traj(arm, 120.0), StaticTrajectory(obs_far))
    assert res_rot["status"] == "PASS", f"Expected PASS for D-rot, got {res_rot}"
    assert res_rot["clearance_mm"] > 1.0

    box_a = OBB.from_bounds("a", -5.0, -5.0, -5.0, 5.0, 5.0, 5.0)
    box_b = OBB.from_bounds("b", -5.0, -5.0, 15.0, 5.0, 5.0, 25.0)
    traj_a = LipschitzTrajectory(
        pose_fn=lambda t: box_a.transformed(translation=np.array([-50.0 + 100.0 * t, 0.0, 0.0])),
        v_center_max=100.0, omega_max_rad=0.0, r_obb=box_a.bounding_radius,
    )
    traj_b = LipschitzTrajectory(
        pose_fn=lambda t: box_b.transformed(translation=np.array([0.0, -50.0 + 100.0 * t, 0.0])),
        v_center_max=100.0, omega_max_rad=0.0, r_obb=box_b.bounding_radius,
    )
    res_mv = verify_interval_collision(traj_a, traj_b)
    assert res_mv["status"] == "PASS", f"Expected PASS for D-moving, got {res_mv}"
    assert res_mv["clearance_mm"] > 0.0
    return res_mv


def test_e_boundary_and_precision() -> dict:
    """E: 0.01/0.1/1.0 mm gaps, flush contact, thin wall, degenerate SAT axes, combined rot+trans."""
    base = OBB.from_bounds("base", 0.0, 0.0, 0.0, 20.0, 20.0, 20.0)
    for gap in (0.01, 0.1, 1.0):
        other = OBB.from_bounds("other", 20.0 + gap, 0.0, 0.0, 40.0 + gap, 20.0, 20.0)
        traj = LipschitzTrajectory(
            pose_fn=lambda t, b=base: b.transformed(translation=np.array([0.0, 10.0 * t, 0.0])),
            v_center_max=10.0, omega_max_rad=0.0, r_obb=base.bounding_radius,
        )
        res = verify_interval_collision(traj, StaticTrajectory(other))
        assert res["status"] == "PASS", f"Expected PASS for gap={gap}, got {res}"

    flush = OBB.from_bounds("flush", 20.0, 0.0, 0.0, 40.0, 20.0, 20.0)
    res_flush = verify_interval_collision(StaticTrajectory(base), StaticTrajectory(flush), max_depth=6)
    assert res_flush["status"] == "UNRESOLVED", f"Flush contact must return UNRESOLVED, got {res_flush}"

    wall = OBB.from_bounds("wall", 49.75, -20.0, -20.0, 50.25, 20.0, 20.0)
    pin = OBB.from_bounds("pin", -2.0, -2.0, -2.0, 2.0, 2.0, 2.0)
    res_wall = verify_interval_collision(
        LipschitzTrajectory(lambda t: pin.transformed(translation=np.array([100.0 * t, 0.0, 0.0])), 100.0, 0.0, pin.bounding_radius),
        StaticTrajectory(wall),
    )
    assert res_wall["status"] == "FAIL", f"Expected FAIL crossing 0.5 mm thin wall, got {res_wall}"

    a_rot = base.transformed(rotation=rot_axis_angle(np.array([0.0, 0.0, 1.0]), 45.0))
    b_rot = OBB.from_bounds("b_rot", 35.0, 0.0, 0.0, 55.0, 20.0, 20.0).transformed(
        rotation=rot_axis_angle(np.array([0.0, 0.0, 1.0]), 45.0)
    )
    col, _, clr = obb_sat_distance(a_rot, b_rot)
    assert not col and clr > 5.0
    return res_wall


def test_f_sinusoidal_reciprocating_collision() -> dict:
    """F: x(t) = 50*sin(2*pi*t) where t=0, 0.5, 1 are all at x=0, colliding at t=0.25 (pen=2.0 mm)."""
    moving = OBB.from_bounds("moving", -1.0, -1.0, -1.0, 1.0, 1.0, 1.0)
    obstacle = OBB.from_bounds("obstacle", 49.0, -1.0, -1.0, 51.0, 1.0, 1.0)
    traj = LipschitzTrajectory(
        pose_fn=lambda t: moving.transformed(translation=np.array([50.0 * math.sin(2.0 * math.pi * t), 0.0, 0.0])),
        v_center_max=50.0 * 2.0 * math.pi,
        omega_max_rad=0.0,
        r_obb=moving.bounding_radius,
        label="Sin(2*pi*t) A=50",
    )
    res = verify_interval_collision(traj, StaticTrajectory(obstacle))
    assert res["status"] == "FAIL", f"Expected FAIL for F sinusoidal motion, got {res}"
    assert abs(res["t_collision"] - 0.25) < 0.05
    assert res["penetration_mm"] > 0.5
    return res


def test_g_higher_frequency_vanishing_samples() -> dict:
    """G: x(t) = 50*sin(4*pi*t) where t=0, 0.25, 0.5, 0.75, 1.0 ALL equal 0, colliding at t=0.125."""
    moving = OBB.from_bounds("moving_hf", -1.0, -1.0, -1.0, 1.0, 1.0, 1.0)
    obstacle = OBB.from_bounds("obstacle_hf", 49.0, -1.0, -1.0, 51.0, 1.0, 1.0)
    traj = LipschitzTrajectory(
        pose_fn=lambda t: moving.transformed(translation=np.array([50.0 * math.sin(4.0 * math.pi * t), 0.0, 0.0])),
        v_center_max=50.0 * 4.0 * math.pi,
        omega_max_rad=0.0,
        r_obb=moving.bounding_radius,
        label="Sin(4*pi*t) A=50",
    )
    res = verify_interval_collision(traj, StaticTrajectory(obstacle))
    assert res["status"] == "FAIL", f"Expected FAIL for G high-frequency motion, got {res}"
    assert res["colliding"] is True
    return res


def test_h_uncertified_callable_returns_unresolved() -> dict:
    """H: Arbitrary Callable without certified motion upper bound MUST return UNRESOLVED, never PASS."""
    moving = OBB.from_bounds("moving_raw", -1.0, -1.0, -1.0, 1.0, 1.0, 1.0)
    obstacle = OBB.from_bounds("obstacle_raw", 49.0, -1.0, -1.0, 51.0, 1.0, 1.0)

    def raw_pose(t: float) -> OBB:
        return moving.transformed(translation=np.array([50.0 * math.sin(2.0 * math.pi * t), 0.0, 0.0]))

    res = verify_interval_collision(raw_pose, lambda t: obstacle)
    assert res["status"] == "UNRESOLVED", f"Expected UNRESOLVED for uncertified callable, got {res}"
    assert res["certification_condition"] == "missing_certified_motion_bound"
    return res


def run_all() -> None:
    tests = [
        ("A_120deg_rotation_miss", test_a_120deg_rotation_miss),
        ("B_180deg_and_wrap", test_b_180deg_and_wrap),
        ("C_two_moving_obbs_crossing", test_c_two_moving_obbs_crossing),
        ("D_clear_paths_pass", test_d_clear_paths_pass),
        ("E_boundary_and_precision", test_e_boundary_and_precision),
        ("F_sinusoidal_reciprocating", test_f_sinusoidal_reciprocating_collision),
        ("G_higher_freq_vanishing_samples", test_g_higher_frequency_vanishing_samples),
        ("H_uncertified_callable_UNRESOLVED", test_h_uncertified_callable_returns_unresolved),
    ]
    for name, fn in tests:
        res = fn()
        print(
            f"[PASS] {name:34s} -> status={res['status']:10s} | t_col={res['t_collision']} | "
            f"pen={res['penetration_mm']:.3f} | clr_lb={res['clearance_mm']:.3f} | "
            f"bound={res.get('max_interval_bound_mm')} | cond={res['certification_condition']}"
        )
    print("ALL 8 V3.2.1 REGRESSION TESTS (A-H) PASSED.")


if __name__ == "__main__":
    run_all()
