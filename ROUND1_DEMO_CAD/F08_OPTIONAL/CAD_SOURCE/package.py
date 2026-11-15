"""Copy parametric sources into deliverable, write SHA256SUMS, build final ZIP."""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent.parent / "ROUND1_DEMO_CAD"
ZIP_OUT = ROOT.parent / "ROUND1_DEMO_CAD.zip"

SCRIPTS = ["common_r1.py", "kinematics_r1.py", "build_gantry.py", "build_scz.py",
           "build_f08.py", "build_all.py", "validate_r1.py", "render_r1.py",
           "make_3mf.py", "make_docs.py", "build_coupons.py", "joint_diagrams.py", "package.py"]

CAND_DIRS = {"F09_L82": "F09_L82", "F07": "F07", "SCZ": "SCZ", "F08_OPTIONAL": "F08_OPTIONAL"}


def copy_sources():
    for cand, d in CAND_DIRS.items():
        cs = ROOT / d / "CAD_SOURCE"
        cs.mkdir(parents=True, exist_ok=True)
        for s in SCRIPTS:
            shutil.copy2(WORK / s, cs / s)
        (cs / "README.md").write_text(
            f"# {cand} CAD_SOURCE\n\n"
            "自包含参数化源（build123d, Python 3.12 + cadquery-ocp-novtk）。\n\n"
            f"再生成本方案: `python build_all.py {cand}`\n"
            f"验证: `python validate_r1.py {cand}`  渲染: `python render_r1.py {cand} --gif`\n"
            f"3MF: `python make_3mf.py {cand}`  文档/BOM: `python make_docs.py`\n\n"
            "关键参数在 kinematics_r1.py（1:2 缩比 + 局部放大），零件几何在 build_gantry.py / "
            "build_scz.py / build_f08.py，配合/材料在 common_r1.py。\n",
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
    sha256sums()
    make_zip()


if __name__ == "__main__":
    main()
