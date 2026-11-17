"""Generate BOM CSVs and all root-level delivery documents from manifests + validation JSON."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from validate_r1 import ROOT, CAND_DIRS, PREFIX

# part metadata: cn name, subassembly/joint, key interface, print orientation note, alternative
META = {
    "BASE": ("底座板(床支撑/塔安装孔/根铰让位坑)", "基架", "塔销孔Ø3.4@y0,±65; 底面卡圈让位坑", "平放, 底面朝下", "F09/F07共享"),
    "SCZ-BASE": ("SCZ底座(导槽+横轴窗+支脚)", "基架", "舌槽6.4@y±62.5; 横轴窗x0..85,z0..6; 支脚6mm; 锁孔@y±66.2", "平放, 支脚朝下", "—"),
    "BED": ("热床包络标记板", "基架", "搁于底座床支撑墙顶 z26", "平放", "可省略(仅影响避让演示)"),
    "TWR": ("导向塔(双Ø5立导柱, V6.1起不含顶盖)", "抬升移动副", "导柱Ø5@±15; 锁孔Ø3.2@z48; 顶盖销孔Ø3.2@z65; 足部4×Ø3.4", "立放, 导柱竖直", "导柱可改Ø6(需同步改滑座孔)"),
    "CAP": ("可拆顶盖(V6.1新增, 套导柱顶+横销)", "抬升移动副", "套孔Ø5.3@±15; 横销Ø3.2@z65, 每塔2×PIN3-L14", "平放", "修复一体顶盖导致的滑座/SYNC不可装问题"),
    "CAR": ("抬升滑座(双轴套+根部叉耳+旋钮)", "抬升移动副/根部转动副", "轴套孔Ø5.3; 叉耳孔Ø5.3@ (14,3); 锁孔Ø3.2", "旋钮轴朝上(绕Y转-90°)", "轴套可嵌铜螺母(非必须)"),
    "COL": ("立柱管(根舌板+框连接孔; F07另含柱顶臂叉耳)", "根部转动副/(F07)臂转动副", "舌板20厚Ø5.3; 管15×20壁3; 框榫孔Ø3.2@z132/162; F07臂叉耳孔Ø5.3@(16,137)", "立放", "F09/F07柱几何不同(臂叉耳)"),
    "ARM": ("X臂+工具头包络标记(107.5)", "臂转动副", "根舌20厚Ø5.3; 锁孔Ø3.2@x8; 臂16×12", "平放, 臂水平", "工具头标记可拆(减重)"),
    "SYNC": ("双滑座刚性同步杆", "抬升同步(被动耦合)", "2×Ø3.2水平销孔@y±55; Ø5.4导柱让位孔", "平放", "可用2×M3螺钉替代销(外购)"),
    "XBAR": ("龙门顶横梁(含柱顶榫)", "龙门刚性框", "榫8.6×13.6入柱顶; 横销Ø3.2@z162", "平放, 榫朝下先打印", "可与BRG合并为单框(改型)"),
    "BRG": ("龙门中横梁(中央X臂叉耳+端榫入柱内壁)", "龙门刚性框/臂转动副", "中央臂叉耳孔Ø5.3@(16,137)+臂锁孔; 端榫8.6×13@z132; Y向销Ø3.2; 全高中央让位槽", "翻转90°, 端榫朝下", "F09专用(承中央X臂)"),
    "SCZ-ARM": ("剪叉臂(160×10×3, 孔0/77/154)", "剪叉转动副×3", "3×Ø4.3孔; 两端+中心", "平放, 3mm厚朝Z", "臂加厚至4mm(需改叉耳槽)"),
    "SCZ-POST": ("固定铰支座(右下)", "剪叉固定端", "臂B槽3.4; Ø4.3@z12; 轴让位Ø4.6@z16; 4×Ø3.4安装", "立放", "可与底座一体(改底座)"),
    "SCZ-SLB": ("底部滑块(左下输入)", "剪叉滑动端/输入", "舌6×8入底座槽; Ø4.3臂孔+Ø4.0轴孔; 锁孔Ø3.2", "立放(舌朝下)", "舌宽改6.2/6.6按试件"),
    "SCZ-SLT": ("顶部滑块(左上)", "剪叉滑动端(平台)", "舌6×8入平台槽; Ø4.3臂孔+Ø4.0轴孔", "立放(舌朝上→翻转平放)", "同上"),
    "SCZ-SHB": ("底部输入横轴Ø4×164+中央旋钮", "左右同步+手动输入", "压入滑块Ø4.0+Ø2.5横销; 两端卡圈槽", "轴水平沿X", "可加打印丝杆螺母副(改型, 未验证)"),
    "SCZ-SHT": ("顶部横轴Ø4×164", "左右同步", "同SHB无旋钮", "轴水平沿X", "同上"),
    "SCZ-PLAT": ("上平台(165×152×6+滑槽+叉耳+工具头标记)", "剪叉输出", "底面槽6.4@y±71; 叉耳Ø4.3; 轴让位Ø4.6", "平放, 槽朝上(即打印底面)", "可减薄至4mm"),
    "F08-CARD": ("平面运动卡底座(L槽+刻度+后支脚铰)", "F08平面机构", "L槽3.4; 定位孔Ø3.2; 刻度0..-90°", "平放", "—"),
    "F08-SLIDER": ("根滑块(上下 integral 销)", "抬升+后移移动副", "下销Ø3入卡槽; 上销Ø3带卡圈槽", "平放(销竖直)", "—"),
    "F08-COL": ("柱连杆(137.5臂铰距)", "根部转动副", "根孔Ø3.3; 导销孔@(0,20); 臂锁孔×2", "平放", "—"),
    "F08-ARM": ("臂连杆(107.5)+工具头标记", "臂转动副", "根孔Ø3.3; 锁孔@x8", "平放", "—"),
    "F08-FOOT": ("后支脚连杆(防倾覆演示)", "后支脚转动副", "孔Ø3.3; 展开锁孔", "平放", "—"),
}


def pin_meta(pid: str):
    if pid.startswith("PIN"):
        d = pid.split("-")[0].replace("PIN", "")
        d = "2.5" if d == "25" else d
        return (f"打印销轴 Ø{d}", "运动副连接/锁止", f"Ø{d} 转轴, 尾槽+卡圈", "竖直(头朝下)", "可换金属销(外购, 非必须)")
    if pid.startswith("CLIP"):
        d = pid.replace("CLIP", "")
        return (f"C形卡圈 Ø{d} 槽用", "销轴轴向保持", f"卡入Ø{float(d)-0.6:g}尾槽", "平放", "可用E形金属卡圈(外购)")
    return (pid, "—", "—", "平放", "—")


def bom_rows(cand: str):
    cdir = ROOT / CAND_DIRS[cand]
    man = json.loads((cdir / "VALIDATION" / "parts_manifest.json").read_text(encoding="utf-8"))
    rows = []
    for r in man["parts"]:
        pid = r["part_id"]
        short = pid.split("-", 1)[1]
        if pid in META:
            name, joint, iface, orient, alt = META[pid]
        elif short in META:
            name, joint, iface, orient, alt = META[short]
        else:
            name, joint, iface, orient, alt = pin_meta(short)
        qty = r.get("qty", 1)
        rows.append({
            "候选方案": cand, "零件编号": pid, "零件名称": name, "CAD版本": r["cad_version"],
            "数量": qty, "尺寸及关键接口": f"{r['bbox_mm'][0]}×{r['bbox_mm'][1]}×{r['bbox_mm'][2]}mm; {iface}",
            "材料": r["material"], "打印/外购": "打印", "预计耗材质量_g": r["mass_est_g"],
            "是否必须": "必须" if short not in ("BED",) else "可选(避让演示)",
            "是否可复用": ("是(F07/F09共享)" if short == "BASE" else "是(F07/F09/SCZ共享)" if short == "BED" else ("销/卡圈跨方案通用" if short.startswith(("PIN", "CLIP")) else "方案内备件")),
            "替代方案": alt, "所属关节或子装配体": joint, "打印方向": orient,
        })
    return rows


def write_boms():
    all_rows = []
    for cand in CAND_DIRS:
        rows = bom_rows(cand)
        all_rows += rows
        p = ROOT / CAND_DIRS[cand] / "BOM.csv"
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"BOM {cand}: {len(rows)} rows")
    # master: dedup identical geometry across candidates by (short id, bbox, volume)
    seen = {}
    master = []
    for r in all_rows:
        short = r["零件编号"].split("-", 1)[1]
        key = (short, r["尺寸及关键接口"].split(";")[0])
        if key in seen:
            m = seen[key]
            m["数量"] = int(m["数量"]) + int(r["数量"])
            m["候选方案"] += "+" + r["候选方案"]
            m["是否可复用"] = "跨方案共享(几何相同)"
        else:
            m = dict(r)
            seen[key] = m
            master.append(m)
    p = ROOT / "MASTER_PARTS_BOM.csv"
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(master[0].keys()))
        w.writeheader()
        w.writerows(master)
    print(f"MASTER BOM: {len(master)} unique rows")
    return all_rows


def mass_by_material(rows):
    out = {}
    for r in rows:
        key = (r["候选方案"], r["材料"])
        out[key] = out.get(key, 0) + float(r["预计耗材质量_g"]) * int(r["数量"])
    return out


def write_print_plan(rows):
    mm = mass_by_material(rows)
    cands = list(CAND_DIRS)
    totals = {c: sum(v for (cc, _), v in mm.items() if cc == c) for c in cands}
    lines = [
        "# 5 台打印机并行打印计划（ROUND1 缩比演示模型）",
        "",
        f"CAD 版本: R1-V6.1。质量估算 = 实体体积 × 材料密度 × 0.60（3 壁 + 20% 填充近似）。",
        "**以下质量与机时均为 CAD 体积估算，非真实切片结果**；估算打印速度按 15–25 g/h",
        "（0.4 喷嘴, 0.2 层高, Bambu 标准速度）。实际耗材/机时以 Bambu Studio 切片为准。",
        "",
        "## 各方案耗材估算（按方案 BOM 直接求和，含共享件重复计）",
        "",
        "| 方案 | PLA (g) | PETG (g) | 合计 (g) | 估算机时 (h, 单机) |",
        "|---|---|---|---|---|",
    ]
    for c in cands:
        pla = mm.get((c, "PLA"), 0)
        petg = mm.get((c, "PETG"), 0)
        tot = pla + petg
        lines.append(f"| {c} | {pla:.0f} | {petg:.0f} | {tot:.0f} | {tot/22:.1f}–{tot/15:.1f} |")
    # dedup actual print quantity from MASTER
    master = list(csv.DictReader((ROOT / "MASTER_PARTS_BOM.csv").open(encoding="utf-8-sig")))
    dedup = sum(float(r["预计耗材质量_g"]) * int(r["数量"]) for r in master)
    lines += [
        "",
        "## 耗材口径统一（回应 P1-3）",
        "",
        f"- **实际打印总量（MASTER_PARTS_BOM 去重后）≈ {dedup:.0f} g**。BASE/BED 等共享件在 F09/F07/SCZ 间",
        "  几何相同，MASTER 已合并数量，只计一次。上表各方案直接求和会重复计入共享件，故大于此值。",
        f"- 含 20% 余量（备件/试件/失败重打）≈ {dedup*1.2:.0f} g。",
        "- 采购备料请按 **MASTER_PARTS_BOM.csv** 的数量，不要将各方案 BOM 简单相加。",
        "- 所有数字来自 CAD 体积估算（×0.60 填充系数），**未跑真实切片**；README/PR/BOM/本计划口径一致。",
        "",
        "## 机器分配（5 台, 0.4 喷嘴, PLA/PETG 各按需换料）",
        "",
        "| 机器 | 任务 | 说明 |",
        "|---|---|---|",
        "| P1 | F09_L82 全部 PLA 件 | BASE/BED/TWR×2/CAP×2/CAR×2/COL×2/ARM/XBAR/BRG/SYNC |",
        "| P2 | F09_L82 全部 PETG 件 + F07 PLA 件 | 销/卡圈/滑座类; F07 BASE/BED/TWR/CAP/CAR/COL/ARM |",
        "| P3 | F07 PETG 件 + SCZ PLA 件 | SCZ BASE/BED/POST×2/PLAT |",
        "| P4 | SCZ PETG 件 + F08_OPTIONAL 全部 | SCZ 臂×4/滑块×4/轴×2/销; F08 卡/连杆/销 |",
        "| P5 | L4 接口试件 + 全部易损件备件 | 先打印试件! 销/卡圈按 BOM 数量 ×2 备件 |",
        "",
        "## 执行顺序（关键路径）",
        "",
        "1. **P5 先打印 `COUPONS_L4/` 试件**（约 1–2 h），现场试配销孔/滑槽/卡圈，",
        "   按 `COUPONS_L4/TEST_PLAN.md` 记录实测间隙，必要时回改正式件孔径参数再批量打印。",
        "2. P1–P4 并行打印各方案结构件（试件确认前可先打底座/立柱等非配合敏感件）。",
        "3. 配合敏感件（滑座、滑块、叉耳、臂）在试件结论冻结后打印。",
        "4. 每方案先装 1 套验证运动，再补备件。",
        "",
        "## 切片建议（Bambu Studio, 0.4 喷嘴）",
        "",
        "- 层高 0.2 mm；壁 3 圈；填充 20% Gyroid；PLA 喷嘴 220 °C / PETG 240 °C（按耗材标签）。",
        "- 销轴/卡圈：PETG，层高 0.16 mm，壁 4 圈，填充 40%（提高销轴剪切与卡圈弹性寿命）。",
        "- 运动配合孔按 CAD 名义尺寸打印，**不要**在切片里额外加孔补偿；先试件后冻结。",
        "- 支撑：仅 XBAR 榫朝下时建议改立放避免支撑；其余件按 BOM 打印方向基本无支撑。",
        "- 3MF 为几何排版工程（不含切片参数），导入后按上表设置材料/参数再切片。",
        "",
        "## 备件策略",
        "",
        "- 全部销轴、C 形卡圈按 BOM 数量 ×2 打印（P5）。卡圈为弹性易损件，优先备件。",
        "- 剪叉臂（SCZ-ARM）+2 备件；滑块（SLB/SLT）各 +1；F08 销 +2。",
        "- 底座/立柱等大件不备件（损坏概率低，重打成本低）。",
    ]
    (ROOT / "PRINT_PLAN_5_MACHINES.md").write_text("\n".join(lines), encoding="utf-8")
    print("PRINT_PLAN written")


def write_motion_report():
    lines = [
        "# ROUND1 缩比演示模型 · 运动与装配验证报告",
        "",
        "CAD 版本 R1-V6.1 · 连杆几何 1:2（V3.2.1 冻结参数 × 0.5）· 单位 mm",
        "",
        "## 0. 证据等级与方法（必读）",
        "",
        "- **L1 参数/几何**：build123d BREP 实体 → STL/STEP；trimesh 复核水密/**单实体(n_bodies=1)**/体积/包围盒；",
        "  关节中心距与 V3.2.1 冻结参数 ×0.5 对照（见各方案 VALIDATION/L1_parts.json 与下表）。",
        "- **L2 运动学（穿透）**：对每个方案执行 展开→折叠→逆向恢复 全行程。正向与逆向经过同一组状态，",
        "  采样 t∈[0,1] 共 2001 步；每一步对全部非允许接触零件对做 AABB 粗筛 + manifold 精确网格布尔",
        "  求穿透体积；关节变量做解析限位与相位顺序检查。另对关键相位（臂折/根翻/剪叉行程）分子相位",
        "  计算运动件顶点集扫掠凸包与静态件求交：凸包不相交即该子相位连续无碰撞的保守证明；凸包相交者",
        "  在该子相位内做 2001 步细化采样判定（保守伪阳性/真实穿透）。**整体仍非解析连续碰撞认证**",
        "  （未给出 Lipschitz 运动上界的数学证明）；未做凸包覆盖的零件对依赖密集采样。",
        "- **L2b 装配约束闭合（V6 新增，回应 P0-3）**：以零件局部坐标系的关节基准（与实际 CAD 孔心一致）",
        "  在全行程逐步验证：① 运动副连接件位置一致性（铰链点重合/径向偏移）；② 铰链轴线共线性（轴线夹角）；",
        "  ③ 销-孔接口（直径间隙 0.15–0.6 mm）；④ 滑块-导轨约束保持（导路偏移）；⑤ 刚性连接件相对位姿不变；",
        "  ⑥ 全行程连接闭合误差上限。另做 **CAD 孔轴审计**：用 BRepAdaptor 提取每个零件的圆柱面，确认每个铰链",
        "  基准处确实存在指定直径、轴线通过基准点的孔（防止'只改动画不改零件'）。见 L2b_closure.json。",
        "  **'2001 步无穿透'不再单独作为可装配判据；须 L2b 闭合 + 孔轴审计同时通过。**",
        "- **L3 可制造性**：包围盒 vs 250 mm 安全平台、最小壁厚（设计参数表）、打印方向、",
        "  耗材质量估算（体积×密度×0.60）。悬垂以打印方向建议控制，未做逐面悬垂角仿真。",
        "- **L4 接口试件**：已生成试件 STL 与验收方法；**本环境无打印机操作权限，全部标注待现场确认，",
        "  未进行真实打印测试**。CAD 检查不等于打印测试。",
        "",
        "## 1. 参数溯源",
        "",
        "全尺寸参数取自 GitHub PR#1（sync/v2-to-v3_2_1 @ 6229d60）：",
        "`simulation_v3_2_1/config/candidates_v3_2_1.json` + `scripts/run_v3_2_1_verification.py` 冻结覆盖值。",
        "",
        "| 方案 | 全尺寸关键参数 (V3.2.1) | 演示模型 (×0.5) |",
        "|---|---|---|",
        "| F09_L82 | lift 82, 双柱 y±130 塔, X臂 215, 根翻 90° | lift 41, 塔 y±65, 臂 107.5, 根翻 90° |",
        "| F07 | lift 75, 单柱, X臂 215, 根翻 90° | lift 37.5, 臂 107.5, 根翻 90° |",
        "| SCZ | 臂半长 154 (全臂 308), H 270→45 | 半长 77 (全臂 154), H 135→22.5 |",
        "| F08 | lift 25/30, shift -75, 后翻 90° | lift 12.5, shift -37.5, 后翻 90° (平面卡) |",
        "",
        "局部放大（保持运动学关系）：销轴 Ø5/Ø4/Ø3（原 Ø8/Ø6 缩比后过小）；根部铰点抬高 3 mm 布置叉耳；",
        "臂铰点前移 8.5 mm、抬高 2.5 mm 保证臂下折避让；床面降 2 mm 保证折叠臂净距；",
        "SCZ 错层 8.5 mm（原 10×0.5=5，放大避让）、底铰抬高 6 mm（固定座叉耳强度）；F09 顶横梁改为柱顶盖板+榫（+8 mm）。",
        "**V6 关键修正：F09 中央 X 臂（y=0）铰接于中横梁 BRG 的中央叉耳（而非悬空/动画连接），",
        "中横梁抬高至 world z142.5–157.5 承载臂铰；F07 单柱则由柱顶叉耳直接承臂。**",
        "**V6.1 装配拓扑修复：一体式塔顶盖封死导柱顶端，滑座（闭口轴套）与 SYNC（过柱孔）物理上无法装入，",
        "运动学/碰撞验证无法发现此类问题。顶盖拆分为独立 CAP 件（每塔 2×PIN3-L14 销接），先套件后锁顶盖；",
        "复跑 L1/L2/L2b：0 穿透、0 闭合失败、0 孔缺失，新增 CAP 相关扫掠凸包经细化采样确认无穿透。**",
        "",
        "## 2. 各方案结果",
        "",
    ]
    for cand in CAND_DIRS:
        vd = ROOT / CAND_DIRS[cand] / "VALIDATION"
        l1 = json.loads((vd / "L1_parts.json").read_text(encoding="utf-8")) if (vd / "L1_parts.json").exists() else []
        lim = json.loads((vd / "L2_joint_limits.json").read_text(encoding="utf-8")) if (vd / "L2_joint_limits.json").exists() else {}
        sw = json.loads((vd / "L2_sweep.json").read_text(encoding="utf-8")) if (vd / "L2_sweep.json").exists() else {}
        bad = [r for r in l1 if not r["watertight"] or r.get("n_bodies", 1) != 1]
        lines.append(f"### {cand}")
        lines.append("")
        lines.append(f"- L1: {len(l1)} 件 STL 复核（水密/单实体/体积偏差），异常 {len(bad)} 件" + (f": {[r['part_id'] for r in bad]}" if bad else ""))
        if lim:
            lines.append(f"- L2 关节限位/相位: {json.dumps(lim, ensure_ascii=False)}")
        if sw:
            lines.append(f"- L2 全行程扫描 {sw.get('steps')} 步: 非允许接触对穿透 {sw.get('n_penetrations')} 处, "
                         f"未解析 {len(sw.get('unresolved', []))} 处")
            if sw.get("worst_by_pair"):
                lines.append(f"- 穿透明细（最差）: {json.dumps(sw['worst_by_pair'], ensure_ascii=False)}")
            if not sw.get("n_penetrations"):
                lines.append("- 结论: 在采样与允许接触定义下未检出非预期穿透（证据等级见 §0）。")
            hc = sw.get("hull_checks", [])
            if hc:
                clear = sum(1 for h in hc if h["status"] in ("CLEAR_CONSERVATIVE", "CLEAR_BY_REFINEMENT"))
                refined = sum(1 for h in hc if h["status"] == "CLEAR_BY_REFINEMENT")
                flag = [h for h in hc if h["status"] not in ("CLEAR_CONSERVATIVE", "CLEAR_BY_REFINEMENT")]
                lines.append(f"- 关键相位扫掠凸包保守检查: {len(hc)} 对, {clear} 对确认连续无碰撞"
                             f"（其中 {refined} 对凸包保守相交后经相位内 2001 步细化采样确认无穿透）, "
                             f"{len(flag)} 对未决" + (f": {json.dumps(flag, ensure_ascii=False)}" if flag else ""))
        l2b = json.loads((vd / "L2b_closure.json").read_text(encoding="utf-8")) if (vd / "L2b_closure.json").exists() else {}
        if l2b:
            clo = l2b.get("closure", {})
            ha = l2b.get("cad_hole_audit", {})
            pins = l2b.get("pin_interfaces", [])
            lines.append(f"- **L2b 装配约束闭合（V6 新增）**: {clo.get('n_joints')} 个运动副, 全行程闭合失败 "
                         f"{len(clo.get('fails', []))} 处; CAD 孔轴审计 {ha.get('n_checks')} 项, 缺失 "
                         f"{len(ha.get('missing', []))} 项; 销-孔间隙合格 {sum(1 for p in pins if p['ok'])}/{len(pins)}。")
            mx = clo.get("stats", {})
            worst_radial = max((s.get("max_radial", 0) for s in mx.values()), default=0)
            worst_axis = max((s.get("max_axis_deg", 0) for s in mx.values()), default=0)
            worst_rigid = max((s.get("max_rigid", 0) for s in mx.values()), default=0)
            worst_slide = max((s.get("max_slide_dev", 0) for s in mx.values()), default=0)
            lines.append(f"  闭合误差上限: 铰链径向 {worst_radial:.2e} mm, 轴线夹角 {worst_axis:.2e}°, "
                         f"刚体相对位姿 {worst_rigid:.2e}, 滑块导路偏移 {worst_slide:.2e} mm。")
        lines.append("")
    lines += [
        "## 3. 机构学声明与运动链（V6）",
        "",
        "- **F09_L82 运动链**：底座→(移动副)双滑座→(根部转动副,同轴)双立柱+顶横梁XBAR+中横梁BRG(刚性龙门)",
        "  →(**中横梁中央叉耳转动副**)中央X臂(y=0)→工具头标记。双滑座由刚性 SYNC 杆被动耦合 → 演示运动学同步，",
        "  **不验证原双丝杆+同步带传动的载荷分配、消回差与同步误差**。抬升后翻折，相位与 V3.2.1 一致。",
        "  V6 修复 P0-1：X 臂现物理铰接于 BRG 中央叉耳（零件级 CAD，孔轴审计确认），不再是悬空/动画连接。",
        "- **F07 运动链**：底座→(移动副)单滑座(双Ø5导柱抗转)→(根部转动副)单立柱→(柱顶叉耳转动副)X臂。",
        "  抬升/臂折/根翻三手动输入，相位同上。",
        "- **SCZ 运动链**：底座→(移动副)底滑块×2(底部横轴SHB刚性耦合,手推输入)→臂A×2；底座固定座→臂B×2；",
        "  臂A/臂B 中心铰交叉；臂A顶→平台叉耳(固定铰,x=155)；臂B顶→(移动副)顶滑块×2(顶部横轴SHT刚性耦合)→平台底槽。",
        "  平面 Grübler 3×5−2×7=1 DOF；平台水平姿态保持、平台 x 不漂移。H=√(4L²−S²)，S=固定铰↔滑动铰水平距。",
        "  V6 修复 P0-2：顶部横轴 SHT 随顶滑块 sx 移动（此前误置于固定 fix_x），左右镜像耦合与平台约束经 L2b 闭合复核。",
        "  **与仿真对称丝杆驱动的差异已声明；不演示丝杆推力/自锁；低位 |dH/dS| 大见 L2 输出。**",
        "- **F08**：平面运动卡（brief 允许）。V6：L 槽相位改为抬升(0.20–0.40)→后移(0.40–0.55)顺序无重叠，",
        "  避免根销在 L 槽内对角卡滞；导销+定位孔保证 0°/−90°，臂先折；仅演示运动关系，不演示整机包络。",
        "",
        "## 4. 未验证事项",
        "",
        "- 真实打印配合（L4 待现场确认）；真实摩擦/间隙/卡滞；承载与刚度；寿命；",
        "- 连续碰撞数学认证；采样间隔内的穿透；柔性变形下的干涉；",
        "- 3MF 切片参数与实机打印时间（几何工程已生成，参数见 PRINT_PLAN）。",
    ]
    (ROOT / "MOTION_VALIDATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("MOTION_VALIDATION_REPORT written")


def write_limitations():
    txt = """# ROUND1 演示模型 · 模型限制与声明（MODEL_LIMITATIONS）

## 1. 目的边界
本轮为**机械原理缩比演示**（教师明确允许 1:10 等缩比，只要现场演示原理）。
模型用于演示自由度、运动顺序、展开/折叠路径、基本约束与潜在干涉，**不是**整机性能验证件：
不承载工程载荷、不测真实刚度/寿命/精度、不复现电控、不使用金属导轨/工业轴承。

## 2. 缩比与局部放大
- 连杆几何统一 1:2（V3.2.1 冻结参数 ×0.5）。1:5 时臂仅 43 mm、销约 1.6 mm，无法可靠打印装配，
  故按 brief 允许的比例自由度选 1:2；运动学关系（杆长比、铰点距、相位、行程比）保持。
- 局部放大：销轴 Ø5/Ø4/Ø3、叉耳厚 4、舌板 20、根部铰点 +3 mm、臂铰点前移 8.5 mm 并抬高 2.5 mm、
  床面降 2 mm、SCZ 错层 8.5 mm、SCZ 底铰抬高 6 mm（固定座叉耳强度）、F09 顶横梁 +8 mm。
  **V6：F09 中横梁抬高至 world z142.5–157.5 以承载中央 X 臂叉耳（V5 曾下移，已纠正）**。
  这些改变局部包络，不改变机构自由度与运动路径拓扑。缩比选择依据见 SCALE_JUSTIFICATION.md。

## 3. 机构简化声明（逐方案）
- **F09_L82**：取消双 T8 丝杆+同步带；双滑座用刚性 SYNC 杆被动耦合。
  → 只演示运动学同步，**不得声称验证了原双柱同步传动机构**（载荷分配/消回差/同步误差均未验证）。
  抬升为手推+两位置锁销，非丝杆驱动。**中央 X 臂(y=0)物理铰接于中横梁 BRG 中央叉耳**（V6 修复 P0-1），
  运动链：底座→滑座→立柱+XBAR+BRG(刚性龙门)→BRG中央叉耳→X臂，经 L2b 闭合与孔轴审计确认。
- **F07**：双 Ø5 导柱保留抗转导向（对应原双光轴）；抬升手推+锁销；根部/臂铰链为打印销+叉耳，
  非原 CNC M8 耳片+锥销。X 臂铰于柱顶叉耳（单柱，无 BRG）。导向间隙按打印配合，非原 0.021 mm 认证净距。
- **SCZ**：仿真为对称丝杆驱动（两端滑动、平台居中）；演示模型为经典固定端+滑动端剪叉（镜像），
  1 DOF 可证、平台水平、平台 x 不漂移；H=√(4L²−S²) 与参考式一致（S 定义见报告）。
  输入为手推底部横轴，**不演示丝杆推力、效率、自锁**；无载荷摩擦不代表真实输入推力。
  左右副由上下横轴刚性耦合（理想 1 DOF，打印间隙吸收过约束）；**顶横轴随顶滑块移动**（V6 修复 P0-2）。
- **F08_OPTIONAL**：平面运动卡，仅演示后移/抬升/反向翻折/避让顺序；不演示整机 897 mm 折叠包络。
  V6：L 槽相位顺序化（抬升→后移无重叠），避免根销对角卡滞。
- **F12**：V3.2.1 No-Go，本轮不制造。

## 4. 验证证据等级
- L1/L2/L3 为 CAD 级检查（BREP+网格布尔+密集采样 2001 步），**非连续碰撞认证**，
  采样间隔内穿透理论上可能漏检；允许接触对（销-孔、滑槽、叉耳-舌板）按运动副名义接触排除。
- L4 接口试件已生成，**无打印机权限，全部待现场确认**；CAD 检查 ≠ 真实打印测试。
- 仿真认证净距 0.007–0.023 mm 为 OBB 理论值，不覆盖 FDM ±0.2–0.5 mm 公差；
  演示模型配合间隙按 0.3/0.4 mm 设计，须试件冻结。

## 5. 制造与材料
- PLA：底座/床/塔/柱/臂/平台等几何展示件。PETG：销轴/卡圈/滑块/剪叉臂/舌板类等反复拆装、
  弹性或冲击件。不得全部用同一种材料（见 BOM 逐件指定）。
- 3MF 为标准几何排版工程，**不含切片参数**；Bambu Studio 导入后按 PRINT_PLAN 设置。
- 质量/机时为估算（体积×密度×0.60，15–25 g/h），以实际切片为准。

## 6. 采购
- 目标零新增采购：全部零件打印。若试件表明打印销/卡圈保持力不足，可提交采购 Agent 评估
  金属 E 卡圈/标准销（外购建议见 BOM 替代方案列），**本 Agent 不自行下单**。

## 7. 迭代记录
- R1-V1 首版经 L2 密集扫描检出 COL×TWR / SYNC×TWR 真实干涉（柱管/舌板/同步杆与塔顶盖、塔足）。
- R1-V2 修正塔足摆槽/顶盖位置后，复扫仍检出: 塔足摆槽坐标偏移、塔顶盖实际标高错误（F07 臂×塔）、
  SCZ 横轴穿臂/顶滑块臂摆干涉。
- R1-V3 修正塔足摆槽坐标/顶盖标高、SCZ 叉耳滑块与横轴窗后，复扫: F09 全清; F07 臂折末段
  工具头标记角点擦塔顶盖 14mm³; SCZ 0 穿透但 SLB/SLT 网格不水密（横销孔/轴孔与端面齐平切出破面）。
- R1-V4 臂铰点再抬高 2.5mm、SCZ 吊耳加深/横销孔超程/顶舌板加厚/平台通槽/顶横轴 hz+9、
  允许接触对基名修正、根翻凸包 12 子相位后: 全量 0 穿透/0 未解析/水密全过；但**单实体检查**发现
  COL 臂叉耳与柱壁未连接（3 实体）、SCZ 固定座被臂槽切成两半、SCZ 底座支脚面接触未融合。
- R1-V5: COL 叉耳加连接腹板；SCZ 固定座改叉耳式（底铰抬高 6mm 至 world z18）；
  支脚/床墙/旋钮改体积重叠融合；L1 增加单实体(n_bodies)强制检查；装配接口复核修正:
  塔安装销 L20→L14、固定座销 L20→L13、同步杆改水平销 L18+滑座凸台、中横梁端榫加长入柱壁让位槽。
- **R1-V6（当前，回应独立审查）**:
  P0-1 F09 中央 X 臂改铰接于中横梁 BRG 中央叉耳（零件级 CAD，立柱叉耳移除）；
  P0-2 SCZ 顶横轴 SHT 随顶滑块 sx 移动；P0-3 新增 L2b 装配约束闭合检查 + CAD 孔轴审计；
  P1-1 deliverable_root() 修复源码路径并干净复现；P1-2 旧销清理 + 历史归档 HISTORY/；
  P1-3 SCALE_JUSTIFICATION 缩比依据 + 耗材口径统一（MASTER 去重，标注非真实切片）；
  附加 F08 L 槽相位顺序化。逐项见 CHANGELOG_V5_V6.md。
  V1–V5 记录保留于 notes.md §6 与 VALIDATION/HISTORY/。
- **R1-V6.1（当前，装配拓扑修复）**：一体式塔顶盖导致滑座/SYNC 物理不可装（闭口轴套 vs 两端封闭导柱），
  顶盖拆分为独立 CAP 件（套导柱顶 z63..67 + 每塔 2×PIN3-L14 横销 z65）；TWR 增顶盖销孔；
  运动学/验证/BOM/3MF/装配指南同步；复跑 L1/L2/L2b 全绿（详见 CHANGELOG_V6_1.md）。
- 后续如实测/装配失败 → V7 并重新验证。
"""
    (ROOT / "MODEL_LIMITATIONS.md").write_text(txt, encoding="utf-8")
    print("MODEL_LIMITATIONS written")


def write_assembly_guide():
    txt = """# ROUND1 缩比演示模型 · 装配指南（ASSEMBLY_GUIDE）

> **V6.1 装配修复**：导向塔顶盖拆分为独立 CAP 件（每塔 2×PIN3-L14 横销+卡圈）。
> V6 及之前的一体式顶盖封死导柱顶端，滑座与 SYNC 在物理上无法套入；V6.1 起先套件、后锁顶盖。

通用约定：销轴插入后在尾槽卡入 C 形卡圈（PETG）；转动配合孔 = 销径 +0.3 mm，滑动 +0.4 mm。
锁销（PIN3）在两个极限位置之间移插，实现"简化锁止"。装配前请先完成 `COUPONS_L4` 试配。
各方案 `ASSEMBLY/view_*.png` 与 `contact_sheet.png` 为姿态参考，`motion.gif` 为全行程动画。

## A. F09_L82（双柱抬升+折叠，3 手动输入）
刚体：底座/床(固定)、塔×2(固定)、滑座×2(移动副)、SYNC杆(刚性耦合)、柱×2+XBAR+BRG(刚性龙门)、X臂。
运动副：滑座-塔 移动副(Z)×2；柱根-滑座 转动副(Y)×2（同轴）；**臂-中横梁BRG中央叉耳 转动副(Y)×1**。
1. 底座平放；床板搁于床支撑墙顶。
2. 塔×2 装于 y=±65：4×PIN3-L14 竖直穿过塔足+底座，底面让位坑内卡 CLIP3。
3. 滑座×2 套入塔导柱（轴套孔 Ø5.3），压到底；旋钮朝后（背面）。
4. SYNC 杆置于两滑座顶面，4×PIN3-L18 水平穿滑座凸台+杆端，卡 CLIP3 → 双滑座刚性同步。
   然后装可拆顶盖：CAP×2 分别套入两塔导柱顶（z63..67），每塔 2×PIN3-L14 横穿顶盖+导柱 z65 孔，卡 CLIP3。
5. 柱×2 根舌板插入滑座叉耳，PIN5-L34 横穿，卡 CLIP5；0° 锁销 PIN3-L34 插 (14,·,11) 孔。
6. XBAR 榫插入两柱顶，2×PIN3-L22 横穿；BRG 端榫插入柱内壁(z132)，2×PIN3-L18 横穿 → 刚性龙门。
7. **X臂根舌插入中横梁 BRG 中央叉耳(y=0)**，PIN5-L34 横穿，卡 CLIP5；0° 锁销 PIN3-L34 插臂锁孔。
演示顺序：① 拔臂锁销，臂下折 90°，锁销插 90° 孔；② 拔滑座底位限制，推旋钮抬升 41 mm，
   顶部 PIN3-L26 横穿导柱孔锁位；③ 拔根锁销，龙门整体前翻 90°，锁销插 90° 孔。逆向恢复。
干涉关注：臂下折时工具头标记与床/塔；前翻时柱与塔顶盖、臂与床（见验证报告）。

## B. F07（单柱抬升+根部翻折）
与 F09 共享 BASE/BED/TWR/CAR/ARM；**COL 不同**：F07 柱顶带臂叉耳（直接承臂），F09 柱不带（臂铰于 BRG）。
仅装中央塔(y=0)、单滑座、单柱，无 SYNC/XBAR/BRG。步骤同 A.1–A.3；**A.3 滑座试装顺畅后立即装顶盖 CAP**
（2×PIN3-L14 横穿+卡圈），再继续 A.5；臂根舌插入**柱顶叉耳**，
PIN5-L34 横穿+卡圈，0° 锁销 PIN3-L34。导向由双 Ø5 导柱抗转。演示顺序同 A。

## C. SCZ（剪叉升降，1 手动输入）
刚体：SCZ底座(固定, 含横轴窗与支脚)、固定铰支座×2、剪叉臂×4、底滑块×2(叉耳+吊耳)、
顶滑块×2(叉耳+舌板)、上下横轴、平台。
运动副：臂A-底滑块/平台叉耳 转动副；臂B-固定座/顶滑块 转动副；臂A-臂B 中心转动副；
滑块-底座/平台 移动副(X)；横轴-滑块 固接（左右同步）。平面 Grübler 1 DOF。
1. SCZ底座平放（支脚朝下，底面横轴窗贯通）；床板搁于床支撑墙顶。
2. 固定铰支座×2 装于 (155, ±71)，4×PIN3-L13 竖直+底面卡圈。
3. 底滑块×2 吊耳入底座舌槽(y=±62.5)；臂A×2 底孔入滑块叉耳，PIN4-L18 横穿，卡 CLIP4。
4. 底部横轴 SHB 从底座下方穿入两滑块吊耳 Ø4.0 孔（压入），Ø2.5 横销自下而上防转；
   两端卡 CLIP4；中央旋钮在底座横轴窗内（支脚保证旋钮离桌间隙）。
5. 臂B×2 底孔装于固定座（PIN4-L16），卡 CLIP4。
6. 臂A/臂B 中心孔对齐，PIN4-L16 横穿两臂（错层 8.5 mm），卡 CLIP4 → 剪叉交叉铰。
7. 顶滑块×2 叉耳套臂B 顶孔（PIN4-L18）；顶部横轴 SHT 穿顶滑块舌板 Ø4.0 孔压入+横销+卡圈。
8. 平台叉耳套臂A 顶孔（PIN4-L18）；顶滑块舌板入平台底槽，横轴落入平台边部让位槽。
9. 折叠/最高位锁销 PIN3-L24 穿底滑块耳+底座定位孔(y=±66.2/±58.8)，底面坑内卡圈。
演示：推/拉底部旋钮 → 平台水平升降；观察低位"水平输入大、垂直输出小"（dH/dS）。
注意：平台保持水平且 x 不漂移（固定端在右）；行程限位 H=22.5..135。

## D. F08_OPTIONAL（平面运动卡）
层叠：卡(0–3) → 滑块(3–6) → 柱连杆(6–9) → 臂连杆(9–12)，销沿 Z。
1. 滑块下销入卡 L 槽起点 (20,13)；柱连杆根孔套滑块上销，卡 CLIP3。
2. 导销 PIN3-L12 自下而上穿卡平行 L 槽+柱 (0,20) 孔，顶面卡 CLIP3 → 抬升/后移时柱保持竖直。
3. 臂连杆根孔套柱顶销 PIN3-L14（自下而上，顶面卡圈）；臂锁销 PIN3-L14 插 0° 孔。
4. 后支脚连杆铰于卡 (-30,3)，展开锁孔定位。
演示：① 臂折 90°（锁销移位）；② 推滑块沿 L 槽先上 12.5 再后 37.5（导销在平行槽内）；
③ 拔导销，柱绕根销后翻 −90°，导销插 −90° 定位孔；④ 展开后支脚。逆向恢复。

## 拆装
全部销轴为 headed pin + C 卡圈，用小平口起子撬卡圈即可拆；卡圈为备件易损件。
"""
    (ROOT / "ASSEMBLY_GUIDE.md").write_text(txt, encoding="utf-8")
    print("ASSEMBLY_GUIDE written")


def write_readme():
    master = list(csv.DictReader((ROOT / "MASTER_PARTS_BOM.csv").open(encoding="utf-8-sig")))
    dedup = sum(float(r["预计耗材质量_g"]) * int(r["数量"]) for r in master)
    txt = f"""# ROUND1_DEMO_CAD — 可折叠3D打印机 第一轮缩比机械原理演示模型

版本 **R1-V6.1** · 2026-11-17 · 连杆几何 1:2（V3.2.1 冻结参数 ×0.5）· 单位 mm

## 来源与版本
- 参数基准: GitHub CodyNing-desi/foldable-3d-printer **PR#1 (sync/v2-to-v3_2_1 @ 6229d60)**，
  `simulation_v3_2_1/config/candidates_v3_2_1.json` + `scripts/run_v3_2_1_verification.py` 冻结值。
  main 不是最新；旧 stageB 交付包为外购五金夹具体系，本轮已重建为纯打印可活动机构。
- 候选: M1 F09_L82 / M2 F07 / M3 SCZ / M4 F08_OPTIONAL（F12 No-Go 不制造）。
- V6 回应独立审查 P0-1/P0-2/P0-3/P1-1/P1-2/P1-3，逐项见 **CHANGELOG_V5_V6.md**。
- **V6.1 装配拓扑修复**：一体顶盖封死导柱导致滑座/SYNC 不可装，顶盖拆分为独立 CAP 销接件，见 **CHANGELOG_V6_1.md**。

## 目录
- `F09_L82/ F07/ SCZ/ F08_OPTIONAL/`: 各含 CAD_SOURCE(自包含参数化 build123d 源) / STEP(逐件+装配) /
  STL(逐件打印) / 3MF(排版工程, 无切片参数) / ASSEMBLY(姿态图+动画+运动简图+装配STL) /
  VALIDATION(L1/L2/L2b/L3 JSON+清单, HISTORY/ 归档旧版) / BOM.csv。
- `COUPONS_L4/`: 接口试件 STL + TEST_PLAN.md（待现场确认）。
- 根级: MASTER_PARTS_BOM.csv / MOTION_VALIDATION_REPORT.md / PRINT_PLAN_5_MACHINES.md /
  ASSEMBLY_GUIDE.md / MODEL_LIMITATIONS.md / SCALE_JUSTIFICATION.md / CHANGELOG_V5_V6.md / CHANGELOG_V6_1.md /
  PURCHASE_INTERFACE.md / REPRODUCTION_REPORT.md / SHA256SUMS.txt。

## 再生成（CAD_SOURCE 自包含，可在干净目录运行）
项目 venv (Python 3.12 + build123d 0.13 + cadquery-ocp-novtk + trimesh + manifold3d + networkx)：
```
python build_all.py            # 逐件 STL/STEP + 装配
python validate_r1.py          # L1/L2/L2b(装配闭合+孔轴审计)/L3
python render_r1.py --gif      # 快照/动画
python joint_diagrams.py       # 运动简图
python build_coupons.py        # L4 试件
python make_3mf.py             # 3MF 排版
python make_docs.py            # BOM/文档
python package.py              # 归档历史 + SHA256 + ZIP
```
输出目录由 common_r1.deliverable_root() 自动定位（或设环境变量 ROUND1_OUT）。复现核查见 REPRODUCTION_REPORT.md。

## 耗材（CAD 估算，非真实切片）
- 实际打印总量（MASTER 去重）≈ **{dedup:.0f} g**；含 20% 余量 ≈ {dedup*1.2:.0f} g。备料以 MASTER_PARTS_BOM.csv 为准。
- 各方案 BOM 求和含共享件重复计；口径统一见 PRINT_PLAN / SCALE_JUSTIFICATION。机时按 15–25 g/h 估算。

## 关键声明（详见 MODEL_LIMITATIONS.md）
- 纯 PLA/PETG 打印机构，零新增采购目标；可活动，非静态姿态轮廓。
- F09 中央 X 臂物理铰接于中横梁中央叉耳（V6 修复）；双柱同步为刚性杆被动耦合，不验证原双丝杆+同步带传动。
- SCZ 为经典固定端+滑动端剪叉（1 DOF 可证），顶横轴随顶滑块移动（V6 修复）；与仿真对称丝杆驱动差异已声明。
- 验证: L1 水密/单实体；L2 密集采样+凸包保守检查（非连续碰撞认证）；**L2b 装配约束闭合+CAD 孔轴审计**；
  L4 无打印机权限，待现场确认。"2001 步无穿透"不单独作为可装配判据。
"""
    (ROOT / "README.md").write_text(txt, encoding="utf-8")
    print("README written")


def write_purchase_interface():
    txt = """# 采购 Agent 对接说明（ROUND1 机械装配 BOM）

## 结论：本轮零新增采购（目标）
全部零件为 PLA/PETG 打印件（见各方案 BOM.csv 与 MASTER_PARTS_BOM.csv，"打印/外购"列均为"打印"）。
无电机、导轨、铝型材、轴承、丝杆等工程件需求 —— 本轮为缩比机械原理演示，非整机性能验证。

## 条件性外购建议（仅在 L4 试件失败时启用，需采购 Agent 评估）
| 触发条件 | 建议物料 | 规格 | 用途 | 数量级 |
|---|---|---|---|---|
| CP-CLIP 试件卡圈保持力不足/易裂 | 金属 E 形卡圈 | Ø4.4 / Ø3.4 / Ø2.5 槽用 | 销轴轴向保持 | 各 ~30 |
| 打印销 Ø5/Ø4 剪切/磨损不足 | 标准圆柱销 | Ø5×28/34, Ø4×16/18 | 转动副 | 各 ~10 |
| 滑槽磨损过快 | 无（改打印参数/材料） | — | — | — |

**本 Agent 不下单、不询价、不选商家**；以上仅为接口建议，由采购 Agent 转化为采购计划。
BOM 版本: **R1-V6.1**（最终接口 BOM，供采购 Agent 核对）；设计调整导致零件变化时更新 BOM 版本并通知采购 Agent。

## 共享件提示
BASE/BED 几何在 F09_L82/F07/SCZ 间完全相同（MASTER_PARTS_BOM 已去重合并数量），
采购/打印备料时按 MASTER 数量计，不要按各方案 BOM 简单相加。实际打印总量见 PRINT_PLAN 耗材口径节。
"""
    (ROOT / "PURCHASE_INTERFACE.md").write_text(txt, encoding="utf-8")
    print("PURCHASE_INTERFACE written")


def write_scale_justification():
    master = list(csv.DictReader((ROOT / "MASTER_PARTS_BOM.csv").open(encoding="utf-8-sig")))
    dedup = sum(float(r["预计耗材质量_g"]) * int(r["数量"]) for r in master)
    txt = f"""# 缩比选择依据与耗材核算（回应 P1-3）

## 1. 为什么选 1:2（而非 1:3 / 1:5）
brief 建议从 1:5 探索、SCZ 可 1:4，但明确"比例非死约束，按打印工艺/观察尺度/关节可装配性确定"。
本轮选 **连杆几何统一 1:2**，依据如下（关键在关节可打印性与手动演示）：

| 量 | 全尺寸 | 1:2 (选用) | 1:3 | 1:5 |
|---|---|---|---|---|
| X 臂长 | 215 | 107.5 | 71.7 | 43.0 |
| 立柱高 | 345 | 172.5 | 115.0 | 69.0 |
| 抬升行程 F09 | 82 | 41.0 | 27.3 | 16.4 |
| 剪叉臂半长 | 154 | 77.0 | 51.3 | 30.8 |
| 根部铰销（局部放大后） | Ø6 | **Ø5** | Ø4 | Ø3 |
| 剪叉销（局部放大后） | — | **Ø4** | Ø3 | Ø2.5 |

- **关节下限**：FDM 0.4 喷嘴下，可反复拆装且不失稳的打印销轴经验下限约 Ø4–5；转动配合间隙 0.3 mm。
  1:3 时根部销需缩到 Ø4、剪叉销 Ø3，铰耳厚仅 ~2.7 mm，卡圈/叉耳强度与打印成功率明显下降；
  1:5 时销 ≤Ø3、臂仅 43 mm，手指难以捏持演示，关节几乎不可装配。
- **手动演示尺度**：1:2 模型臂 ~108 mm、底座 ~158×174 mm、整机高 ~190 mm，单手/双手可操作，
  铰链与滑块清晰可见，适合课堂现场演示机械原理。
- **打印包络**：1:2 最大件（底座 158×174、立柱 172.5 高）均在 250 mm 安全平台内，无需拆件。
- **运动学保真**：统一 1:2 保持杆长比/铰点距/相位/行程比不变；仅销轴/铰耳/让位槽局部放大（逐条见
  MODEL_LIMITATIONS 与验证报告 §1），不改变自由度与运动路径拓扑。
- 结论：1:2 在"可打印关节 + 可手动演示 + 平台包络"三者间最稳妥。**不强制缩小**；若后续需更省料，
  可评估"精简底座"（见下）而非整体缩比。

## 2. 精简大型底座的可选方案（未实施，供决策）
底座占整套质量的主要部分。可选减料方向（保持机构不变）：
- 底座改镂空/加强筋板（减重 ~30–40%），但需重新做 L1 单实体与刚度方向评估；
- F09/F07/SCZ 共享底座已合并（MASTER 去重），避免重复打印；
- 床支撑墙/塔足等非运动件减薄。
本轮为保证一次装配成功与验证简洁，**保留实心底座**；减料作为 V7 可选项，不在本轮强制。

## 3. 耗材核算（CAD 估算，非真实切片）
- 估算方法：零件实体体积 × 材料密度（PLA 1.24 / PETG 1.27 g/cm³）× 0.60（3 壁+20% 填充近似）。
- **实际打印总量（MASTER 去重）≈ {dedup:.0f} g**；含 20% 余量 ≈ {dedup*1.2:.0f} g。
- 各方案 BOM 直接求和会重复计入共享件（BASE/BED），故大于 MASTER 总量；备料以 MASTER 为准。
- 机时按 15–25 g/h 估算（见 PRINT_PLAN）。**所有数字未跑真实切片**，实机以 Bambu Studio 为准。
- 口径已在 README / PR 说明 / BOM / PRINT_PLAN / 本文件统一。
"""
    (ROOT / "SCALE_JUSTIFICATION.md").write_text(txt, encoding="utf-8")
    print("SCALE_JUSTIFICATION written")


def write_changelog():
    txt = """# R1-V5 → R1-V6 变更对照表

针对独立审查反馈（P0-1/P0-2/P0-3/P1-1/P1-2/P1-3）的逐项修复。V5 问题记录保留于
各方案 VALIDATION/HISTORY/ 与本表，不删除。

| 编号 | 审查问题 | V5 状态 | V6 修复 | 证据 |
|---|---|---|---|---|
| P0-1 | F09 中央 X 臂(y=0)未与龙门(y=±65)形成机械连接 | 臂叉耳在立柱上，臂悬空于 y=0，仅动画对齐 | **零件级 CAD**：立柱叉耳移除(F09)，中横梁 BRG 抬高至 world z142.5–157.5 并加中央叉耳，X 臂真实铰接于 BRG；F07 单柱仍由柱顶叉耳承臂 | L2b 闭合 arm 副径向/轴线误差~0；CAD 孔轴审计 BRG/ARM 孔存在 |
| P0-2 | SCZ 顶横轴 SHT 置于固定 fix_x，顶滑块 SLT 在变化 sx | SHT 不穿过顶滑块 | SHT 改随 sx 移动，始终穿过两顶滑块；复审整条剪叉运动链/左右镜像耦合/平台约束 | L2b sht_slt 刚体相对位姿不变、slide_top 导路偏移~0 |
| P0-3 | 验证缺装配约束闭合检查，仅"2001步无穿透" | 无连接闭合/共线/接口/约束保持检查 | 新增 **L2b**：①连接位置一致②铰链轴线共线③销孔接口④滑块导路保持⑤刚体相对位姿不变⑥全行程闭合误差；并加 **CAD 孔轴审计**(BRepAdaptor 圆柱面) | 各方案 L2b_closure.json：闭合失败 0、孔缺失 0、销孔合格 |
| P1-1 | 源码相对路径错误，不可干净复现 | CAD_SOURCE 内 ROOT 多算一层 | common_r1.deliverable_root() 自动定位(支持 ROUND1_OUT 环境变量)；干净目录复现并比对哈希 | REPRODUCTION_REPORT.md |
| P1-2 | L1 含 4 个不在最新 BOM 的旧销 STL | F09/F07-PIN3-L20, SCZ-PIN3-L20/L26 残留于 L1 | 删除旧销文件；历史 JSON 归档至 VALIDATION/HISTORY/；L1 由当前 STL 重新生成 | L1 与 manifest/STL/3MF/BOM 完全一致 |
| P1-3 | 1:2 依据缺失；耗材口径不一(1059 vs 各方案和) | 无缩比论证；README/PR/BOM 数字口径混用 | SCALE_JUSTIFICATION.md 给出 1:2/1:3/1:5 对比与关节下限论证；统一以 MASTER 去重总量为准，明确**非真实切片** | SCALE_JUSTIFICATION.md / PRINT_PLAN 耗材口径节 |
| 附加 | F08 L 槽抬升/后移相位重叠致根销对角卡滞 | lift(0.20–0.40)与shift(0.28–0.45)重叠 | F08 相位改顺序：抬升0.20–0.40→后移0.40–0.55→后翻0.55–0.95 | L2b root_slot 路径偏移~0 |

## 机构零件变更明细
- **F09 COL**：移除臂叉耳/臂让位槽；bridge 榫孔/让位槽由 z117.5 移至 z132。
- **F09 BRG**：本体抬高至 z129.5–144.5(local)，新增中央臂叉耳(枢轴 16,0,137)+臂锁孔+全高中央让位槽；端榫 z132。
- **F07 COL**：保留柱顶臂叉耳（with_arm_clevis=True）。
- **SCZ kinematics**：SHT 位置 (fix_x→sx, hz+9)。
- **F08 kinematics**：shift/root 相位顺序化。
- 销轴表、BOM、3MF、装配指南、验证报告同步更新。

## 未变事项
- 缩比仍 1:2；纯 PLA/PETG、零新增采购目标；F12 不制造。
- 不做第二轮工程性能验证；不代替采购 Agent 下单。
- L4 试件仍待现场确认（无打印机权限）。
"""
    (ROOT / "CHANGELOG_V5_V6.md").write_text(txt, encoding="utf-8")
    print("CHANGELOG_V5_V6 written")


def main():
    rows = write_boms()
    write_print_plan(rows)
    write_motion_report()
    write_limitations()
    write_assembly_guide()
    write_readme()
    write_purchase_interface()
    write_scale_justification()
    write_changelog()


if __name__ == "__main__":
    main()
