# 可复现性说明 (REPRODUCIBILITY)

- **Python 环境**：Python 3.10+，`numpy>=1.26.0`, `scipy>=1.11.0`, `matplotlib>=3.8.0`。
- **V3.2.1 一键复现**：进入 `simulation_v3_2_1/` 执行 `sh run_all.sh`（Linux/macOS）或 `run_all.bat`（Windows），将自动运行 A–H 全部 8 组回归测试与全候选连续碰撞/FEA 复核。
- **校验和**：`tools/verify_payload.py` 校验载荷全部文件的 SHA-256；`tools/test_sync_safety.py` 可在隔离临时 Git 仓库完整复现 Dry Run、原有 `docs/` 保护、冲突中止与幂等性测试。
