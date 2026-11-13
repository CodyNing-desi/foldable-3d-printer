from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence" / "折叠收纳方案_队友原版.pptx"
OUTPUT = ROOT / "deliverables" / "折叠收纳方案_完善版.pptx"
FONT = "Microsoft YaHei"
INK = "202729"
MUTED = "596467"
BLUE = "638DA5"
PALE = "EAF2F5"
PALE_AMBER = "FFF3DF"
AMBER = "9B641B"
WHITE = "FFFFFF"
LINE = "D8E1E4"

prs = Presentation(SOURCE)
blank = next(layout for layout in prs.slide_layouts if layout.name == "Blank")

def add_text(slide, value, x, y, w, h, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = value
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    return shape

def add_lines(slide, lines, x, y, w, h, size=17, color=INK, gap=8):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = True
    for index, value in enumerate(lines):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        run = p.add_run()
        run.text = value
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor.from_string(color)
    return shape

def add_box(slide, x, y, w, h, fill=WHITE, line=LINE, radius=True):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(fill)
    shape.line.color.rgb = RGBColor.from_string(line)
    shape.line.width = Pt(1)
    return shape

def add_header(slide, title, subtitle, number):
    add_text(slide, title, 0.54, 0.31, 12.25, 0.65, 31.5, INK, True)
    add_text(slide, subtitle, 0.56, 1.03, 12.17, 0.4, 16.5, MUTED)
    add_text(slide, f"{number:02d}", 12.45, 7.1, 0.42, 0.24, 12, MUTED, align=PP_ALIGN.RIGHT)

def add_card(slide, title, lines, x, y, w, h, fill=WHITE, title_color=BLUE):
    add_box(slide, x, y, w, h, fill)
    add_text(slide, title, x + 0.26, y + 0.24, w - 0.52, 0.45, 22, title_color, True)
    add_lines(slide, lines, x + 0.26, y + 0.88, w - 0.52, h - 1.12, 16.5, INK, 9)

def add_note(slide, value):
    slide.notes_slide.notes_text_frame.text = value

def add_printer(slide, x, y, scale=1.0, folded=False):
    add_box(slide, x, y + 3.05 * scale, 3.9 * scale, 0.42 * scale, PALE, BLUE, False)
    add_box(slide, x + 0.38 * scale, y + 2.48 * scale, 2.65 * scale, 0.15 * scale, WHITE, BLUE, False)
    add_text(slide, "打印板", x + 1.2 * scale, y + 2.14 * scale, 1.5 * scale, 0.3 * scale, 13, MUTED)
    pivot_x = x + 0.65 * scale
    pivot_y = y + 2.94 * scale
    if not folded:
        add_box(slide, pivot_x, y + 0.3 * scale, 0.32 * scale, 2.55 * scale, WHITE, BLUE, False)
        add_box(slide, pivot_x + 0.2 * scale, y + 1.25 * scale, 2.6 * scale, 0.28 * scale, WHITE, BLUE, False)
        add_box(slide, pivot_x + 2.15 * scale, y + 1.48 * scale, 0.46 * scale, 0.58 * scale, PALE, BLUE, False)
        add_text(slide, "Z 立柱", pivot_x - 0.25 * scale, y, 1.3 * scale, 0.3 * scale, 13, MUTED)
        add_text(slide, "X 横臂", pivot_x + 1.15 * scale, y + 0.94 * scale, 1.4 * scale, 0.3 * scale, 13, MUTED)
    else:
        column = add_box(slide, pivot_x + 0.45 * scale, y + 1.75 * scale, 0.32 * scale, 2.55 * scale, WHITE, BLUE, False)
        column.rotation = 78
        beam = add_box(slide, pivot_x + 1.0 * scale, y + 2.38 * scale, 2.2 * scale, 0.28 * scale, WHITE, BLUE, False)
        beam.rotation = 78
    pivot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(pivot_x - 0.12 * scale), Inches(pivot_y - 0.18 * scale), Inches(0.42 * scale), Inches(0.42 * scale))
    pivot.fill.solid()
    pivot.fill.fore_color.rgb = RGBColor.from_string(BLUE)
    pivot.line.color.rgb = RGBColor.from_string(BLUE)
    add_text(slide, "转轴", pivot_x - 0.48 * scale, pivot_y - 0.9 * scale, 1.0 * scale, 0.3 * scale, 13, BLUE, True)

slide = prs.slides.add_slide(blank)
add_header(slide, "14版之后：方案已发散，验证刚开始", "保留全部版本；新增的是证据边界与下一步收敛方法", 35)
add_card(slide, "已经做到", ["14 个概念版本，归为 8 条方向", "区分驱动、导向、定位、锁紧与检测", "每版都有动作顺序、代价和首轮验证"], 0.56, 1.7, 3.94, 4.65, PALE)
add_card(slide, "还没有证明", ["同尺度折叠尺寸与收纳收益", "全轨迹干涉、承载和锁紧刚度", "重复定位与展开后的恢复打印"], 4.7, 1.7, 3.94, 4.65, PALE_AMBER, AMBER)
add_card(slide, "现在怎样收敛", ["mini：先用 F01 根部关节做样件", "A1：用 F03 检查双柱同轴与锁紧", "碰撞看 F04／F10；箱体 F11 后置"], 8.84, 1.7, 3.94, 4.65, PALE)
add_text(slide, "新增页只整理证据与验证，不改变原有 14 版方案内容。", 0.62, 6.62, 12.0, 0.38, 16.5, MUTED)
add_note(slide, "本页为新增证据边界页。14版仍是概念方案，当前未形成尺寸、干涉、承载和恢复打印证据。保留全部原始方案，不在本页宣称某个方向已验证。")

slide = prs.slides.add_slide(blank)
add_header(slide, "同尺度对照：把折前与折后画在一起", "示意只定义测量对象，不填写未测尺寸；机构图不是加工图", 36)
add_box(slide, 0.56, 1.58, 5.86, 4.88, WHITE)
add_box(slide, 6.91, 1.58, 5.86, 4.88, WHITE)
add_text(slide, "工作状态", 0.84, 1.82, 2.0, 0.42, 22, BLUE, True)
add_text(slide, "收纳状态", 7.19, 1.82, 2.0, 0.42, 22, BLUE, True)
add_printer(slide, 1.15, 2.25, 0.95, False)
add_printer(slide, 7.65, 2.25, 0.95, True)
chevron = slide.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(6.47), Inches(3.55), Inches(0.42), Inches(0.68))
chevron.fill.solid()
chevron.fill.fore_color.rgb = RGBColor.from_string(BLUE)
chevron.line.color.rgb = RGBColor.from_string(BLUE)
add_text(slide, "记录：工作外包络、根部基准、锁点、床板与管线", 0.86, 5.82, 5.2, 0.42, 15, MUTED)
add_text(slide, "记录：收纳外包络、运输承托、运输锁与附件位置", 7.2, 5.82, 5.2, 0.42, 15, MUTED)
add_text(slide, "折叠前后使用同一台实机、同一参照点和同一测量方法。", 0.62, 6.67, 12.0, 0.38, 16.5, MUTED)
add_note(slide, "新增同尺度示意页。图中机构仅用于说明要画哪些对象、测哪些关系，不代表转轴、杆件、床板或锁点的最终几何。不得从示意图读取尺寸或承载。")

slide = prs.slides.add_slide(blank)
add_header(slide, "先验证根部关节，再恢复整机打印", "同一测量点、同一载荷、同一 G-code；失败也进入记录", 37)
items = [
    ("01  折叠循环", ["做 20 次折叠／展开", "记录卡滞、碰撞与松脱"]),
    ("02  定位与刚度", ["测参考点偏移与关节挠度", "载荷和测量位置保持不变"]),
    ("03  状态与安全", ["确认止挡、锁点和失电状态", "未锁紧时不进入打印"]),
    ("04  恢复打印", ["回零后检查整床首层", "同一文件打印三次"]),
]
for i, (title, lines) in enumerate(items):
    x = 0.56 + i * 3.15
    add_card(slide, title, lines, x, 1.75, 2.94, 2.6, PALE if i < 2 else WHITE)
add_box(slide, 0.56, 4.72, 12.21, 1.52, PALE_AMBER, "E5C99D")
add_text(slide, "先通过最简单的手动关节，再增加助力、电动、箱体或伸缩模组。", 0.86, 5.0, 11.6, 0.46, 21, AMBER, True)
add_text(slide, "任何一次失败都记录机构版本、载荷、测量位置和现象；不用自动调平掩盖机架松动。", 0.86, 5.55, 11.6, 0.4, 16.5, INK)
add_text(slide, "当前目标不是选最复杂的方案，而是找到能重复恢复工作状态的最简单机构。", 0.62, 6.67, 12.0, 0.38, 16.5, MUTED)
add_note(slide, "新增验证闭环页。20次循环和三次打印是本轮验证任务，不是已完成结果。先验证根部关节，再决定是否增加助力、电动或其他模组。")

OUTPUT.parent.mkdir(exist_ok=True)
prs.save(OUTPUT)
print(f"Saved {OUTPUT} with {len(prs.slides)} slides")
