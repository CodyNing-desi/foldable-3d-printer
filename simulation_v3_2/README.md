# simulation_v3_2

V3.2 第三轮虚拟终审连续碰撞修复与线下实物验证定型交付包。

## 目录结构
- `config/candidates_v3_2.json`: 候选机构统一几何与有限元参数配置
- `src/foldsim_v3_2/`: 连续区间碰撞内核 (`geometry3d.py`)、运动学 (`mechanisms3d.py`)、评估器 (`evaluate3d.py`) 与有限元 (`fea3d.py`)
- `tests/test_v3_2_collision_suite.py`: 5 组回归反例（A–E）测试套件
- `scripts/run_v3_2_verification.py`: 候选全量连续碰撞与 FEA 复核及图表生成脚本
- `results/`, `figures/`: JSON/CSV 数值结果与对比图
- `FINAL_REPORT_V3_2.md`, `COLLISION_AUDIT.md`, `LINEUP_DECISION.md`, `MODEL_LIMITATIONS.md`

## 一键复现
```sh
sh run_all.sh
```
Windows:
```bat
run_all.bat
```
