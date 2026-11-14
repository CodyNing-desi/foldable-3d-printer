# Foldable 3D Printer Research

可折叠 3D 打印机方案的研究、点评、技术规划与开放项目参考资料。

## 当前任务

折叠是已确定的工程任务。围绕一台具体打印机，研究其龙门／立柱及关联杆件如何折叠、收纳、展开、锁紧和恢复打印；首版不叠加 AI、五轴、长打印或自动展开。

**先读：`docs/planning/现有准备工作总结.md`。**

## 当前选型结论（V3.2.1，2026-11-14）

**以 [`docs/simulation_history/CURRENT_DECISION.md`](docs/simulation_history/CURRENT_DECISION.md) 和 [`simulation_v3_2_1/LINEUP_DECISION_V3_2_1.md`](simulation_v3_2_1/LINEUP_DECISION_V3_2_1.md) 为准。** 线下实体实验资格上限为 3 套主候选 + 1 套备选：

| 候选 | 参数 | 资格 | 收纳比 | 10 N Y 向挠度 | 最小认证净距 |
| :--- | :--- | :--- | ---: | ---: | ---: |
| **F09_L82**（主候选 1） | `lift=82.0, shift=0, arm_fold=1` | Conditional Go | 0.786 | 0.1252 mm | 0.023 mm |
| **F07**（主候选 2） | `lift=75.0, shift=0, arm_fold=1` | Conditional Go | 0.751 | 0.8166 mm | 0.021 mm |
| **SCZ**（主候选 3） | `arm=154.0, h_fold=45.0` | Bench-only，仅台架机构验证 | 0.503 | — | 0.010 mm |
| **F08**（备选） | `lift=25/30, shift=-75` | Fallback，折叠最长边 897.0 mm | 0.616 | — | — |
| **F12** | `overlap=52, outer=60` | **No-Go，淘汰归档** | — | — | — |

相对第一轮的关键变化：

- **F12 由"稳健推荐"改为 No-Go**：6 周研发周期内精密三级伸缩导轨的制造、晃动与卡滞风险不可控，不进入实物制作。
- **F09 进入主候选**：`lift=85` 时含 215 mm 折叠 X 臂与附件的收纳比为 `0.802 > 0.800`（筛选 FAIL）；V3.2.1 在**门槛不放宽**的前提下把 `lift` 几何微调至 `82.0 mm`，收纳比降至 `0.786`（PASS）。
- **F09 刚度纠偏**：V3 误把 10 N 载荷加在横梁中心（`0.030 mm`），补齐 215 mm X 向悬臂末端载荷后为 `0.1252 mm`。
- **连续碰撞认证纠偏**：V3.2 的三点采样位移上界会把 `x(t)=50·sin(2πt)` 这类真实穿透误判为 PASS；V3.2.1 改用解析运动上界契约 `BoundedTrajectory`，缺少可信上界的任意 `Callable` 强制返回 `UNRESOLVED`。交付记录为 A–H 共 8 组回归反例全部通过（`simulation_v3_2_1/tests/test_v3_2_1_collision_suite.py`）。
- **微米级净距不是安全余量**：`0.010–0.023 mm` 的最小认证净距只证明简化 OBB 几何模型无碰撞，**不构成覆盖真实加工与装配公差的工程安全余量**。

证据边界：简化 OBB 碰撞、假定材料与关节柔度、局部等效梁有限元；**没有整机/铰链 FEA、多体动力学或实机验证**。全部结论属于线上模型筛选与台架实验决策资料，**不是实机性能认证**。

V3.2.1 一键复现：进入 `simulation_v3_2_1/` 执行 `sh run_all.sh`（Windows 用 `run_all.bat`），自动运行 A–H 回归测试与全候选连续碰撞／FEA 复核。环境要求 Python 3.10+、`numpy>=1.26.0`、`scipy>=1.11.0`、`matplotlib>=3.8.0`。

关键入口：

- [当前冻结选型决策](docs/simulation_history/CURRENT_DECISION.md)
- [V3.2.1 入围名单与逐项台架验证内容](simulation_v3_2_1/LINEUP_DECISION_V3_2_1.md)
- [V3.2.1 最终报告](simulation_v3_2_1/FINAL_REPORT_V3_2_1.md)
- [版本演进历史](docs/simulation_history/VERSION_HISTORY.md)
- [关键结论纠偏记录](docs/simulation_history/RESULT_CORRECTIONS.md)
- [可复现性说明](docs/simulation_history/REPRODUCIBILITY.md)

### 第一轮基线结论（历史保留，已被取代）

第一轮 `simulation/` 完成 F01–F14 与剪刀式 Z 轴 SCZ 共 15 套机构的统一参数化初筛、优化和可行性筛选，当时结论为稳健推荐 F07/F12、探索型第三项 SCZ、工程备选 F08；F04 在加入槽轨、滚轮和导向约束后优化无可行解。名义方案完成 201/501/1001 姿态稳定性检查，优化候选最高完成 5001 姿态复验；30 项测试、138/138 交付检查通过，一键复现 `bash simulation/run_all.sh`。

**该结论已被 V2–V3.2.1 取代（尤其 F12 现为 No-Go），仅作可追溯历史保留，不再作为当前选型依据。** 第一轮全部文件原样保留：

- [第一轮仿真与筛选总报告](simulation/REPORT.md)
- [第一轮全实验过程复盘与推荐变化](simulation/PROCESS_REVIEW.md)
- [第三项选择理由](simulation/verification/THIRD_OPTION_DECISION.md)
- [实物验证计划](simulation/verification/PHYSICAL_VALIDATION_PLAN.md)
- [实物材料清单](simulation/verification/third_option_bom.csv)（48 项，概念估算，不是报价）

第一轮成果在 GitHub `main` 与 `feature/full-mechanism-simulation` 分支；V2–V3.2.1 历史归档在 `sync/v2-to-v3_2_1` 分支，经 [PR #1](https://github.com/CodyNing-desi/foldable-3d-printer/pull/1) 提交待审查合并。尚未把任何仿真候选当作实机可行产品。

## 文件导航

### 研究资料 `docs/research/`

- `可折叠3D打印机_案例与现有做法.md`：案例、机构谱系、现有做法与证据边界。
- `折叠方向补充案例.md`：当前八条折叠方向的直接案例与证据缺口。
- `算法基础与技术路线.md`：运动学、固件、校准与五轴代码入口。
- `机械图纸与打印床处理.md`：Trident／Prusa／A1 结构、板材取件与测量清单。
- `研究笔记.md`：逐条来源摘录与综合发现。

### 执行规划 `docs/planning/`

- `现有准备工作总结.md`：已完成工作、文件分类和未完成事项。
- `技术规划.md`：机构、电控、算法、验证与课程节点。
- `下一轮工作部署.md`：成熟项目做法、角色分工、实验目录和逐项验收。
- `虚拟端可行性验证准备.md`：各路线的模型、输入、失败条件、工具与结果要求。
- `虚拟验证_根部翻折演示.md`：A1 mini 简化侧视模型的碰撞、避让与收纳高度参数化结果。

### 手绘任务 `docs/drawing/`

- `手绘图任务与绘图指南.md`：12 张设计手绘的内容、分工、验收和命名。

### 仿真版本归档 `simulation_v2/` … `simulation_v3_2_1/`

六轮历史工程资料按原相对路径完整归档，含源码、配置、结果 JSON/CSV、概念 CAD（STL/OBJ）、图表与逐版报告。**旧版中被后续纠正的结论原样保留，未作改写**；纠偏集中在 `docs/simulation_history/RESULT_CORRECTIONS.md`。

| 目录 | 阶段定位 | 文件数 |
| :--- | :--- | ---: |
| [`simulation_v2/`](simulation_v2/REPORT_V2.md) | 第二轮高保真仿真：修复工作空间约束默认通过缺陷，引入 3D 参数化几何与多目标优化 | 43 |
| [`simulation_v3/`](simulation_v3/REPORT_V3.md) | 第三轮虚拟终审：统一运输包络与附件摆放优化，建立双柱／剪刀／伸缩真实机构模型与 FEA | 41 |
| [`simulation_v3_1/`](simulation_v3_1/REPORT_V3_1.md) | V3.1 补充纠错：F09 补齐 215 mm X 悬臂载荷，修正 F07 `lift=75` 与 SCZ 连续停靠 | 19 |
| [`simulation_v3_1_final/`](simulation_v3_1_final/FINAL_REPORT.md) | V3.1 最终修订补丁：统一 F09 FEA 与运动学的 215 mm 折叠 X 臂，升级 Chasles 旋转扫掠碰撞检查 | 18 |
| [`simulation_v3_2/`](simulation_v3_2/FINAL_REPORT_V3_2.md) | V3.2 连续碰撞修复：自适应二分连续碰撞认证，通过 A–E 回归反例（仍存在三点采样上界缺陷） | 21 |
| [`simulation_v3_2_1/`](simulation_v3_2_1/FINAL_REPORT_V3_2_1.md) | **V3.2.1 最终验收补丁（当前结论）**：解析运动上界 `BoundedTrajectory`，通过 A–H 反例，统一 F09 筛选一致性 | 18 |
| [`docs/simulation_history/`](docs/simulation_history/CURRENT_DECISION.md) | 版本沿革、结论纠偏、可复现性说明与当前冻结决策 | 4 |

### 数据与证据

- `data/cases.csv`：19 条产品、原型、概念和专利案例。
- `data/drawing_checklist.csv`：12 张手绘图的进度跟踪。
- `data/virtual_validation_parameters.csv`：虚拟验证所需参数、单位、来源和状态。
- `teacher_feedback/`：点评整理、带时间戳转写和 JSON 分段。
- `evidence/进度对比_01.png`：相较开题展板的新增准备工作与未完成项。
- `evidence/进度对比_01.md`：对照图的文字说明、来源与生成记录。
- `external/`：26 个上游项目的快照、导读、commit 与许可证记录。
- `scripts/virtual_fold_checks.py`：铰链扫掠、剪刀映射和翻转力矩的方法自检。
- `simulation/`：**第一轮基线（结论已被 V3.2.1 取代，文件原样保留）**——F01–F14 与剪刀式 Z 轴的全方案 L1/L2 仿真、局部梁 L3 有限元、NSGA-II、原始数据、动画、概念 CAD、过程复盘、第三项决策与实物材料清单；先读 `simulation/REPORT.md`，再看 `simulation/PROCESS_REVIEW.md`。
- `simulation_v2/` … `simulation_v3_2_1/`：第二轮至 V3.2.1 的六轮历史归档，共 160 个文件；当前结论见 `simulation_v3_2_1/`，沿革与纠偏见 `docs/simulation_history/`。
- `deliverables/折叠收纳方案_完善版.pptx`：保留队友原 34 页，追加证据边界、同尺度示意和根部关节验证 3 页。
- `deliverables/折叠收纳与模块化_完善版.pptx`：保留新版 47 页，追加主线分层、M01 同尺度示意和四方向共同验证 3 页。
- `task_plan.md`：工作过程、错误和验证记录。

## 证据与版权边界

- 专利、概念和厂商宣称不等于已验证产品。
- 上游项目保留原许可证、来源链接和 commit；没有明确许可证的项目只作私有研究参考。
- 本仓库自 2026-11-13 起公开，不包含 PaperLoop 旧访谈音频或旧方向完整归档。
- 未找到明确许可证的上游快照已移至本地参考区；公开仓库只保留其链接与元数据。
- 老师点评为自动转写后整理，不确定项已标注。
- 历史仿真版本（`simulation/`、`simulation_v2/` … `simulation_v3_2/`）中被后续纠正的结论原样保留作追溯，**不代表当前选型**；当前选型只以 `docs/simulation_history/CURRENT_DECISION.md` 为准。
- 当前尚无实机测量、真实手绘、折叠样机和恢复打印数据，不把计划写成已完成原型。
