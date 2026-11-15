# ROUND1_DEMO_CAD — 可折叠3D打印机 第一轮缩比机械原理演示模型

版本 R1-V5 · 2026-11-15 · 连杆几何 1:2（V3.2.1 冻结参数 ×0.5）· 单位 mm

## 来源与版本
- 参数基准: GitHub CodyNing-desi/foldable-3d-printer **PR#1 (sync/v2-to-v3_2_1 @ 6229d60)**，
  `simulation_v3_2_1/config/candidates_v3_2_1.json` + `scripts/run_v3_2_1_verification.py` 冻结值。
  main 不是最新；旧 stageB 交付包为外购五金夹具体系，本轮已重建为纯打印可活动机构。
- 候选: M1 F09_L82 / M2 F07 / M3 SCZ / M4 F08_OPTIONAL（F12 No-Go 不制造）。

## 目录
- `F09_L82/ F07/ SCZ/ F08_OPTIONAL/`: 各含 CAD_SOURCE(参数化build123d源) / STEP(逐件+装配) /
  STL(逐件打印) / 3MF(排版工程, 无切片参数) / ASSEMBLY(姿态图+动画+装配STL) /
  VALIDATION(L1/L2/L3 JSON+清单) / BOM.csv。
- `COUPONS_L4/`: 接口试件 STL + TEST_PLAN.md（待现场确认）。
- `CAD_COMMON/`: 共享参数化内核 common_r1.py / kinematics_r1.py（各方案 CAD_SOURCE 引用）。
- 根级: MASTER_PARTS_BOM.csv / MOTION_VALIDATION_REPORT.md / PRINT_PLAN_5_MACHINES.md /
  ASSEMBLY_GUIDE.md / MODEL_LIMITATIONS.md / SHA256SUMS.txt。

## 再生成
项目 venv (Python 3.12 + build123d 0.13 + cadquery-ocp-novtk + trimesh + manifold3d)：
```
python scripts/build_all.py          # 逐件 STL/STEP + 装配
python scripts/validate_r1.py        # L1/L2/L3
python scripts/render_r1.py --gif    # 快照/动画
python scripts/joint_diagrams.py     # 运动简图
python scripts/build_coupons.py      # L4 试件
python scripts/make_3mf.py           # 3MF 排版
python scripts/make_docs.py          # BOM/文档
python scripts/package.py            # SHA256 + ZIP
```

## 关键声明（详见 MODEL_LIMITATIONS.md）
- 纯 PLA/PETG 打印机构，零新增采购目标；可活动，非静态姿态轮廓。
- F09 双柱同步为刚性杆被动耦合，不验证原双丝杆+同步带传动。
- SCZ 为经典固定端+滑动端剪叉（1 DOF 可证），与仿真对称丝杆驱动差异已声明。
- L2 为密集采样+精确网格布尔检查，非连续碰撞认证；L4 无打印机权限，待现场确认。
