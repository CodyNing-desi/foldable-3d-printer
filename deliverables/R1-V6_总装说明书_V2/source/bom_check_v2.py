"""Generate V2 version/BOM closure report from actual BOM CSVs and PPT usage map."""
import csv
from pathlib import Path

ROOT = Path(r"G:\我的云端硬盘\ROUND1_DEMO_CAD")
OUT = Path(__file__).parent

USAGE = {
    "F07": {
        "F07-BASE": (1, "14"), "F07-BED": (1, "14（可选件）"), "F07-TWR": (1, "14"),
        "F07-CAP": (1, "16"), "F07-CAR": (1, "15"), "F07-COL": (1, "17"), "F07-ARM": (1, "18"),
        "F07-PIN5-L34": (2, "17×1+18×1"), "F07-CLIP5": (2, "17×1+18×1"),
        "F07-PIN3-L34": (2, "17×1+18×1，19移插"), "F07-PIN3-L26": (2, "19×2"),
        "F07-PIN3-L14": (6, "14×4+16×2"),
        "F07-CLIP3": (10, "14×4+16×2+17×1+18×1+19×2"),
    },
    "F09_L82": {
        "F09-BASE": (1, "21"), "F09-BED": (1, "21（可选件）"), "F09-TWR": (2, "21"),
        "F09-CAP": (2, "25"), "F09-CAR": (2, "22"), "F09-COL": (2, "24"),
        "F09-SYNC": (1, "23"), "F09-XBAR": (1, "26"), "F09-BRG": (1, "27"), "F09-ARM": (1, "28"),
        "F09-PIN5-L34": (3, "24×2+28×1"), "F09-CLIP5": (3, "24×2+28×1"),
        "F09-PIN3-L34": (3, "24×2+28×1，29移插"), "F09-PIN3-L26": (4, "29×4"),
        "F09-PIN3-L14": (12, "21×8+25×4"),
        "F09-CLIP3": (27, "21×8+23×4+24×2+25×4+26×2+27×2+28×1+29×4"),
        "F09-PIN3-L18": (6, "23×4+27×2"), "F09-PIN3-L22": (2, "26×2"),
    },
    "SCZ": {
        "SCZ-BASE": (1, "31"), "SCZ-BED": (1, "31（可选件）"), "SCZ-POST": (2, "31"),
        "SCZ-ARM": (4, "32×2+34×2"), "SCZ-SLB": (2, "32"), "SCZ-SLT": (2, "35"),
        "SCZ-SHB": (1, "33"), "SCZ-SHT": (1, "35"), "SCZ-PLAT": (1, "36"),
        "SCZ-PIN4-L18": (4, "32×2+36×2"), "SCZ-PIN4-L16": (6, "34×4+35×2"),
        "SCZ-CLIP4": (14, "32×2+33×2+34×4+35×4+36×2"),
        "SCZ-PIN3-L24": (2, "37×2"), "SCZ-PIN3-L13": (4, "31×4"),
        "SCZ-PIN25-L10": (4, "33×2+35×2"), "SCZ-CLIP3": (6, "31×4+37×2"),
    },
}

lines = [
    "# V2 版本与 BOM 闭环核对报告",
    "",
    "核对日期：2026-11-17。对象：`R1-V6_乐高风总装说明书_V2.pptx`（41页）。",
    "",
    "## 一、P0 版本事实核查",
    "",
    "| 问题 | 核查结果 |",
    "|---|---|",
    "| V6.1 是否真实完成建模？ | **是，本地完成**。可拆顶盖 CAP 已建模并导出；L1–L3 已重跑通过。 |",
    "| CAP 的 STL/STEP/参数化源码是否存在？ | **存在**：F07/F09 的 CAP.stl、CAP.step；`build_gantry.py::build_cap()`；相关运动学、验证、BOM 源码均在。 |",
    "| V6.1 是否仅本地、未同步 GitHub？ | **是**。GitHub `round1-demo-cad` 当前仍为 `d35cbd1eacfa9908aef302b009610c5dbc03d15a`（R1-V6）。 |",
    "| 顶盖是否已实际打印？ | **无法确认已打印，按未打印处理**。无 CAP 实物或打印验收记录；不得宣称实物可装已验证。 |",
    "| CAP 新增后 TWR/CAR 接口是否同步修改？ | **TWR 已改**：去除一体顶盖、新增 z65 销孔；**CAR 几何未改**，其闭口轴套装配路径因顶盖可拆而成立。 |",
    "| BOM 与装配指南是否更新？ | **本地已更新**：逐方案 BOM、MASTER_PARTS_BOM、PRINT_PLAN、ASSEMBLY_GUIDE、README、验证报告均含 V6.1。 |",
    "",
    "**采用基准**：V2 以本地 V6.1 CAD 为几何基准，同时显式标注“未同步 GitHub、未实物验收”。V6 一体塔与 V6.1 可拆顶盖不得混装。",
    "",
    "## 二、V6.1 CAD 级验证结果",
    "",
    "- F07：13件，L1 异常0；2001步全行程穿透0、未解析0；L2b 6副闭合失败0、孔缺失0、销孔间隙全合格。",
    "- F09：18件，L1 异常0；2001步全行程穿透0、未解析0；L2b 15副闭合失败0、孔缺失0、销孔间隙全合格。",
    "- 扫掠凸包：F07 既有2项与新增 ARM×CAP 1项均为保守相交，经相位内2001步细化采样穿透0；F09全清。",
    "- 以上仅证明 CAD 几何可装/可动，**不等于实物配合、保持力与全行程验收通过**。",
    "",
    "## 三、BOM 闭环核对",
    "",
    "验收口径：每个正式零件在步骤中使用，或明确标为可选件；锁销在0°/90°孔间移插，不重复消耗。",
    "",
    "| 方案 | 零件编号 | BOM数量 | PPT累计用量 | 差异 | 步骤页 | 材料 | 状态 |",
    "|---|---|---:|---:|---|---|---|---|",
]

errors = []
for cand in ("F07", "F09_L82", "SCZ"):
    with (ROOT / cand / "BOM.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        pid = r["零件编号"]
        bq = int(r["数量"])
        uq, pages = USAGE[cand].get(pid, (0, "未使用"))
        optional = "可选" in r["是否必须"]
        ok = bq == uq
        if not ok:
            errors.append((pid, bq, uq))
        lines.append(f"| {cand} | {pid} | {bq} | {uq} | {'一致' if ok else '需修订'} | {pages} | {r['材料']} | {'通过' if ok else '需修订'} |")

lines += [
    "",
    f"**闭环结论：{len(errors)} 项差异。**" + ("全部一致。" if not errors else str(errors)),
    "",
    "专项复核：",
    "- F07 塔足 PIN3-L14×4 + 顶盖×2 = 6，与 BOM 一致；未只加总数而不分位置。",
    "- F09 塔足 PIN3-L14×8 + 两顶盖×4 = 12，与 BOM 一致。",
    "- F09 SYNC 使用 PIN3-L18×4（每滑座2根），与指南及 BOM 一致；滑座其余凸台孔未安排销轴，不做虚构消耗。",
    "- SCZ 臂A底/顶各2根 PIN4-L18，共4；臂B底2+臂B顶2+中心铰2根 PIN4-L16，共6；第35页已补回上版漏列的臂B顶2根。",
    "- SCZ CLIP4：10个关节销卡圈 + SHB/SHT轴端4个 = 14，与 BOM 一致。",
    "- SCZ PIN25-L10×4 为上下横轴横销，无独立 Ø2.5 卡圈；实际为压入防转结构，保持力列为待验证，未虚构防脱卡圈。",
    "- 材料按 BOM 原样保留：结构件 PLA、销/卡圈/SCZ运动小件 PETG，未出现 PLA/PETG 错写。",
    "",
    "## 四、GitHub 同步清单（未执行推送，不覆盖 R1-V6）",
    "",
    "建议新建分支或 PR（例如 `round1-demo-cad-v6-1`），审查后合并；不得直接覆盖 `d35cbd1`。需同步：",
    "",
    "1. 参数化源（各方案 CAD_SOURCE 同步副本）：`common_r1.py`、`build_gantry.py`、`kinematics_r1.py`、",
    "   `validate_r1.py`、`joints_r1.py`、`build_all.py`、`make_docs.py`、`package.py`。",
    "2. F07/F09：TWR 与 CAP 的 STL/STEP；各装配状态 STEP/STL；`VALIDATION/parts_manifest.json`、",
    "   L1/L2/L2b 结果；3MF；逐方案 BOM.csv；ASSEMBLY 姿态图。",
    "3. 根级：`README.md`、`ASSEMBLY_GUIDE.md`、`MODEL_LIMITATIONS.md`、`MOTION_VALIDATION_REPORT.md`、",
    "   `CHANGELOG_V6_1.md`、`MASTER_PARTS_BOM.csv`、`PRINT_PLAN_5_MACHINES.md`、",
    "   `PURCHASE_INTERFACE.md`、`build_manifest.json`、`SHA256SUMS.txt`。",
    "4. 新打包的 `ROUND1_DEMO_CAD.zip`（V6.1）。V6 原始包已备份，未删除。",
    "",
    "## 五、尚未解决的工程问题",
    "",
    "1. **CAP 未打印、装配未实测**：可拆顶盖的套装间隙、销接保持与滑座全程手感待现场验收。",
    "2. **V6.1 未同步 GitHub**：现场若按公开分支打印将得到 V6 一体塔，必须先核对版本。",
    "3. **SCZ PIN25-L10 防脱待验证**：横销无独立卡圈，靠压入配合；松脱需改结构或增加可靠保持。",
    "4. **L4 试件未实测**：正式孔径/槽宽未冻结，不能直接批量宣称配合合格。",
    "5. **三套全行程未实物验收**：打印完成不等于装配成功；验收表未实测项保持空白。",
    "6. **局部销轴插入方向为 CAD 建议**：主转轴/锁销可按实际叉耳开口反向安装，以尾槽卡圈可操作、受力合理为准，不改变数量闭环。",
    "",
    "原始 V6 快照：`C:\\Users\\94823\\r1v6-ppt-build\\ROUND1_DEMO_CAD_v6_backup.zip`。",
]
(OUT / "V2_版本与BOM核对报告.md").write_text("\n".join(lines), encoding="utf-8")
print("report written; differences:", errors)

# separate changelog and issue list requested by user
(OUT / "未解决工程问题清单.md").write_text("\n".join(lines[lines.index("## 五、尚未解决的工程问题"):]), encoding="utf-8")
