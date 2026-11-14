# 全方案虚拟仿真与优化筛选

本目录包含 F01–F14 与剪刀式 Z 轴（SCZ）的可执行概念模型、真实批量仿真结果、多目标优化、概念 CAD、折叠动画和筛选报告。

**先读 [`REPORT.md`](REPORT.md)，过程与推荐变化见 [`PROCESS_REVIEW.md`](PROCESS_REVIEW.md)。所有输出均为 L1/L2 虚拟推演和局部等效梁 L3，不是实机验证。**

## 一键复现

需要 Windows/Git Bash、Python 3.13 与 [uv](https://docs.astral.sh/uv/) 0.12+。从仓库根目录运行：

```bash
bash simulation/run_all.sh
```

`uv_run.sh` 在本机 uv 缓存中创建隔离环境，不写入 `.venv`，并设置 UTF-8 与 `PYTHONPATH`。`src/sitecustomize.py` 只过滤系统字体目录中无法解析的字体，解决本机 build123d 导入问题，不修改字体或上游包。

也可逐项运行：

```bash
bash simulation/uv_run.sh -m unittest discover -s tests -v
bash simulation/uv_run.sh scripts/verify_units_and_symbolic.py
bash simulation/uv_run.sh scripts/run_screening.py
bash simulation/uv_run.sh scripts/run_deepening.py --samples 10000
bash simulation/uv_run.sh scripts/run_optimization.py --pop-size 32 --generations 20
bash simulation/uv_run.sh scripts/run_sensitivity.py --samples 48
bash simulation/uv_run.sh scripts/select_recommendations.py
bash simulation/uv_run.sh scripts/validate_convergence.py
bash simulation/uv_run.sh scripts/select_third_option.py
bash simulation/uv_run.sh scripts/generate_figures.py
bash simulation/uv_run.sh scripts/run_beam_fea.py
bash simulation/uv_run.sh scripts/generate_cad.py
bash simulation/uv_run.sh scripts/record_environment.py
bash simulation/uv_run.sh scripts/generate_report.py
bash simulation/uv_run.sh scripts/validate_deliverables.py
```

## 目录

- `config/candidates.json`：15 套机构、参数边界、单位与假设来源。
- `src/foldsim/`：刚体几何、评价、静力学/刚度、蒙特卡洛、NSGA-II、DOE 与选择。
- `results/`：原始轨迹、CSV/JSON、NPZ 误差样本、随机种子、优化历史和环境版本。
- `figures/`：PNG/SVG 对比图与来源清单。
- `animations/`：每套 21 个实际求值姿态生成的 GIF 与逐帧图。
- `cad/`：推荐方案、第三项 SCZ 与备选 F08 的参数化 Python、STEP、STL 与 manifest；接口尺寸均未实测核验。`cad/reference/` 另保存 FoldaRap 真实铰链 STEP、孔系数据与快照。
- `verification/`：第三项决策、SCZ 实物验证计划、材料 BOM、成本摘要与空白数据表；这是待执行计划，不是实测结果。
- `tests/`：标准库 `unittest` 契约与回归测试。

## 证据等级

- **L1**：2.5D 刚体运动、Shapely 相交面积和挤出包络体积；不是完整三维装配碰撞。
- **L2**：静力学、降阶梁/锁点刚度与公差蒙特卡洛；不是标定有限元或实机打印精度。
- **L3（局部）**：等效矩形悬臂梁的三维六面体线弹性网格收敛，只验证梁公式与 FE 流程，不是整机/铰链 FEA。
- **L4**：实机标定、寿命与恢复打印仍未完成；`verification/` 是待执行方案，不作结果宣称。

`external/` 未修改。上游项目版本与许可证仍见 `external/sources.csv`。
