"""Compose exploded/after/detail triptychs and part thumbnails for V2."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).parent / "assets" / "v2"
FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 30)

STEPS = {
    "F07_1": "F07_1_pin", "F07_2B": "F07_2B_pin", "F07_3": "F07_3_pin", "F07_4": "F07_4_pin",
    "F09_3A": "F09_3A_pin", "F09_3B": "F09_3B_pin", "F09_3C": "F09_3C_pin",
    "F09_4A": "F09_4A_pin", "F09_4B": "F09_4B_pin", "F09_5A": "F09_5A_pin",
    "SCZ_2": "SCZ_2_pin", "SCZ_3A": "SCZ_3A_pin", "SCZ_3B": "SCZ_3B_center",
    "SCZ_4A": "SCZ_4A_pin", "SCZ_4B": "SCZ_4B_pin",
}
NO_DETAIL = {"F07_2A", "F09_1", "F09_2", "SCZ_1"}


def fit(im, w, h):
    im = im.copy()
    im.thumbnail((w, h), Image.Resampling.LANCZOS)
    return im


STEPLIST = ([f"F07_{i}" for i in ("1", "2A", "2B", "3", "4")]
            + [f"F09_{i}" for i in ("1", "2", "3A", "3B", "3C", "4A", "4B", "5A")]
            + [f"SCZ_{i}" for i in ("1", "2", "3A", "3B", "4A", "4B")])
for step in STEPLIST:
    canvas = Image.new("RGB", (1800, 1200), (248, 250, 252))
    dr = ImageDraw.Draw(canvas)
    ex = fit(Image.open(D / f"{step}_exploded.png"), 1080, 810)
    af = fit(Image.open(D / f"{step}_after.png"), 1080, 810)
    canvas.paste(ex, (0, 70))
    if step not in NO_DETAIL:
        af2 = fit(Image.open(D / f"{step}_after.png"), 680, 510)
        det = fit(Image.open(D / f"{STEPS[step]}_detail.png"), 680, 510)
        canvas.paste(af2, (1100, 70))
        canvas.paste(det, (1100, 640))
        dr.text((1100, 18), "装好后（同视角）", font=FONT, fill=(40, 45, 52))
        dr.text((1100, 588), "连接特写", font=FONT, fill=(40, 45, 52))
    else:
        # no separate closeup: use larger after image on right
        canvas.paste(fit(Image.open(D / f"{step}_after.png"), 680, 810), (1100, 70))
        dr.text((1100, 18), "装好后（同视角）", font=FONT, fill=(40, 45, 52))
    dr.text((0, 18), "爆炸图（箭头=装入方向）", font=FONT, fill=(40, 45, 52))
    canvas.save(D / f"{step}_triptych.png")
    print("composed", step)

# individual part thumbnails
import sys
sys.path.insert(0, str(Path(__file__).parent))
from render_v2 import PARTS, NEW, render, xform  # noqa: E402

for cand, parts in PARTS.items():
    for pid, mesh in parts.items():
        render([(mesh, NEW[cand])], f"part_{cand}_{pid}.png", size=(420, 340))
print("PART THUMBNAILS DONE")
