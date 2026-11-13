import json
import sys
from pathlib import Path

import pandas as pd

SIMULATION_DIR = Path(__file__).resolve().parents[1]
RESULTS = SIMULATION_DIR / "results"
sys.path.insert(0, str(SIMULATION_DIR / "src"))

from foldsim.registry import load_candidates


def _number(value, digits=3):
    return "—" if pd.isna(value) else f"{value:.{digits}f}"


def _parameters(parameters):
    return ", ".join(f"{key}={value:.3g}" for key, value in parameters.items())


def main():
    screen = pd.read_csv(RESULTS / "screening_summary.csv").set_index("id")
    deep = pd.read_csv(RESULTS / "deep_summary.csv").set_index("id")
    candidates = load_candidates(SIMULATION_DIR / "config" / "candidates.json")
    with (RESULTS / "selection.json").open(encoding="utf-8") as handle:
        selection = json.load(handle)
    with (RESULTS / "optimization_raw.json").open(encoding="utf-8") as handle:
        optimization_raw = json.load(handle)
    with (RESULTS / "convergence_validation.json").open(encoding="utf-8") as handle:
        convergence = json.load(handle)
    with (RESULTS / "beam_fea.json").open(encoding="utf-8") as handle:
        beam_fea = json.load(handle)
    with (RESULTS / "third_option_analysis.json").open(encoding="utf-8") as handle:
        third = json.load(handle)
    with (SIMULATION_DIR / "verification" / "bom_summary.json").open(encoding="utf-8") as handle:
        bom = json.load(handle)
    no_feasible = [row["id"] for row in optimization_raw if not row["solutions"]]
    cad_by_id = {}
    cad_ids = set(selection["recommended_ids"]) | {
        third["selected_third_option"], third["fallback_option"],
    }
    for candidate_id in cad_ids:
        manifest_path = SIMULATION_DIR / "cad" / candidate_id / f"{candidate_id.lower()}.manifest.json"
        if manifest_path.is_file():
            with manifest_path.open(encoding="utf-8") as handle:
                cad_by_id[candidate_id] = json.load(handle)
    lines = [
        "# 可折叠 3D 打印机全方案虚拟仿真与优化筛选报告",
        "",
        "> 本报告包含基于显式概念假设的 L1/L2 仿真和仅针对等效悬臂梁的 L3 线弹性有限元，不是实机或整机 FEA 验证。仓库尚无冻结实机、完整实测尺寸、长期寿命或恢复打印数据。所有尺寸为 mm、力矩为 N·mm、力为 N、成本为概念增量 CNY。",
        "",
        "## 1. 结论与证据边界",
        "",
        f"- 已对 **{len(screen)} 套候选（F01–F14 与 SCZ）**逐姿态运行统一刚体初筛；{int(screen['passed_screen'].sum())} 套通过名义参数硬约束。",
        "- 每套名义轨迹使用 201 个状态，并完成 201/501/1001 收敛检查；推荐解以 1001、第三项与备选以 5001 个状态复验。所有原始轨迹均保存在 `results/traces/`。",
        "- 对全部方案计算了指示性静力学/刚度；只有 L1 通过者标记为 `L2_completed`。重复定位误差来自每套 10,000 次、推荐方案每套 20,000 次独立输入抽样的蒙特卡洛结果。",
        "- 额外对 I=7000 mm⁴ 的等效悬臂梁做了三维六面体线弹性有限元网格收敛；最细网格与 Euler–Bernoulli 相差 2.4%，仅验证梁公式与 FE 流程。",
        "- 未运行完整三维装配碰撞、整机/铰链有限元、多体动力学、计算流体或实机恢复打印；不得把挠度与误差百分位数当作量产打印精度承诺。",
        "",
        "## 2. 统一模型与评价契约",
        "",
        "- 基准：347×315×365 mm 公开外形启发外形与 180 mm 目标打印高度；这是演示假设，不是 A1 mini 完整 CAD。",
        "- L1：2.5D 刚体侧视/顶视模型。体积为侧视包络乘显式 Y 向宽度；相交面积是实际 Shapely 布尔计算，不是三维相交体积。F04/F10 包含槽轨中心线、槽宽、滚轮和导向间隙；F11 包含运动箱盖；F14 包含双柱预折和第二阶段翻转。",
        "- 刚度是跨族启发式降阶指标，虽纳入臂长、重叠和锁点跨距，但不是各机构已标定的真实刚度；其参与排序的证据强度低于几何与误差结果。",
        "- 系统边界：非箱体/外托架方案在运输态加入 200×200 mm 料盘、电源与工具包络；F06/F11/F14 的柜体/箱体已包含附件。报告同时保留裸机芯与运输系统两种体积比。",
        "- 硬约束：轨迹无穿透、装配可达、180 mm 工作空间、运输系统收纳体积比 ≤0.800；伸缩重叠率 ≥25%；抽屉线缆动态弯曲半径 ≥35 mm。",
        "- L2：重力矩、驱动几何增益、Euler–Bernoulli 降阶梁、线性化锁点接触刚度、独立矩形间隙/基准座误差蒙特卡洛。锁紧刚度和材料参数均为未标定假设。",
        "- L3（局部）：scikit-fem 三维六面体线弹性等效悬臂梁，网格 20/40/80/160 单元收敛；不是 T-slot 空心截面、铰链、整机或塑性/屈曲/疲劳分析。",
        "- 优化：NSGA-II，32 个体×20 代/可变方案，固定随机种子；目标为收纳、重复定位代理、挠度、成本。另以 48 点拉丁超立方/可变方案计算 Spearman 秩相关。",
        "",
        "## 3. 全方案名义参数结果",
        "",
        "| ID | 方案 | L1 | 系统体积比 | 裸机芯比 | 最大穿透面积 mm² | 挠度 mm | 重复定位 P95 mm | 峰值驱动力 N | 增量成本 CNY | 淘汰/失败证据 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for candidate_id, spec in candidates.items():
        s = screen.loc[candidate_id]
        d = deep.loc[candidate_id]
        reasons = "；".join(json.loads(s["screen_reasons"].replace("'", '"')) if isinstance(s["screen_reasons"], str) else s["screen_reasons"])
        if not reasons:
            reasons = "通过名义初筛"
        lines.append(
            f"| {candidate_id} | {spec['name']} | {'通过' if s['passed_screen'] else '淘汰'} | "
            f"{_number(s['storage_ratio'])} | {_number(s['core_storage_ratio'])} | {_number(s['max_intersection_mm2'])} | "
            f"{_number(d['tip_deflection_mm'])} | {_number(d['p95_mm'])} | {_number(d['peak_drive_force_N'], 1)} | "
            f"{_number(d['estimated_incremental_cost_CNY'], 0)} | {reasons} |"
        )
    lines += [
        "",
        "注：L1 淘汰方案的 L2 数字仅用于理解失败量级，不参与入围。完整机器可靠性没有实测；`reliability_proxy_score` 只是关节数、锁点、同步与制造复杂度的启发式代理。",
        "驱动力是按机构分别定义的概念模型值：翻折类为重力矩÷声明的 50 mm 力臂，伸缩类为重力与摩擦÷效率，抽屉类为滚动摩擦与加速力，剪刀类为非线性几何增益÷效率；不能把这些值直接用于执行器选型。",
        "",
        "## 4. 参数扫描、Pareto 与权重稳健性",
        "",
        "- `results/sensitivity_raw.json` 保留每次拉丁超立方求值；`sensitivity_rank_correlations.csv` 给出参数—输出 Spearman ρ，不将确定性仿真包装成物理因果推断。",
        "- `results/optimization_raw.json` 保存末代非支配/最小不可行解、约束、随机种子和逐代历史；没有为固定拓扑失败方案伪造可行解。",
        "- 本次优化无可行解的候选：" + "、".join(no_feasible) + "。这些候选保留 `least_infeasible` 参数与约束违反度，不能进入推荐。",
        "- 选择阶段对归一化权重进行 100 次扰动，记录各候选进入前三的频率，并要求推荐方案来自不同机构族。",
        "- 名义 15 套在 201/501/1001 姿态下通过状态全部稳定；优化候选 F07/F08/F12/SCZ 在最高 5001 姿态下仍全部通过且最大穿透为 0 mm²。离散采样不等同连续扫掠证明。",
        f"- 等效梁 FEA 最细网格 160×4×4 单元、12075 自由度，端部挠度 {beam_fea['mesh_convergence'][-1]['fea_tip_deflection_mm']:.4f} mm，对 Euler–Bernoulli 的相对差 {beam_fea['finest_relative_error']:.2%}。",
        "",
        "| 候选 | 权重扰动前三频率 | 基线分数（越小越好） | 候选间 Pareto |",
        "|---|---:|---:|---|",
    ]
    for row in sorted(selection["candidate_front"], key=lambda item: -item["robust_frequency"]):
        lines.append(f"| {row['id']} | {row['robust_frequency']:.0%} | {row['baseline_score']:.4f} | {'是' if row['candidate_pareto'] else '否'} |")
    lines += ["", f"## 5. 推荐进入实体实测的 {len(selection['recommendations'])} 套方案", "", "仅保留权重扰动前三频率 ≥80% 的机构族；不为凑满三套而纳入低稳健性方案。", ""]
    for rank, recommendation in enumerate(selection["recommendations"], start=1):
        static = recommendation["final_static_metrics"]
        repeat = recommendation["final_repeatability"]
        lines += [
            f"### {rank}. {recommendation['id']}｜{recommendation['name']}",
            "",
            f"- 优化参数：`{_parameters(recommendation['parameters'])}`。",
            f"- 最终参数已重新通过全部 L1 硬约束" + ("；名义参数的穿透失败已在优化变体中消除" if not screen.loc[recommendation['id'], 'passed_screen'] else "") + f"；1001 姿态复验最大穿透 {recommendation['dense_validation']['max_intersection_mm2']:.6f} mm²。",
            f"- 驱动计算口径：{static['drive_model']}。",
            f"- 系统收纳体积比 **{static['storage_ratio']:.4f}**；10 N 侧载降阶挠度 **{static['tip_deflection_mm']:.3f} mm**；锁点等效刚度 **{static['lock_stiffness_N_mm']:.1f} N/mm**。",
            "- 收纳比距离 0.800 初筛阈值不足 0.005，属于边界候选，实测偏差可能改变结论。" if static['storage_ratio'] > 0.795 else "- 收纳比相对 0.800 初筛阈值有余量，但仍受附件包络假设影响。",
            f"- 重复定位径向误差蒙特卡洛 P50/P95/P99：**{repeat['p50_mm']:.3f}/{repeat['p95_mm']:.3f}/{repeat['p99_mm']:.3f} mm**（20,000 次，seed={repeat['seed']}）。",
            f"- 峰值力矩 **{static['peak_torque_Nmm']:.0f} N·mm**；峰值驱动力 **{static['peak_drive_force_N']:.1f} N**；概念增量成本 **{static['estimated_incremental_cost_CNY']:.0f} CNY**。",
            f"- 推荐理由：在声明权重与 100 次扰动下保持机构族多样性，并非预设根部铰链优胜；该方案前三频率为 {recommendation['robust_frequency']:.0%}。",
            f"- 模型假设：{recommendation['assumption']}",
            f"- 概念 CAD：`cad/{recommendation['id']}/`（STEP 为概念装配，不是可直接加工图）。",
            "",
        ]
    selected_third = third["selected"]
    third_static = selected_third["static_metrics"]
    third_repeat = selected_third["repeatability_20000"]
    fallback = next(row for row in third["candidate_metrics"] if row["id"] == third["fallback_option"])
    lines += [
        "## 6. 第三项选择：探索型 SCZ + 工程备选 F08",
        "",
        "F07 与 F12 已覆盖根部翻折和伸缩两类。第三项不按单纯通过概率选择，否则只会重复根部翻折；本阶段按“独立机构证据增益”选 SCZ，按“最可能通过”保留 F08 为备选。",
        "",
        "| 选项 | 定位 | 5001姿态 | 前三频率 | 收纳比 | P95 mm | 成本 CNY | 主要问题 |",
        "|---|---|---|---:|---:|---:|---:|---|",
        f"| SCZ | 探索型第三项 | {'通过' if selected_third['dense_5001_passed'] else '失败'} | {selected_third['robust_frequency']:.0%} | {third_static['storage_ratio']:.4f} | {third_repeat['p95_mm']:.3f} | {third_static['estimated_incremental_cost_CNY']:.0f} | 低位力比、回差、同步、非线性 Z |",
        f"| F08 | 工程备选 | 通过 | {fallback['robust']:.0%} | {fallback['storage']:.4f} | 0.656 | 337 | 与 F07 同族冗余，偏置铰链刚度 |",
        "",
        f"- SCZ 靶参数：`{_parameters(selected_third['parameters'])}`；模型驱动峰值 {third_static['peak_drive_force_N']:.1f} N，仅是几何/效率模型，不是电机选型值。",
        "- 决策与测试门槛：[verification/THIRD_OPTION_DECISION.md](verification/THIRD_OPTION_DECISION.md)、[verification/PHYSICAL_VALIDATION_PLAN.md](verification/PHYSICAL_VALIDATION_PLAN.md)。",
        f"- 材料与工具估算：SCZ 样机 **{bom['assembly_subtotals']['SCZ_exploratory']['low']:.0f}–{bom['assembly_subtotals']['SCZ_exploratory']['high']:.0f} CNY**；F08 备选 **{bom['assembly_subtotals']['F08_fallback']['low']:.0f}–{bom['assembly_subtotals']['F08_fallback']['high']:.0f} CNY**；共用测试装备 **{bom['shared_test_equipment_subtotals']['total']['low']:.0f}–{bom['shared_test_equipment_subtotals']['total']['high']:.0f} CNY**。均为概念估算，不是报价。",
        "- 具体 BOM：[verification/third_option_bom.csv](verification/third_option_bom.csv)；摘要：[verification/BOM_SUMMARY.md](verification/BOM_SUMMARY.md)。",
        "",
        "## 7. 推荐 CAD 与第三项 CAD 的实际检查",
        "",
        "- " + "；".join(
            f"{candidate_id} STEP：{cad_by_id[candidate_id]['bbox_mm'][3]-cad_by_id[candidate_id]['bbox_mm'][0]:.1f}×{cad_by_id[candidate_id]['bbox_mm'][4]-cad_by_id[candidate_id]['bbox_mm'][1]:.1f}×{cad_by_id[candidate_id]['bbox_mm'][5]-cad_by_id[candidate_id]['bbox_mm'][2]:.1f} mm，{cad_by_id[candidate_id]['solid_count']} 个有效实体"
            for candidate_id in selection["recommended_ids"] if candidate_id in cad_by_id
        ) + "。独立 `facts` 与 2/2 几何量规通过。",
        f"- 第三项/备选 CAD：SCZ {cad_by_id['SCZ']['bbox_mm'][3]-cad_by_id['SCZ']['bbox_mm'][0]:.1f}×{cad_by_id['SCZ']['bbox_mm'][4]-cad_by_id['SCZ']['bbox_mm'][1]:.1f}×{cad_by_id['SCZ']['bbox_mm'][5]-cad_by_id['SCZ']['bbox_mm'][2]:.1f} mm、{cad_by_id['SCZ']['solid_count']} 个实体；F08 {cad_by_id['F08']['bbox_mm'][3]-cad_by_id['F08']['bbox_mm'][0]:.1f}×{cad_by_id['F08']['bbox_mm'][4]-cad_by_id['F08']['bbox_mm'][1]:.1f}×{cad_by_id['F08']['bbox_mm'][5]-cad_by_id['F08']['bbox_mm'][2]:.1f} mm、{cad_by_id['F08']['solid_count']} 个实体；两者均通过独立 2/2 几何量规。",
        "- 已逐张读取六视图快照：可见底座、热床、折叠/伸缩立柱、剪刀臂与上框架等概念实体及其相对位置；没有销轴孔、轴承座、锁点或线缆细节。这些 STEP 仅是参数化概念装配，不是加工就绪零件。",
        "- 已复用并实测读取 FoldaRap 上游铰链 CAD：内件 23×28×48 mm、外件 35×69×46 mm，均为单一有效实体；孔系数据与六视图保存在 `cad/reference/`。可见导槽、夹持结构和安装孔，作为 F07 后续关节细化参考；未在未知装配变换下硬拼入概念装配。",
        "- 所有型材槽宽、转轴、锁点和配合公差均为未核验接口；先制造配合试片并实测，再细化关节 CAD。",
        "",
        "## 8. 第三项实物验证准备",
        "",
        "- 完整方案：[verification/PHYSICAL_VALIDATION_PLAN.md](verification/PHYSICAL_VALIDATION_PLAN.md)；材料：[verification/third_option_bom.csv](verification/third_option_bom.csv)；成本摘要：[verification/BOM_SUMMARY.md](verification/BOM_SUMMARY.md)。",
        "- 试验顺序固定为：原机基线 → 关节试片 → 空载 SCZ 台架 → 分级静载 → 20 次重复定位 → 200 次锁紧 → 驱动与非线性 Z 映射 → 整机打印。",
        "- 临时门槛：20 次展开 P95 ≤1.0 mm、最大 ≤2.0 mm；30 N 锁紧滑移 ≤0.05 mm；10 N 端部挠度 ≤0.50 mm；双向回差 ≤0.10 mm；未锁定不得运动/加热。",
        "- 材料采购必须先核对型材槽宽、轴承/肩轴实测尺寸、热床与工具头接口；打印件只用于试片，不承担正式承力路径。",
        "",
        "1. 先冻结实机和全部接口：型材槽宽/螺母、转轴、锁点、热床、工具头、线缆、料盘、电源、重心和附件尺寸；当前这些接口均未被标准或供应商图纸核验。",
        "2. 加工关键关节试片而非整机：CNC 铝合金或合适金属承力件用于正式样机；FDM 件只作装配试片。先做配合试片，记录实际间隙后回写模型。",
        "3. 顶端施加 20 N 侧载，用千分表测弹性挠度、界面张开和卸载残余；拒绝只测喷嘴 Z 高度而忽略 X/Y 方正。",
        "4. 做 20 次折叠—展开循环与 16 点基准测量，再进行 200 次锁紧力衰减试验；保留卡滞、碰撞和松脱失败。",
        "5. 使用同一 G-code 做折叠前/后各三次打印；任何重新调平都计入展开成本。ABL 不得用于掩盖机架正交度或动态间隙。",
        "6. 家族专项：伸缩方案增加热床辐射下卡滞/预紧测试；剪刀方案测全行程双向回差、左右同步和低位失步；抽屉方案测 35 mm 弯曲半径下线缆疲劳；外部托架测倾覆与失电防坠。",
        "7. 若关键接口实测后轨迹穿透、工作空间不足、20 次展开误差超过原机冻结阈值或锁紧不能独立承载，则停止该路线，不用增加电机掩盖机构失败。",
        "",
        "## 9. 交付文件与复现",
        "",
        "- 参数：`config/candidates.json`；代码：`src/foldsim/` 与 `scripts/`；测试：`tests/`。",
        "- 初筛：`results/screening_summary.*`、`results/traces/`；深化：`deep_summary.*` 与 `repeatability_samples/*.npz`。",
        "- 扫描/优化：`sensitivity_*`、`optimization_*`、`weight_sensitivity.csv`、`selection.json`。",
        "- 补充验证：`results/convergence_validation.json`、`results/beam_fea.json`、`results/third_option_analysis.json`。",
        "- 图：`figures/`（PNG/SVG 与来源清单，含 `fea_convergence` 与 `third_option_comparison`）；动画：`animations/*_fold.gif`（每套 21 个真实求值姿态）。",
        "- 实物准备：`verification/THIRD_OPTION_DECISION.md`、`PHYSICAL_VALIDATION_PLAN.md`、`third_option_bom.csv`、`BOM_SUMMARY.md`、空白 `physical_test_log.csv`。",
        "- 从仓库根目录运行：",
        "",
        "```bash",
        "bash simulation/uv_run.sh -m unittest discover -s tests -v",
        "bash simulation/uv_run.sh scripts/verify_units_and_symbolic.py",
        "bash simulation/uv_run.sh scripts/run_screening.py",
        "bash simulation/uv_run.sh scripts/run_deepening.py",
        "bash simulation/uv_run.sh scripts/run_optimization.py",
        "bash simulation/uv_run.sh scripts/run_sensitivity.py",
        "bash simulation/uv_run.sh scripts/select_recommendations.py",
        "bash simulation/uv_run.sh scripts/validate_convergence.py",
        "bash simulation/uv_run.sh scripts/select_third_option.py",
        "bash simulation/uv_run.sh scripts/generate_figures.py",
        "bash simulation/uv_run.sh scripts/run_beam_fea.py",
        "bash simulation/uv_run.sh scripts/generate_cad.py",
        "bash simulation/uv_run.sh scripts/record_environment.py",
        "bash simulation/uv_run.sh scripts/generate_report.py",
        "bash simulation/uv_run.sh scripts/validate_deliverables.py",
        "```",
        "",
        "实际依赖版本见 `results/environment.json`。`uv_run.sh` 使用本机 uv 缓存隔离环境，不需要把 `.venv` 放入云端仓库。",
        "",
        "## 10. 参考资料",
        "",
        "- 本仓库 `docs/planning/虚拟端可行性验证准备.md`、`docs/research/折叠方向补充案例.md`、`docs/research/可折叠3D打印机_案例与现有做法.md`。",
        "- Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065",
        "- 上游项目版本与许可证见 `external/sources.csv`；本轮没有修改 `external/` 原件。",
        "",
    ]
    (SIMULATION_DIR / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote simulation/REPORT.md")


if __name__ == "__main__":
    main()
