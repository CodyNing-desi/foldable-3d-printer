# 源码干净复现核查报告（REPRODUCTION_REPORT）

方法：将各方案自包含 CAD_SOURCE 复制到全新临时目录，设 ROUND1_OUT 指向独立空输出目录，
用同一 venv 解释器运行 `build_all.py <cand>`，逐文件比对再生成 STL/STEP 与交付件的 SHA256。

| 方案 | 退出码 | 哈希一致 | 不一致 | 缺失 | 结论 |
|---|---|---|---|---|---|
| F09_L82 | 0 | 39 | 0 | 0 | PASS |
| F07 | 0 | 29 | 0 | 0 | PASS |
| SCZ | 0 | 35 | 0 | 0 | PASS |
| F08_OPTIONAL | 0 | 21 | 0 | 0 | PASS |

**总体: PASS — 源码可干净复现，输出与交付件一致**。

注：STL 由 build123d/OCP 确定性 tessellation 生成，逐字节一致。STEP 的实体编号/时间戳随 OCP 会话
历史变化（非几何差异），故按**几何内容**比对：重导入后体积/包围盒/实体数一致即判一致。