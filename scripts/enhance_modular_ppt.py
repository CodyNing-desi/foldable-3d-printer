from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence" / "折叠收纳与模块化_队友原版.pptx"
OUTPUT = ROOT / "deliverables" / "折叠收纳与模块化_完善版.pptx"
FONT = "Microsoft YaHei"
INK = "202729"
MUTED = "596467"
BLUE = "638DA5"
PALE = "EAF2F5"
AMBER_PALE = "FFF3DF"
AMBER = "9B641B"
WHITE = "FFFFFF"
LINE = "D8E1E4"

prs = Presentation(SOURCE)
blank = next(layout for layout in prs.slide_layouts if layout.name == "Blank")

def text(slide, value, x, y, w, h, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT):
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

def lines(slide, values, x, y, w, h, size=16.5, color=INK, gap=7):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = True
    for index, value in enumerate(values):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        run = p.add_run()
        run.text = value
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor.from_string(color)
    return shape

def box(slide, x, y, w, h, fill=WHITE, line=LINE):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(fill)
    shape.line.color.rgb = RGBColor.from_string(line)
    shape.line.width = Pt(1)
    return shape

def header(slide, title, subtitle, number):
    text(slide, title, 0.54, 0.31, 12.25, 0.65, 31.5, INK, True)
    text(slide, subtitle, 0.56, 1.03, 12.17, 0.4, 16.5, MUTED)
    text(slide, f"{number:02d}", 12.45, 7.1, 0.42, 0.24, 12, MUTED, align=PP_ALIGN.RIGHT)

def card(slide, title, body, x, y, w, h, fill=WHITE, title_color=BLUE):
    box(slide, x, y, w, h, fill)
    text(slide, title, x + 0.24, y + 0.2, w - 0.48, 0.42, 21, title_color, True)
    lines(slide, body, x + 0.24, y + 0.78, w - 0.48, h - 0.98, 15.5)

def note(slide, value):
    slide.notes_slide.notes_text_frame.text = value

def printer(slide, x, y, folded=False):
    box(slide, x, y + 2.6, 3.65, 0.36, PALE, BLUE)
    box(slide, x + 0.38, y + 2.15, 2.55, 0.13, WHITE, BLUE)
    text(slide, "打印板", x + 1.15, y + 1.86, 1.2, 0.25, 12, MUTED)
    px, py = x + 0.62, y + 2.5
    if not folded:
        box(slide, px, y + 0.25, 0.28, 2.25, WHITE, BLUE)
        box(slide, px + 0.18, y + 1.08, 2.4, 0.24, WHITE, BLUE)
        box(slide, px + 2.0, y + 1.29, 0.4, 0.5, PALE, BLUE)
        text(slide, "Z 立柱", px - 0.1, y, 1.2, 0.25, 12, MUTED)
        text(slide, "X 横臂", px + 1.05, y + 0.82, 1.2, 0.25, 12, MUTED)
    else:
        column = box(slide, px + 0.45, y + 1.5, 0.28, 2.25, WHITE, BLUE)
        column.rotation = 78
        beam = box(slide, px + 0.9, y + 2.05, 2.0, 0.24, WHITE, BLUE)
        beam.rotation = 78
    pivot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(px - 0.12), Inches(py - 0.14), Inches(0.36), Inches(0.36))
    pivot.fill.solid()
    pivot.fill.fore_color.rgb = RGBColor.from_string(BLUE)
    pivot.line.color.rgb = RGBColor.from_string(BLUE)
    text(slide, "转轴", px - 0.42, py - 0.68, 0.9, 0.25, 12, BLUE, True)

slide = prs.slides.add_slide(blank)
header(slide, "14＋4 之后：折叠主线与模块化分支", "14 个机构版本与 4 个架构方向分层呈现，不把概念数量当作验证进度", 48)
card(slide, "M01｜折叠三轴主线", ["收纳关节在打印时锁紧", "先验证轨迹、锁紧和重复定位", "仍按连续 XYZ 导轨打印"], 0.56, 1.68, 6.0, 2.1, PALE)
card(slide, "M04｜接口可并行验证", ["只做一对定位锁紧接头", "记录反复拆装后的参考点变化", "不提前承诺成套扩容与任意兼容"], 6.77, 1.68, 6.0, 2.1, PALE)
card(slide, "M02｜机械臂独立研究", ["关节在打印时持续参与运动", "需要运动学、回差与末端刚性", "不能凭多关节外形称为五轴"], 0.56, 4.05, 6.0, 2.1, WHITE)
card(slide, "M03｜双转轴独立研究", ["先分度定位，再研究连续联动", "需要旋转标定、轨迹与避碰", "普通平面切片不能直接控制全部轴"], 6.77, 4.05, 6.0, 2.1, WHITE)
text(slide, "如果本轮仍以折叠为主：M01 优先；M04 只验证接口；M02／M03 不阻塞折叠主线。", 0.62, 6.58, 12.0, 0.42, 16.5, MUTED)
note(slide, "新增分层页。14个折叠版本和M01-M04架构方向不是同层方案数量。此页不替团队提前最终选型，只明确折叠主线和不同方向的验证依赖。")

slide = prs.slides.add_slide(blank)
header(slide, "先画清 M01 的工作与收纳状态", "同尺度、同附件、同参照点；示意图不填写未测尺寸与性能", 49)
box(slide, 0.56, 1.58, 4.45, 4.8, WHITE)
box(slide, 5.23, 1.58, 4.45, 4.8, WHITE)
text(slide, "工作状态", 0.82, 1.82, 1.8, 0.4, 21, BLUE, True)
text(slide, "收纳状态", 5.49, 1.82, 1.8, 0.4, 21, BLUE, True)
printer(slide, 0.85, 2.25, False)
printer(slide, 5.52, 2.25, True)
chevron = slide.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(4.91), Inches(3.52), Inches(0.36), Inches(0.6))
chevron.fill.solid()
chevron.fill.fore_color.rgb = RGBColor.from_string(BLUE)
chevron.line.color.rgb = RGBColor.from_string(BLUE)
box(slide, 9.91, 1.58, 2.86, 4.8, PALE)
text(slide, "同尺度记录", 10.17, 1.82, 2.3, 0.4, 21, BLUE, True)
lines(slide, ["工作与收纳外包络", "床板、料盘和全部附件", "转轴、锁点与机械基准", "整个折叠过程的碰撞区", "展开后的回零参考点"], 10.17, 2.45, 2.3, 2.8, 15.5, INK, 10)
text(slide, "折叠前后使用同一台实机、同一套附件和同一测量方法。", 0.62, 6.66, 12.0, 0.38, 16.5, MUTED)
note(slide, "新增M01同尺度示意。图中的几何仅说明测量对象，不是加工或装配图。收纳比较必须包含床板、料盘、线缆与运动过程，不能只用机身渲染图。")

slide = prs.slides.add_slide(blank)
header(slide, "下一轮交付：四个模型，同一套记录", "每条路线回答一个结构问题；本轮不把未测性能写成结论", 50)
rows = [
    ("M01｜折叠模型", "连杆与导轨占位件", "折叠轨迹、20 次循环、参考点偏移", "不承诺收纳率与打印性能"),
    ("M04｜接口模型", "一对定位锁紧接头", "反复拆装、锁紧刚度、参考点变化", "不承诺任意模块兼容"),
    ("M02｜机械臂样段", "关节样段与等重工具", "可达区、末端挠度、底座稳定性", "不以关节数代替轴数证明"),
    ("M03｜双转台模型", "可倾转平台与喷头占位件", "旋转中心、夹具碰撞、分度轨迹", "不宣称连续五轴已完成"),
]
for i, (name, model, measure, boundary) in enumerate(rows):
    y = 1.62 + i * 1.14
    box(slide, 0.56, y, 12.21, 0.98, PALE if i == 0 else WHITE)
    text(slide, name, 0.78, y + 0.17, 2.35, 0.36, 18, BLUE, True)
    text(slide, model, 3.1, y + 0.17, 2.55, 0.52, 15.5, INK)
    text(slide, measure, 5.75, y + 0.17, 3.65, 0.52, 15.5, INK)
    text(slide, boundary, 9.55, y + 0.17, 2.95, 0.52, 15.5, MUTED)
text(slide, "所有模型记录：机构版本、测量位置、载荷、装配次数、失效现象和对应照片／视频。", 0.62, 6.4, 12.0, 0.42, 16.5, MUTED)
text(slide, "若折叠为主线：先交 M01 的折叠与恢复打印证据；其余模型按同一格式保留。", 0.62, 6.84, 12.0, 0.38, 16.5, BLUE, True)
note(slide, "新增共同验证页。20次循环是下一轮任务，不是已完成结果。四方向都用机构版本、测量位置、载荷、次数和失效记录比较；折叠主线需要继续完成恢复打印。")

OUTPUT.parent.mkdir(exist_ok=True)
prs.save(OUTPUT)
print(f"Saved {OUTPUT} with {len(prs.slides)} slides")
