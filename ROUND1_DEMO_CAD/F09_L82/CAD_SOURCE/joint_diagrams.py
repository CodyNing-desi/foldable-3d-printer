"""2D joint / kinematic schematics per candidate (matplotlib, headless)."""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

import kinematics_r1 as K
from validate_r1 import ROOT, CAND_DIRS

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def r_joint(ax, x, z, label=""):
    ax.add_patch(Circle((x, z), 2.2, fill=False, lw=1.6, color="#DC2626"))
    ax.plot([x], [z], "+", color="#DC2626", ms=6)
    if label:
        ax.annotate(label, (x, z), xytext=(4, 4), textcoords="offset points", fontsize=8, color="#DC2626")


def p_joint(ax, x, z, label=""):
    ax.add_patch(plt.Rectangle((x - 3, z - 2), 6, 4, fill=False, lw=1.6, color="#2563EB"))
    if label:
        ax.annotate(label, (x, z), xytext=(4, -8), textcoords="offset points", fontsize=8, color="#2563EB")


def gantry_schematic(cand: str):
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=150)
    lift = K.LIFT[cand]
    ys = K.TOWER_Y[cand]
    ax.plot([0, 157.5], [10, 10], "k-", lw=2)
    ax.add_patch(plt.Rectangle((35, 18), 90, 10, fill=True, color="#CBD5E1"))
    ax.text(80, 21, "床(固定)", ha="center", fontsize=8)
    for yc in ys:
        ax.plot([10, 10], [10, 69], "-", color="#475569", lw=3)
    p_joint(ax, 13, 17 + lift / 2, f"移动副 抬升{lift:g}")
    ax.add_patch(plt.Rectangle((6, 10 + lift), 15, 14, fill=False, lw=1.4, color="#F59E0B"))
    px, pz = K.PIVOT_X, K.PIVOT_Z0 + lift
    r_joint(ax, px, pz, "根部转动副 0–90°")
    ax.plot([px, px], [pz, pz + 169.5], "-", color="#2563EB", lw=3)
    ax.text(px + 3, pz + 90, "立柱 169.5", fontsize=8, color="#2563EB")
    axp, azp = px + K.ARM_PIVOT[0], pz + K.ARM_PIVOT[2]
    r_joint(ax, axp, azp, "臂转动副 0–90°(下折)")
    ax.plot([axp, axp + 107.5], [azp, azp], "-", color="#0284C7", lw=3)
    ax.text(axp + 50, azp + 4, "X臂 107.5 (215×0.5)", fontsize=8, color="#0284C7")
    ax.add_patch(plt.Rectangle((axp + 42.5, azp - 33.5), 25, 27.5, fill=False, ls="--", color="#0369A1"))
    ax.text(axp + 55, azp - 38, "工具头包络", fontsize=7, color="#0369A1", ha="center")
    if cand == "F09_L82":
        ax.text(13, 30 + lift, "SYNC刚性杆(被动同步)", fontsize=7, color="#7C3AED")
    ax.set_title(f"{cand} 运动简图（侧视, 抬升后/展开位）\n相位: 臂折90° → 抬升{lift:g} → 根部前翻90°")
    ax.set_xlim(-15, 200)
    ax.set_ylim(-5, 235)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Z (mm)")
    fig.tight_layout()
    out = ROOT / CAND_DIRS[cand] / "ASSEMBLY" / "joint_schematic.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[{cand}] {out}")


def scz_schematic():
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=150)
    for ax, H, ttl in ((axes[0], K.SCZ["h_max"], "最高位 H=135"),
                       (axes[1], K.SCZ["h_fold"], "折叠位 H=22.5")):
        Sp = K.scz_span(H)
        sx = K.SCZ["fix_x"] - Sp
        lz = K.SCZ["low_z"]
        hz = lz + H
        ax.plot([0, 157.5], [10, 10], "k-", lw=2)
        ax.plot([sx, 155], [lz, hz], "-", color="#2563EB", lw=3)
        ax.plot([155, sx], [lz, hz], "-", color="#0EA5E9", lw=3)
        r_joint(ax, 155, lz, "固定铰")
        r_joint(ax, sx, lz, "滑动铰(输入)")
        r_joint(ax, (sx + 155) / 2, (lz + hz) / 2, "交叉铰")
        r_joint(ax, 155, hz, "平台固定铰")
        r_joint(ax, sx, hz, "平台滑动铰")
        ax.plot([sx - 10, 160], [hz + 6, hz + 6], "-", color="#1D4ED8", lw=4)
        ax.text(80, hz + 10, "平台(水平姿态保持)", fontsize=8, color="#1D4ED8", ha="center")
        ax.add_patch(FancyArrowPatch((sx - 18, lz), (sx - 4, lz), arrowstyle="->", color="#16A34A", lw=1.5))
        ax.text(sx - 20, lz - 8, "水平输入S", fontsize=8, color="#16A34A")
        ax.set_title(f"{ttl}\nS={Sp:.1f},  H=√(4L²−S²), L=77")
        ax.set_xlim(-10, 175)
        ax.set_ylim(0, 175)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
    fig.suptitle("SCZ 剪叉运动简图（经典固定端+滑动端, 1 DOF; 左右两副由横轴耦合）")
    fig.tight_layout()
    out = ROOT / "SCZ" / "ASSEMBLY" / "joint_schematic.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[SCZ] {out}")


def f08_schematic():
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    ax.add_patch(plt.Rectangle((-60, 0), 200, 175, fill=False, lw=1.5))
    ax.plot([20, 20, -17.5], [13, 25.5, 25.5], "-", color="#16A34A", lw=2.5)
    ax.add_patch(FancyArrowPatch((20, 14), (20, 24), arrowstyle="->", color="#16A34A", lw=1.5))
    ax.add_patch(FancyArrowPatch((18, 25.5), (-15, 25.5), arrowstyle="->", color="#16A34A", lw=1.5))
    ax.text(23, 19, "抬升12.5", fontsize=8, color="#16A34A")
    ax.text(0, 28, "后移37.5", fontsize=8, color="#16A34A")
    r_joint(ax, -17.5, 25.5, "根铰(后翻0→−90°)")
    ax.plot([-17.5, -155], [25.5, 25.5], "--", color="#2563EB", lw=2)
    ax.text(-90, 29, "柱连杆(后翻位)", fontsize=8, color="#2563EB")
    ax.plot([-17.5, -17.5], [25.5, 163], ":", color="#2563EB", lw=1.5)
    ax.text(-15, 100, "抬升/后移位(竖直)", fontsize=7, color="#2563EB")
    ax.plot([-30, -56], [3, 3], "-", color="#7C3AED", lw=2.5)
    ax.text(-45, 6, "后支脚", fontsize=8, color="#7C3AED")
    ax.set_title("F08 平面运动卡简图\n相位: 臂折90° → 抬升12.5 → 后移37.5 → 后翻−90°")
    ax.set_xlim(-70, 150)
    ax.set_ylim(-5, 120)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    out = ROOT / "F08_OPTIONAL" / "ASSEMBLY" / "joint_schematic.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[F08] {out}")


def main():
    for c in ("F09_L82", "F07"):
        gantry_schematic(c)
    scz_schematic()
    f08_schematic()


if __name__ == "__main__":
    main()
