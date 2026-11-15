"""L4 接口试件: 打印完整模型前先验证关键配合。无打印机权限 -> 全部待现场确认。"""
from __future__ import annotations

from pathlib import Path

from build123d import Box, Cylinder, Part, Pos, Rot

from common_r1 import pin, clip, z_hole, y_hole, export_part, save_manifest, CLR_SLD, deliverable_root

ROOT = deliverable_root() / "COUPONS_L4"


def cp_pin_ladder() -> Part:
    p = Pos(35, 15, 3) * Box(70, 30, 6)
    for i, d in enumerate((5.2, 5.3, 5.4, 5.5)):
        p = p - Pos(12 + i * 15, 15, 3) * Cylinder(d / 2, 8)
    p.label = "CP-PIN5-LADDER"
    return p


def cp_slider() -> Part:
    p = Pos(40, 17, 4) * Box(80, 34, 8)
    for i, w in enumerate((6.2, 6.4, 6.6)):
        p = p - Pos(40, 9 + i * 9, 6.5) * Box(70, w, 5.02)
    p.label = "CP-SLIDER-BASE"
    return p


def cp_slider_tongues() -> Part:
    p = Pos(35, 10, 9) * Box(70, 20, 4)
    for i in range(3):
        p = p + Pos(15 + i * 20, 10, 5) * Box(8, 6, 4)
    p.label = "CP-SLIDER-TONGUES"
    return p


def cp_clip_board() -> Part:
    p = Pos(30, 15, 3) * Box(60, 30, 6)
    for i in range(3):
        x = 12 + i * 18
        p = p + Pos(x, 15, 6) * pin(5, 16)
    p.label = "CP-CLIP-BOARD"
    return p


def cp_hinge() -> tuple[Part, Part]:
    base = Pos(20, 15, 5) * Box(40, 30, 10)
    for sy in (-1, 1):
        base = base + Pos(20, 15 + sy * 8.2, 16) * Box(18, 4, 12)
    base = base - Pos(20, 15, 16) * y_hole(5.0, 30, 0.3)
    base = base - Pos(28, 15, 16) * y_hole(3.0, 30, 0.4)
    base = base - Pos(20, 15, 8) * y_hole(3.0, 30, 0.4)
    tongue = Pos(0, 0, 0) * Rot(90, 0, 0) * Cylinder(6, 12)
    tongue = tongue + Pos(0, 0, 8) * Box(12, 12, 16)
    tongue = tongue - y_hole(5.0, 14, 0.3)
    tongue = tongue - Pos(0, 0, 8) * y_hole(3.0, 14, 0.4)
    base.label = "CP-HINGE-CLEVIS"
    tongue.label = "CP-HINGE-TONGUE"
    return base, tongue


def cp_scz_ladder() -> Part:
    p = Pos(30, 15, 3) * Box(60, 30, 6)
    for i, d in enumerate((4.2, 4.3, 4.4)):
        p = p - Pos(12 + i * 18, 15, 3) * Cylinder(d / 2, 8)
    p.label = "CP-SCZ-HOLES"
    return p


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    recs = []
    items = [
        ("CP-PIN5-LADDER", cp_pin_ladder(), "PLA"),
        ("CP-SLIDER-BASE", cp_slider(), "PLA"),
        ("CP-SLIDER-TONGUES", cp_slider_tongues(), "PETG"),
        ("CP-CLIP-BOARD", cp_clip_board(), "PLA"),
        ("CP-SCZ-HOLES", cp_scz_ladder(), "PLA"),
    ]
    for pid, part, m in items:
        recs.append(export_part(part, ROOT, pid, m))
    b, t = cp_hinge()
    recs.append(export_part(b, ROOT, "CP-HINGE-CLEVIS", "PLA"))
    recs.append(export_part(t, ROOT, "CP-HINGE-TONGUE", "PETG"))
    for pid, part, m, q in [("CP-PIN5", pin(5, 16), "PETG", 4), ("CP-PIN4", pin(4, 14), "PETG", 3),
                            ("CP-CLIP5", clip(5), "PETG", 6), ("CP-CLIP4", clip(4), "PETG", 3)]:
        r = export_part(part, ROOT, pid, m)
        r["qty"] = q
        recs.append(r)
    save_manifest(recs, ROOT / "parts_manifest.json")
    (ROOT / "TEST_PLAN.md").write_text(TEST_PLAN, encoding="utf-8")
    print(f"coupons: {len(recs)} -> {ROOT}")


TEST_PLAN = """# L4 接口试件 · 测试尺寸与验收方法（待现场确认）

**状态: 本环境无 3D 打印机操作权限。以下全部为待现场执行的测试计划，未进行真实打印测试。
CAD 级检查（L1–L3）不能替代本试件实测。**

打印: Bambu 0.4 喷嘴, 层高 0.16–0.2, 壁 3–4, 填充 20–40%。板类 PLA, 销/卡圈/舌板 PETG。
每件打印后去毛刺, 用游标卡尺记录实测孔径/槽宽（记录表见下）。

## CP-PIN5-LADDER + CP-PIN5 + CP-CLIP5（销-孔转动配合）
- 测试尺寸: 孔 Ø5.2 / 5.3 / 5.4 / 5.5, 销 Ø5.0。
- 方法: 销逐孔插入, 手转 360°×10 次; 径向晃动目测/塞尺; 卡圈卡入尾槽后轴向拉拔（手感 ~5 N）。
- 验收: 选"转动顺滑且径向晃动 ≤0.3 mm"的最小孔径档为正式转动配合（名义 +0.3）;
  卡圈保持不脱且可拆。若全部过紧 → 正式孔 +0.1; 全部过松 → 销径参数 +0.1 或改金属销（提交采购 Agent）。

## CP-SLIDER-BASE + CP-SLIDER-TONGUES（滑槽移动副）
- 测试尺寸: 槽 6.2 / 6.4 / 6.6, 舌 6.0。
- 方法: 舌在槽内全程推拉 20 次; 侧向晃动塞尺。
- 验收: 手推顺滑无卡滞, 侧隙 ≤0.4 mm → 选名义 +0.4 档; 卡滞则升一档。

## CP-CLIP-BOARD + CP-CLIP5（卡圈保持）
- 方法: 卡圈压入 Ø4.4 尾槽, 拉拔/推压 10 次, 记录脱出力手感与是否断裂。
- 验收: 10 次拆装不裂、保持可靠; 断裂 → 卡圈加厚 0.2 或改 PETG 退火/金属 E 圈（采购建议）。

## CP-HINGE-CLEVIS + CP-HINGE-TONGUE + CP-PIN5（叉耳-舌板 90° 铰链）
- 方法: 组装后 0↔90° 摆动 50 次, 两极限位锁销插拔; 检查极限位是否顶死/松旷。
- 验收: 全摆程无卡滞, 极限位锁销可插, 摆程末端间隙 ≥0.2 mm。

## CP-SCZ-HOLES + CP-PIN4 + CP-CLIP4（剪叉臂孔 Ø4 系）
- 测试尺寸: 孔 Ø4.2 / 4.3 / 4.4, 销 Ø4.0。
- 方法/验收: 同销-孔档, 选 +0.3 档; 臂孔反复摆动 50 次无扩孔/裂纹。

## 记录表（现场填写）
| 试件 | 实测尺寸 | 手感/卡滞 | 选定档位 | 是否回改正式件 | 操作人/日期 |
|---|---|---|---|---|---|
| CP-PIN5 | | | | | |
| CP-SLIDER | | | | | |
| CP-CLIP | | | | | |
| CP-HINGE | | | | | |
| CP-SCZ | | | | | |

冻结后: 将选定间隙写回 common_r1.py 的 CLR_ROT/CLR_SLD, 重新生成正式件并复跑 L1–L3。
"""


if __name__ == "__main__":
    main()
