# SCZ CAD_SOURCE

自包含参数化源（build123d, Python 3.12 + cadquery-ocp-novtk）。

再生成本方案: `python build_all.py SCZ`
验证: `python validate_r1.py SCZ` (含 L2b 装配闭合+孔轴审计)  渲染: `python render_r1.py SCZ --gif`
3MF: `python make_3mf.py SCZ`  文档/BOM: `python make_docs.py`
干净复现核查: `python reproduce_check.py SCZ`

关键参数在 kinematics_r1.py（1:2 缩比 + 局部放大），零件几何在 build_gantry.py / build_scz.py / build_f08.py，配合/材料在 common_r1.py，运动副基准在 joints_r1.py。
输出目录由 common_r1.deliverable_root() 自动定位（或设 ROUND1_OUT 环境变量）。
