from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "进度对比_01.png"
W, H = 2400, 1600
BG = "#F4F5F2"
INK = "#17262D"
MUTED = "#56656B"
TEAL = "#0C746B"
TEAL_LIGHT = "#DDEDE8"
AMBER = "#A55D0A"
AMBER_LIGHT = "#FFF0D9"
WHITE = "#FFFFFF"
LINE = "#D5DEDA"

im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)

def font(size, bold=False):
    path = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
    return ImageFont.truetype(path, size)

def text(x, y, value, size=30, color=INK, bold=False):
    d.text((x, y), value, font=font(size, bold), fill=color)

def box(x, y, w, h, fill=WHITE, outline=None, radius=24, width=2):
    d.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=outline, width=width)

def label(x, y, value, fill=TEAL):
    f = font(25, True)
    bbox = d.textbbox((0, 0), value, font=f)
    w = bbox[2] - bbox[0] + 36
    box(x, y, w, 48, fill=fill, radius=24)
    text(x + 18, y + 8, value, 25, WHITE, True)

text(80, 54, "可折叠 3D 打印机｜准备工作进度 01", 66, INK, True)
text(80, 146, "相较开题展板：从参考拼贴与初步构想，进入机构路线、算法边界和验证设计", 33, MUTED)
label(2070, 72, "对照图｜非实机验收", AMBER)

# Left: original board
box(80, 240, 750, 900)
label(116, 274, "上周｜开题展板", INK)
board = Image.open(ROOT / "evidence" / "开题展板_原始.jpg").convert("RGB")
board = board.resize((678, 508), Image.Resampling.LANCZOS)
im.paste(board, (116, 350))
text(116, 892, "展板上已有的工作", 35, INK, True)
for i, line in enumerate([
    "• 用户类别与空间痛点",
    "• A1 等现有机器与竞品图片",
    "• 折叠、自动取件的初步草图",
]):
    text(116, 956 + i * 48, line, 30, MUTED)
text(116, 1090, "本次对比保留这些基础，只检查新增进度。", 26, MUTED)

# Right: current state
box(870, 240, 1450, 900)
label(906, 274, "现在｜新增准备工作", TEAL)
text(906, 342, "当前机构主线", 32, INK, True)
text(906, 392, "具体实机 → 铰链折叠 → 机械基准 → 两点锁紧 → 回零 → 恢复打印", 31, TEAL, True)
text(906, 440, "首版保留线性运动学；五轴、旋转中打印与自动展开后置。", 27, MUTED)

cards = [
    ("01  案例研究", "19 条案例｜6 类机构路线", "商品、原型、专利、概念分层"),
    ("02  开放图纸", "24 个上游项目", "CAD／固件／许可证／commit 可回查"),
    ("03  算法边界", "剪刀非线性已拆解", "自定义运动学与五轴不抢首版"),
    ("04  打印床处理", "冷却→取件→复位→校准", "加入碰撞、首层和搬运检查"),
    ("05  验证与分工", "WP1–WP5｜角色与停止条件", "原机基线、20 次循环、三次打印"),
    ("06  手绘部署", "12 张设计图已拆解", "旅程、机构、碰撞、联锁与收敛"),
]
for i, (title, main, note) in enumerate(cards):
    col = i % 2
    row = i // 2
    x = 906 + col * 680
    y = 510 + row * 204
    box(x, y, 650, 178, fill=TEAL_LIGHT if i < 4 else WHITE, outline=LINE, radius=18)
    text(x + 24, y + 18, title, 26, MUTED, True)
    text(x + 24, y + 61, main, 30, INK, True)
    text(x + 24, y + 112, note, 24, MUTED)

# Bottom: explicit pending state
box(80, 1190, 2240, 290, fill=AMBER_LIGHT, outline="#E2C59B")
label(116, 1222, "尚未完成｜下一轮必须补齐", AMBER)
text(116, 1296, "实机测量　／　12 张真实手绘　／　1:1 折叠样机　／　展开后三次恢复打印", 38, INK, True)
text(116, 1372, "本图记录研究、规划与资料准备，不表示机器已经制造或折叠机构已经通过验证。", 29, MUTED)
text(80, 1532, "来源：开题展板原图、教师点评转写、当前研究库与上游快照。", 24, MUTED)

im.save(OUT, format="PNG", dpi=(150, 150))
print(OUT)
print(im.size, im.mode)
