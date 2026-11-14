# 仿真版本演进历史 (VERSION_HISTORY)

| 版本 | 阶段定位 | 核心改动 |
| :--- | :--- | :--- |
| `simulation/` (Round 1) | 初筛与概念 CAD | F01–F14 与 SCZ 共 15 套机构 2.5D 简化初筛（GitHub 基线，禁止覆盖） |
| `simulation_v2/` | 第二轮高保真仿真 | 修复工作空间约束默认通过缺陷，引入 3D 参数化几何与多目标优化 |
| `simulation_v3/` | 第三轮虚拟终审 | 统一运输包络与附件摆放优化，建立双柱/剪刀/伸缩真实机构模型与 FEA |
| `simulation_v3_1/` | V3.1 补充纠错 | 为 F09 FEA 补齐 215 mm X 悬臂载荷，修正 F07 `lift=75` 参数与 SCZ 连续停靠 |
| `simulation_v3_1_final/` | V3.1 最终修订补丁 | 统一 F09 FEA 与运动学中的 215 mm 折叠 X 臂，升级 Chasles 旋转扫掠碰撞检查 |
| `simulation_v3_2/` | V3.2 连续碰撞修复 | 升级自适应二分连续碰撞认证，通过 A–E 回归反例（存在三点采样上界与 F09 判定不一致缺陷） |
| `simulation_v3_2_1/` | V3.2.1 最终验收补丁 | 废除三点采样上界，改用解析运动上界 `BoundedTrajectory`（通过 A–H 反例）；修正同步脚本逐文件合并；统一 F09 筛选一致性 |
