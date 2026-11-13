import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
OUT_PNG = ROOT / "evidence" / "virtual_root_fold_demo.png"
OUT_CSV = ROOT / "data" / "virtual_root_fold_demo.csv"
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
font_manager.fontManager.addfont(FONT_PATH)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams["axes.unicode_minus"] = False

base = Polygon([(0, 0), (315, 0), (315, 20), (0, 20)])
bed = Polygon([(70, 40), (250, 40), (250, 60), (70, 60)])
obstacles = [base, bed]
column = Polygon([(30, 20), (50, 20), (50, 365), (30, 365)])
angles = list(range(0, 91, 2))
lifts = [0, 40, 80, 120, 160]
rows = []
summary = []

for lift in lifts:
    raised = translate(column, yoff=lift)
    pivot = (40, 20 + lift)
    lift_rows = []
    for angle in angles:
        pose = rotate(raised, -angle, origin=pivot)
        intersection = sum(pose.intersection(obstacle).area for obstacle in obstacles)
        clearance = min(pose.distance(obstacle) for obstacle in obstacles)
        row = {"lift_mm": lift, "angle_deg": angle, "intersection_area_mm2": intersection, "clearance_mm": clearance}
        rows.append(row)
        lift_rows.append(row)
    folded = rotate(raised, -90, origin=pivot)
    total = unary_union([base, folded])
    min_x, min_y, max_x, max_y = total.bounds
    collisions = [r for r in lift_rows if r["intersection_area_mm2"] > 1e-6]
    summary.append({
        "lift_mm": lift,
        "max_intersection_mm2": max(r["intersection_area_mm2"] for r in lift_rows),
        "first_collision_deg": collisions[0]["angle_deg"] if collisions else None,
        "folded_depth_mm": max_x - min_x,
        "folded_height_mm": max_y - min_y,
    })

with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

fig, axes = plt.subplots(2, 2, figsize=(13.333, 7.5), dpi=180)
fig.text(0.06, 0.965, "根部翻折虚拟演示｜简化侧视模型，不是实机验收", fontsize=21, fontweight="bold", ha="left")
fig.text(0.06, 0.92, "几何参考：A1 mini 公开外形 347×315×365 mm；仅保留底座、床区和单立柱的简化轮廓", fontsize=11, color="#596467")

for ax, lift, title in [
    (axes[0, 0], 0, "A｜纯根部铰链"),
    (axes[0, 1], 120, "B｜枢轴抬升 120 mm 的演示分支"),
]:
    for obstacle, label in zip(obstacles, ["底座", "床区"]):
        x, y = obstacle.exterior.xy
        ax.fill(x, y, color="#596467", alpha=0.18, label=label)
        ax.plot(x, y, color="#596467", linewidth=1)
    raised = translate(column, yoff=lift)
    pivot = (40, 20 + lift)
    for angle, color in [(0, "#202729"), (30, "#638DA5"), (60, "#9B641B"), (90, "#8B3D3D")]:
        pose = rotate(raised, -angle, origin=pivot)
        x, y = pose.exterior.xy
        ax.plot(x, y, color=color, linewidth=1.6, label=f"{angle}°")
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_xlim(-70, 440)
    ax.set_ylim(-30, 420)
    ax.set_xlabel("侧视前后方向 / mm")
    ax.set_ylabel("高度 / mm")
    ax.grid(alpha=0.15)
    ax.legend(fontsize=8, loc="upper right")

ax = axes[1, 0]
ax.plot([s["lift_mm"] for s in summary], [s["max_intersection_mm2"] for s in summary], marker="o", color="#8B3D3D", linewidth=2)
ax.set_title("C｜整个折叠过程中的最大相交面积", loc="left", fontsize=14, fontweight="bold")
ax.set_xlabel("枢轴抬升量 / mm")
ax.set_ylabel("相交面积 / mm²")
ax.grid(alpha=0.2)

ax = axes[1, 1]
ax.plot([s["lift_mm"] for s in summary], [s["folded_height_mm"] for s in summary], marker="o", color="#638DA5", linewidth=2)
ax.set_title("D｜抬升避让也会抬高收纳状态", loc="left", fontsize=14, fontweight="bold")
ax.set_xlabel("枢轴抬升量 / mm")
ax.set_ylabel("折叠后总高 / mm")
ax.grid(alpha=0.2)

fig.text(0.06, 0.025, "演示只说明几何关系与参数敏感性；不代表实际 A1 mini 内部结构、推荐改法或安全许可。", fontsize=11, color="#596467")
fig.tight_layout(rect=(0.04, 0.06, 0.98, 0.9))
fig.savefig(OUT_PNG, dpi=180, facecolor="white")

print(f"Wrote {OUT_PNG}")
print(f"Wrote {OUT_CSV} with {len(rows)} rows")
for row in summary:
    print(row)
