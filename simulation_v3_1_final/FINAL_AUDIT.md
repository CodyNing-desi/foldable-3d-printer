# V3.1 最终修订补丁审计（FINAL_AUDIT）

## 1. 三个 P0 关键缺陷的修复说明

### P0-1：F09 有限元、运动学与碰撞几何统一
- **缺陷**：V3.1 中 F09 FEA 含 215 mm X 悬臂（`0.1207 mm`），但运动与碰撞模型缺少该悬臂，导致收纳比虚低至 `0.445` 且未检出折臂方向干涉。
- **修复**：在 `mechanisms3d.py` 为 F09 补齐 `bridge_beam` + 215 mm `x_arm` + `toolhead`，增设横臂向下折叠铰链（`rot_y(+90°)`，避免向上撞击顶部 `crossbar` `12.95 mm`）；在 `fea3d.py` 为 F09 折臂根部增加有限旋转柔度（`corner_factor=0.70`），与理想刚性锁紧分别报告。
- **结果对照**：F09（`lift=85, shift_x=0, arm_fold=1`）3D 收纳比由 `0.445` 修正为 **`0.740`**；FEA Y 向挠度由 `0.1207 mm` 修正为 **`0.1252 mm`**（理想刚性 `0.1004 mm`，870 DOFs）；不折臂则穿透底座 **`38.2047 mm`（`FAIL`）**。

### P0-2：彻底修复连续扫掠碰撞漏检
- **缺陷**：(1) 反例 A：旧算法用端点 AABB 做宽相剔除且线性插值刚体中心，导致 0°→150° 旋转扫掠漏检 90° 处障碍物；(2) 反例 B：旧算法未检查两个运动 OBB 之间的相对连续扫掠。
- **修复**：在 `geometry3d.py` 实现 `swept_obb_vs_obb`：
  - 采用 **Chasles 螺旋/圆弧刚体位姿插值**（`_screw_interp_pose`）与 SO(3) 测地旋转插值；
  - 按位移上界（`step_bound_mm=2.0 mm`）与转角上界（`angle_bound_deg=3.0°`）双重自适应细分；
  - 每个子步对双方 OBB 叠加半步位移 + 圆弧矢高保守余量 `0.5*disp/n_sub + r*(1 - cos(dtheta/(2*n_sub)))`；
  - 对全路径 `moving vs fixed`、`moving vs moving` 及终态 `extra` 附件全量检查，明确输出 `PASS / FAIL / UNRESOLVED`。
- **反例验证**（`tests/test_p0_regressions.py`）：
  - 反例 A（0°→150° 旋转撞击 90° 障碍物）：旧夹具返回 `0.0`（漏检）→ 修复后返回 **`FAIL`（穿透 > 2.0 mm）**。
  - 反例 B（双运动 OBB X=0↔100 相向穿越）：修复后返回 **`FAIL`（穿透 > 5.0 mm）**。
  - 超出 `max_substeps` 上限区间返回 **`UNRESOLVED`**，不伪标为 `PASS`。

### P0-3：独立交付与一键复现
- 移除对外部 `simulation_v3/` 与 `simulation_v3_1/` 的导入依赖；将旧缺陷对比写为 `test_p0_regressions.py` 内置夹具；提供 Linux/macOS (`run_all.sh`)、Windows (`run_all.bat`)、`requirements.txt` 与 `SHA256SUMS.txt`。

## 2. 仍然存在的模型限制
- 连续扫掠基于刚体 OBB 保守包络，不包含弹性变形引起的动态间隙变化或柔性线缆垂度；
- 铰链/锁紧柔度折减（`0.55` / `0.70`）与库伦摩擦系数为工程假设，需由线下首批台架实测标定。
