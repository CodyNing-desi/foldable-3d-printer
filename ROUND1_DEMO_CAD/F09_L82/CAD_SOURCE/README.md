# F09_L82 CAD_SOURCE

自包含参数化源（build123d, Python 3.12 + cadquery-ocp-novtk）。

再生成本方案: `python build_all.py F09_L82`
验证: `python validate_r1.py F09_L82`  渲染: `python render_r1.py F09_L82 --gif`
3MF: `python make_3mf.py F09_L82`  文档/BOM: `python make_docs.py`

关键参数在 kinematics_r1.py（1:2 缩比 + 局部放大），零件几何在 build_gantry.py / build_scz.py / build_f08.py，配合/材料在 common_r1.py。
