"""Copy parametric sources into deliverable, write SHA256SUMS, build final ZIP."""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

WORK = Path(__file__).resolve().parent
import common_r1 as C
ROOT = C.deliverable_root()
ZIP_OUT = ROOT.parent / "ROUND1_DEMO_CAD.zip"

SCRIPTS = ["common_r1.py", "kinematics_r1.py", "build_gantry.py", "build_scz.py",
           "build_f08.py", "build_all.py", "validate_r1.py", "joints_r1.py", "render_r1.py",
           "make_3mf.py", "make_docs.py", "build_coupons.py", "joint_diagrams.py",
           "reproduce_check.py", "package.py"]

CAND_DIRS = {"F09_L82": "F09_L82", "F07": "F07", "SCZ": "SCZ", "F08_OPTIONAL": "F08_OPTIONAL"}


def archive_history():
    """P1-2: move superseded *_history.json into VALIDATION/HISTORY/ so the active
    validation list matches the current STL/3MF/BOM exactly."""
    n = 0
    for cand, d in CAND_DIRS.items():
        vd = ROOT / d / "VALIDATION"
        hist = vd / "HISTORY"
        for f in vd.glob("*_history.json"):
            hist.mkdir(exist_ok=True)
            shutil.move(str(f), str(hist / f.name))
            n += 1
    print(f"archived {n} history files")


def copy_sources():
    for cand, d in CAND_DIRS.items():
        cs = ROOT / d / "CAD_SOURCE"
        cs.mkdir(parents=True, exist_ok=True)
        for s in SCRIPTS:
            srcf, dstf = WORK / s, cs / s
            if srcf.exists() and dstf.exists() and srcf.read_bytes() == dstf.read_bytes():
                continue  # identical (incl. WORK == cs self-copy)
            shutil.copy2(srcf, dstf)
        (cs / "README.md").write_text(
            f"# {cand} CAD_SOURCE\n\n"
            "自包含参数化源（build123d, Python 3.12 + cadquery-ocp-novtk）。\n\n"
            f"再生成本方案: `python build_all.py {cand}`\n"
            f"验证: `python validate_r1.py {cand}` (含 L2b 装配闭合+孔轴审计)  渲染: `python render_r1.py {cand} --gif`\n"
            f"3MF: `python make_3mf.py {cand}`  文档/BOM: `python make_docs.py`\n"
            f"干净复现核查: `python reproduce_check.py {cand}`\n\n"
            "关键参数在 kinematics_r1.py（1:2 缩比 + 局部放大），零件几何在 build_gantry.py / "
            "build_scz.py / build_f08.py，配合/材料在 common_r1.py，运动副基准在 joints_r1.py。\n"
            "输出目录由 common_r1.deliverable_root() 自动定位（或设 ROUND1_OUT 环境变量）。\n",
            encoding="utf-8")
    print("sources copied")


def sha256sums():
    lines = []
    for f in sorted(ROOT.rglob("*")):
        if f.is_file() and f.name != "SHA256SUMS.txt" and "__pycache__" not in str(f):
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            lines.append(f"{h}  {f.relative_to(ROOT).as_posix()}")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SHA256SUMS: {len(lines)} files")


def make_zip():
    if ZIP_OUT.exists():
        ZIP_OUT.unlink()
    with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(ROOT.rglob("*")):
            if f.is_file() and "__pycache__" not in str(f):
                z.write(f, f.relative_to(ROOT.parent).as_posix())
    print(f"ZIP -> {ZIP_OUT} ({ZIP_OUT.stat().st_size/1e6:.1f} MB)")


def main():
    copy_sources()
    archive_history()
    sha256sums()
    make_zip()


if __name__ == "__main__":
    main()
