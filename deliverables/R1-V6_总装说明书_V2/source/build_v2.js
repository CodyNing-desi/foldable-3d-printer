const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");
const A = (f) => path.join(__dirname, "assets", f);
const AV = (f) => path.join(__dirname, "assets", "v2", f);
const ASTEP = (f) => path.join(__dirname, "assets", "steps", f);

const C = {
  red: "D01012", redD: "8E0B0D", redT: "FDE3E3",
  blue: "0057A8", blueD: "003E77", blueT: "DCEAF7",
  green: "00852B", greenD: "005C1D", greenT: "DFF0E4",
  yellow: "F5C518", yellowD: "B78F00", yellowT: "FFF3C4",
  black: "1B1B1B", gray: "5A5A5A", lgray: "8A8A8A",
  line: "D9D9D9", light: "F4F5F7", imgbg: "F8FAFC",
  white: "FFFFFF", tip: "FFF6D6", warn: "FDECEA",
};
const DARK = { [C.red]: C.redD, [C.blue]: C.blueD, [C.green]: C.greenD, [C.yellow]: C.yellowD, [C.black]: "000000", [C.lgray]: "666666" };
const F = "Microsoft YaHei", M = "Courier New";
const W = 13.33, H = 7.5;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "R1-V6 装配组";
pres.title = "R1-V6 三方案总装说明书 V2";

// ---------- text metrics / audit ----------
const audit = [];
let curSlide = 0;
function tw(str, pt, font, bold) {
  let em = 0;
  for (const ch of str) {
    if (font === M) em += 0.6;
    else if (ch.codePointAt(0) > 0x2e7f) em += 1.0;
    else em += 0.58;
  }
  return (em * pt / 72) * (bold ? 1.03 : 1);
}
function estH(str, w, pt, font, bold) {
  let n = 0;
  for (const l of String(str).split("\n")) n += Math.max(1, Math.ceil(tw(l, pt, font, bold) / Math.max(w, 0.1)));
  return n * pt * 1.36 / 72;
}
function rec(name, x, y, w, h, need) {
  audit.push({ s: curSlide, name, x, y, w, h, need: need || 0 });
}
function report() {
  const bad = [];
  for (const a of audit) {
    if (a.need > a.h + 0.035) bad.push(`S${a.s} ${a.name}: text needs ${a.need.toFixed(2)}in > box ${a.h.toFixed(2)}in`);
    if (a.x < -0.01 || a.y < -0.01 || a.x + a.w > W + 0.02 || a.y + a.h > H + 0.02) bad.push(`S${a.s} ${a.name}: out of bounds (${a.x.toFixed(2)},${a.y.toFixed(2)},${a.w.toFixed(2)},${a.h.toFixed(2)})`);
  }
  if (bad.length) { console.log("AUDIT ISSUES:\n" + bad.join("\n")); } else console.log("AUDIT OK");
}

// ---------- primitives ----------
function txt(s, text, x, y, w, h, o = {}) {
  const pt = o.fontSize || 13, font = o.fontFace || F, bold = !!o.bold;
  const lines = Array.isArray(text) ? text.map(t => t.text).join("\n") : text;
  const need = estH(lines, w - (o.bullet ? 0.28 : 0), pt, font, bold);
  rec(o.name || String(lines).slice(0, 14), x, y, w, h, need);
  s.addText(text, { x, y, w, h, margin: 0, valign: o.valign || "top", align: o.align || "left", fontFace: font, fontSize: pt, bold, color: o.color || C.black, bullet: o.bullet || false, paraSpaceAfter: o.paraSpaceAfter || 0, italic: !!o.italic, lineSpacing: o.lineSpacing });
}
function rrect(s, x, y, w, h, fill, lineColor, linePt, radius) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: lineColor ? { color: lineColor, width: linePt || 1 } : { type: "none" }, rectRadius: radius == null ? 0.06 : radius });
}
function rect(s, x, y, w, h, fill, lineColor, linePt) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: fill }, line: lineColor ? { color: lineColor, width: linePt || 1 } : { type: "none" } });
}
function circ(s, x, y, d, fill, lineColor, linePt) {
  s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: lineColor ? { color: lineColor, width: linePt || 1 } : { type: "none" } });
}
function brick(s, x, y, w, h, color, text, o = {}) {
  const tc = o.tc || C.white, fs = o.fs || 16, studs = o.studs == null ? (w > 1.5 ? 3 : 2) : o.studs;
  const d = Math.min(0.17, h * 0.32);
  if (studs > 0) {
    const span = w * 0.62;
    for (let i = 0; i < studs; i++) {
      const cx = x + w / 2 - span / 2 + (studs === 1 ? span / 2 : span * i / (studs - 1));
      circ(s, cx - d / 2, y - d / 2, d, color, DARK[color] || color, 0.75);
    }
  }
  rrect(s, x, y, w, h, color, null, 0, 0.05);
  if (text) txt(s, text, x, y - 0.01, w, h + 0.02, { fontSize: fs, bold: true, color: tc, align: "center", valign: "middle", name: "brick:" + text });
}
function chip(s, x, y, w, code, qty, o = {}) {
  const h = o.h || 0.36;
  rrect(s, x, y, w, h, C.white, C.line, 1, 0.05);
  const mono = o.mono !== false;
  txt(s, code, x + 0.14, y, w - (qty ? 0.95 : 0.28), h, { fontSize: o.fs || 12, fontFace: mono ? M : F, bold: true, color: C.black, valign: "middle", name: "chip:" + code });
  if (qty) txt(s, qty, x + w - 0.78, y, 0.64, h, { fontSize: 12.5, bold: true, color: C.red, align: "right", valign: "middle", name: "qty:" + qty });
}
function label(s, x, y, text, color) {
  rect(s, x, y + 0.05, 0.12, 0.12, color);
  txt(s, text, x + 0.22, y - 0.03, 3.5, 0.3, { fontSize: 12.5, bold: true, color: C.gray, name: "label:" + text });
}
function numItem(s, x, y, w, n, text, color, pt) {
  pt = pt || 13;
  const d = 0.3;
  circ(s, x, y + 0.02, d, color);
  txt(s, String(n), x, y + 0.02, d, d, { fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle", name: "num" + n });
  const need = estH(text, w - 0.44, pt, F, false);
  const h = Math.max(0.3, need + 0.04);
  txt(s, text, x + 0.44, y, w - 0.44, h, { fontSize: pt, color: C.black, valign: "middle", name: "step:" + text.slice(0, 10) });
  return h;
}
function checkItem(s, x, y, w, text, color, mark, pt, textColor) {
  pt = pt || 13;
  const d = 0.22;
  if (mark === "ok") {
    circ(s, x, y + 0.04, d + 0.04, color);
    txt(s, "✓", x, y + 0.04, d + 0.04, d + 0.04, { fontSize: 11, bold: true, color: color === C.yellow ? C.black : C.white, align: "center", valign: "middle", name: "ok" });
  } else if (mark === "no") {
    circ(s, x, y + 0.04, d + 0.04, color);
    txt(s, "✕", x, y + 0.04, d + 0.04, d + 0.04, { fontSize: 10, bold: true, color: C.white, align: "center", valign: "middle", name: "no" });
  } else {
    rect(s, x, y + 0.05, d, d, C.white, C.lgray, 1.2);
  }
  const need = estH(text, w - 0.42, pt, F, false);
  const h = Math.max(0.28, need + 0.04);
  txt(s, text, x + 0.42, y, w - 0.42, h, { fontSize: pt, color: textColor || C.black, valign: "middle", name: "chk:" + text.slice(0, 10) });
  return h;
}
function imgPanel(s, x, y, w, h, file, caption, o = {}) {
  rrect(s, x, y, w, h, o.fill || C.imgbg, "E3E6EA", 1, 0.08);
  const p = 0.12;
  fitImg(s, file, x + p, y + p, w - 2 * p, h - 2 * p);
  if (caption) txt(s, caption, x, y + h + 0.07, w, 0.42, { fontSize: 10.5, color: C.gray, align: "center", name: "cap:" + file });
}
function imgDim(file) {
  if (file.endsWith("_triptych.png")) return [1800, 1200];
  if (file.startsWith("pin_")) return [600, 700];
  if (file.startsWith("clip_")) return [900, 800];
  if (file.startsWith("part_")) return [420, 340];
  if (file.endsWith("contact_sheet.png")) return [3300, 1700];
  if (file.endsWith("exploded.png")) return [2240, 992];
  if (file === "SCZ_joint_schematic.png") return [1650, 750];
  if (file.endsWith("joint_schematic.png")) return [1350, 975];
  return [1100, 850];
}
function fitImg(s, file, x, y, w, h) {
  const [iw, ih] = imgDim(file);
  const fp = /^(step_|coupon_)/.test(file) ? ASTEP(file) : (fs.existsSync(AV(file)) ? AV(file) : A(file));
  const sc = Math.min(w / iw, h / ih);
  const fw = iw * sc, fh = ih * sc;
  s.addImage({ path: fp, x: x + (w - fw) / 2, y: y + (h - fh) / 2, w: fw, h: fh });
  rec("img:" + file, x, y, w, h, 0);
}
function warnBox(s, x, y, w, h, text) {
  rrect(s, x, y, w, h, C.warn, C.red, 1.5, 0.06);
  circ(s, x + 0.16, y + h / 2 - 0.14, 0.28, C.red);
  txt(s, "!", x + 0.16, y + h / 2 - 0.14, 0.28, 0.28, { fontSize: 14, bold: true, color: C.white, align: "center", valign: "middle", name: "warn!" });
  txt(s, text, x + 0.58, y, w - 0.74, h, { fontSize: 13, bold: true, color: C.redD, valign: "middle", name: "warn:" + text.slice(0, 10) });
}
function progressStrip(s, x, y, w, items, current, color) {
  const gap = 0.08, n = items.length, bw = (w - gap * (n - 1)) / n;
  items.forEach((t, i) => {
    const bx = x + i * (bw + gap), on = i === current;
    rrect(s, bx, y, bw, 0.3, on ? color : "EFEFEF", null, 0, 0.04);
    txt(s, t, bx, y, bw, 0.3, { fontSize: 9.5, bold: on, color: on ? (color === C.yellow ? C.black : C.white) : C.lgray, align: "center", valign: "middle", name: "prog:" + t });
  });
}
function footer(s, n, dark) {  const col = dark ? "9A9A9A" : C.lgray;
  txt(s, "R1-V6 三方案总装说明书", 0.5, 7.14, 4.5, 0.26, { fontSize: 9, color: col, name: "ftL" });
  rect(s, 12.14, 7.19, 0.12, 0.12, dark ? C.yellow : C.red);
  txt(s, `${String(n).padStart(2, "0")} / 41`, 12.32, 7.12, 0.55, 0.26, { fontSize: 9, color: col, name: "ftR" });
}
function header(s, code, color, title, o = {}) {
  const bw = Math.max(0.95, tw(code, 16, F, true) + 0.5);
  brick(s, 0.5, 0.56, bw, 0.58, color, code, { fs: 16, tc: o.tc || C.white });
  txt(s, title, 0.5 + bw + 0.28, 0.42, W - (0.5 + bw + 0.28) - 0.5, 0.82, { fontSize: o.fs || 27, bold: true, color: o.titleColor || C.black, valign: "middle", name: "title:" + title });
}
function newSlide(n) { curSlide = n; return pres.addSlide(); }

// ---------- step page template ----------
function stepSlide(n, cfg) {
  const s = newSlide(n);
  s.background = { color: C.white };
  header(s, cfg.code, cfg.color, cfg.title, { tc: cfg.tc });
  const lx = 0.5, lw = 6.05;
  let y = 1.45;
  label(s, lx, y, "使用零件", cfg.color); y += 0.3;
  for (const [code, qty] of cfg.parts) { chip(s, lx, y, lw, code, qty, { h: 0.32, mono: cfg.mono !== false && /^[A-Z0-9\-× ]+$/.test(code) }); y += 0.38; }
  y += 0.12;
  label(s, lx, y, cfg.stepsLabel || "操作", cfg.color); y += 0.32;
  cfg.steps.forEach((t, i) => { y += numItem(s, lx, y, lw, i + 1, t, cfg.color) + 0.06; });
  y += 0.1;
  label(s, lx, y, cfg.checkLabel || "检查", cfg.color); y += 0.32;
  for (const t of cfg.checks) { y += checkItem(s, lx, y, lw, t, cfg.color, cfg.checkMark) + 0.06; }
  if (cfg.footnote) { txt(s, cfg.footnote, lx, y + 0.02, lw, 0.32, { fontSize: 10.5, color: C.gray, name: "footnote" }); y += 0.36; }
  rec("leftcol-end", lx, 1.45, lw, y - 1.45, 0);
  if (y > (cfg.warn || cfg.extra ? 6.28 : 6.98)) console.log(`S${n} LEFT COLUMN TOO LONG: ends ${y.toFixed(2)}`);
  // right image
  const rx = 6.85, rw = 5.98;
  const ph = cfg.warn || cfg.extra ? 4.0 : 4.55;
  if (cfg.image) imgPanel(s, rx, 1.45, rw, ph, cfg.image, cfg.caption);
  else if (cfg.diagram) cfg.diagram(s, rx, 1.45, rw, ph);
  if (cfg.prog) progressStrip(s, rx, (cfg.warn || cfg.extra) ? 6.0 : 6.62, rw, cfg.prog.items, cfg.prog.i, cfg.color);
  if (cfg.warn) warnBox(s, 0.5, 6.42, 12.33, 0.58, cfg.warn);
  if (cfg.extra) cfg.extra(s, 0.5, 6.42, 12.33, 0.58);
  footer(s, n);
  if (cfg.notes) s.addNotes(cfg.notes);
  return s;
}


// ======================= V2 helpers =======================
function partChipV2(s, x, y, w, code, qty, thumb, material) {
  const h = 0.48;
  rrect(s, x, y, w, h, C.white, C.line, 1, 0.05);
  if (thumb) fitImg(s, thumb, x + 0.05, y + 0.06, 0.46, 0.36);
  const mono = /^[A-Z0-9\-]+$/.test(code);
  txt(s, code, x + 0.58, y + 0.01, w - 1.5, 0.28, { fontSize: 14, fontFace: mono ? M : F, bold: true, valign: "middle", name: "part:" + code });
  if (qty) txt(s, qty, x + w - 0.8, y + 0.01, 0.66, 0.28, { fontSize: 14, bold: true, color: C.red, align: "right", valign: "middle", name: "qty" });
  if (material) txt(s, material, x + 0.58, y + 0.28, w - 0.72, 0.16, { fontSize: 9, color: C.gray, name: "mat" });
}
function stepV2(n, cfg) {
  const s = newSlide(n);
  s.background = { color: C.white };
  header(s, cfg.code, cfg.color, cfg.title, { tc: cfg.tc, fs: 28 });
  const lx = 0.45, lw = 4.65;
  let y = 1.45;
  label(s, lx, y, "本步零件", cfg.color); y += 0.3;
  for (const p of cfg.parts) { partChipV2(s, lx, y, lw, p[0], p[1], p[2], p[3]); y += 0.48; }
  y += 0.1;
  label(s, lx, y, "操作（按顺序）", cfg.color); y += 0.34;
  cfg.steps.forEach((t, i) => { y += numItem(s, lx, y, lw, i + 1, t, cfg.color, 16) + 0.08; });
  if (y > 6.95) console.log(`S${n} LEFT COLUMN TOO LONG ${y.toFixed(2)}`);
  const rx = 5.35, rw = 7.48;
  if (cfg.image) {
    rrect(s, rx, 1.45, rw, 4.1, C.imgbg, "E3E6EA", 1, 0.08);
    fitImg(s, cfg.image, rx + 0.1, 1.55, rw - 0.2, 3.9);
    txt(s, cfg.caption || "新件=方案色，已装件=灰色；橙=销轴，红=卡圈", rx, 5.6, rw, 0.3, { fontSize: 11, color: C.gray, align: "center", name: "stepcap" });
  }
  const bh = cfg.footnote ? 1.12 : 0.88;
  rrect(s, rx, 5.95, rw, bh, C.greenT, null, 0, 0.06);
  txt(s, "装对判断", rx + 0.2, 6.06, 1.1, 0.26, { fontSize: 12.5, bold: true, color: C.greenD, name: "checkH" });
  let cy = 6.05;
  for (const t of cfg.checks) { cy += checkItem(s, rx + 1.35, cy, rw - 1.55, t, cfg.color, cfg.checkMark, 12.5) + 0.04; }
  if (cfg.footnote) txt(s, cfg.footnote, rx + 1.35, cy + 0.01, rw - 1.55, 0.32, { fontSize: 10.5, color: C.gray, name: "footnote" });
  if (cfg.warn) warnBox(s, rx, 6.88, rw, 0.42, cfg.warn);
  footer(s, n);
  if (cfg.notes) s.addNotes(cfg.notes);
  return s;
}
function motionV2(n, cfg) {
  const s = newSlide(n);
  s.background = { color: C.white };
  header(s, cfg.code, cfg.color, cfg.title, { fs: 28 });
  cfg.strip.forEach((v, i) => {
    const x = 0.5 + i * 3.13;
    imgPanel(s, x, 1.45, 2.93, 2.42, v.f, null);
    txt(s, v.t, x, 3.94, 2.93, 0.38, { fontSize: 12.5, bold: true, align: "center", name: "motion" + i });
    if (i < cfg.strip.length - 1) s.addShape(pres.ShapeType.rightArrow, { x: x + 2.95, y: 2.5, w: 0.16, h: 0.26, fill: { color: cfg.color }, line: { type: "none" } });
  });
  txt(s, cfg.rev, 0.5, 4.35, 12.33, 0.36, { fontSize: 13, bold: true, color: C.gray, align: "center", name: "rev" });
  label(s, 0.5, 4.95, "本步销轴（既有锁销只移插，不重复消耗）", cfg.color);
  let y = 5.34;
  for (const p of cfg.parts) { partChipV2(s, 0.5, y, 5.9, p[0], p[1], p[2], p[3]); y += 0.52; }
  rrect(s, 6.85, 4.95, 5.98, 1.95, C.greenT, null, 0, 0.08);
  txt(s, "通过标准（待现场验收）", 7.15, 5.12, 5.4, 0.36, { fontSize: 14, bold: true, color: C.greenD, name: "passH" });
  y = 5.54;
  cfg.checks.forEach(t => { y += checkItem(s, 7.15, y, 5.4, t, C.green, "ok", 13) + 0.08; });
  footer(s, n);
  if (cfg.notes) s.addNotes(cfg.notes);
}

// ======================= 1 封面 =======================
{
  const s = newSlide(1);
  s.background = { color: C.yellow };
  for (let i = 0; i < 12; i++) circ(s, 0.62 + i * 1.06, 0.14, 0.42, "E8B800", C.yellowD, 1);
  txt(s, "R1-V6 三方案总装说明书", 0.5, 0.85, 12.33, 0.9, { fontSize: 40, bold: true, name: "coverTitle" });
  txt(s, "V2 工程修订版｜F07 / F09 / SCZ 缩比机械原理模型", 0.5, 1.83, 12.33, 0.46, { fontSize: 19, bold: true, name: "coverSub" });
  txt(s, "基准：本地 R1-V6.1 CAD（可拆顶盖）｜GitHub 仍为 R1-V6｜实物装配与动作验收待现场进行", 0.5, 2.3, 12.33, 0.3, { fontSize: 12.5, color: C.black, name: "coverVer" });
  const cards = [
    { f: "F07_view_open.png", c: C.red, t: "F07 · 单柱抬升" },
    { f: "F09_view_open.png", c: C.blue, t: "F09 · 双柱龙门" },
    { f: "SCZ_view_open.png", c: C.green, t: "SCZ · 剪叉机构" },
  ];
  cards.forEach((cd, i) => {
    const x = 0.5 + i * 4.19;
    rrect(s, x, 2.78, 3.95, 3.18, C.white, null, 0, 0.09);
    fitImg(s, cd.f, x + 0.13, 2.9, 3.69, 2.94);
    brick(s, x + 0.72, 6.14, 2.5, 0.52, cd.c, cd.t, { fs: 13.5 });
  });
  txt(s, "按步骤装配 · 先试配后锁紧 · 先F07后F09再SCZ", 0.5, 6.85, 12.33, 0.32, { fontSize: 13.5, bold: true, align: "center", name: "coverTag" });
  txt(s, "github.com/CodyNing-desi/foldable-3d-printer（round1-demo-cad @ d35cbd1）", 0.5, 7.24, 7.5, 0.22, { fontSize: 8.5, color: "7A6200", name: "repo" });
  txt(s, "01 / 41", 12.28, 7.24, 0.6, 0.22, { fontSize: 8.5, color: "7A6200", align: "right", name: "pg" });
  s.addNotes("V2 版本声明：本地 V6.1 CAD 已完成并通过 L1-L3 验证，但未推送 GitHub、未实际打印。用户确认打印任务完成，不据此宣称三套均已装配验收。");
}

// ======================= 2 使用方式 =======================
{
  const s = newSlide(2);
  s.background = { color: C.white };
  header(s, "指南", C.black, "这份说明书怎么用", { fs: 28 });
  rrect(s, 0.5, 1.45, 6.0, 4.35, C.white, C.line, 1, 0.08);
  const items = ["先按方案分拣零件；", "先做L4接口试配；", "按步骤装配F07；", "再装F09；", "最后装SCZ；", "每装完一步都做动作检查；", "不要一上来就把全部卡圈锁死。"];
  let y = 1.72;
  items.forEach((t, i) => { y += numItem(s, 0.8, y, 5.4, i + 1, t, i === 6 ? C.red : C.black, 14) + 0.15; });
  rrect(s, 6.85, 1.45, 5.98, 4.35, C.light, null, 0, 0.08);
  txt(s, "版本与边界（先看）", 7.15, 1.7, 5.4, 0.4, { fontSize: 16, bold: true, name: "verH" });
  const vers = [
    "本版按本地 V6.1 CAD 编制：顶盖 CAP 为独立销接件。",
    "V6.1 未推送 GitHub；公开分支仍是 R1-V6（d35cbd1）。",
    "CAP 尚未实际打印；配合、保持与全行程均待现场验收。",
    "若手上是 V6 一体塔，不要按本版强行套装，先核对版本。",
  ];
  y = 2.25;
  vers.forEach(t => { y += checkItem(s, 7.15, y, 5.35, t, C.lgray, null, 13) + 0.14; });
  const flow = [["分拣", C.lgray, C.white], ["试配", C.yellow, C.black], ["F07", C.red, C.white], ["F09", C.blue, C.white], ["SCZ", C.green, C.white], ["验收", C.black, C.white]];
  flow.forEach((f, i) => {
    const x = 0.5 + i * 2.07;
    s.addShape(pres.ShapeType.chevron, { x, y: 6.05, w: 1.95, h: 0.72, fill: { color: f[1] }, line: { type: "none" } });
    txt(s, f[0], x + 0.18, 6.05, 1.7, 0.72, { fontSize: 14, bold: true, color: f[2], align: "center", valign: "middle", name: "flow" + f[0] });
  });
  footer(s, 2);
}

// ======================= 3 工具 =======================
{
  const s = newSlide(3);
  s.background = { color: C.white };
  header(s, "准备", C.yellow, "装配前准备", { tc: C.black, fs: 28 });
  rrect(s, 0.5, 1.45, 6.0, 4.6, C.white, C.line, 1, 0.08);
  txt(s, "工具", 0.8, 1.7, 3, 0.4, { fontSize: 16, bold: true, name: "toolsH" });
  const tools = ["镊子 / 小平口起子（拆卡圈）", "游标卡尺（测孔径/槽宽）", "去毛刺工具 / 美工刀", "贴纸 / 记号笔（标记版本与档位）", "收纳盒 4 个"];
  let y = 2.3;
  tools.forEach((t, i) => { circ(s, 0.82, y + 0.08, 0.16, [C.red, C.blue, C.green, C.yellow, C.black][i]); txt(s, t, 1.15, y, 5.1, 0.4, { fontSize: 14, valign: "middle", name: "tool" + i }); y += 0.7; });
  txt(s, "收纳盒 ×4（贴好标签）", 6.85, 1.7, 5.9, 0.4, { fontSize: 16, bold: true, name: "boxH" });
  const boxes = [
    { t: "L4-TEST", sub: "接口试配件", c: C.yellow, tint: C.yellowT },
    { t: "F07", sub: "单柱抬升", c: C.red, tint: C.redT },
    { t: "F09", sub: "双柱龙门", c: C.blue, tint: C.blueT },
    { t: "SCZ", sub: "剪叉机构", c: C.green, tint: C.greenT },
  ];
  boxes.forEach((b, i) => {
    const x = 6.85 + (i % 2) * 3.13, yy = 2.3 + Math.floor(i / 2) * 1.95;
    for (let k = 0; k < 4; k++) circ(s, x + 0.5 + k * 0.62, yy - 0.1, 0.2, b.tint, b.c, 1);
    rrect(s, x, yy, 2.85, 1.62, b.tint, b.c, 1.2, 0.07);
    txt(s, b.t, x, yy + 0.32, 2.85, 0.5, { fontSize: 19, bold: true, color: b.c === C.yellow ? C.yellowD : b.c, align: "center", fontFace: M, name: "box" + b.t });
    txt(s, b.sub, x, yy + 0.92, 2.85, 0.35, { fontSize: 11.5, color: C.gray, align: "center", name: "boxsub" });
  });
  rrect(s, 0.5, 6.35, 12.33, 0.6, C.tip, null, 0, 0.06);
  txt(s, "提示：打印件先去毛刺；V6 一体塔与 V6.1 可拆顶盖不要混装。", 0.8, 6.35, 11.8, 0.6, { fontSize: 13.5, bold: true, valign: "middle", name: "tip3" });
  footer(s, 3);
}

// ======================= 4 原则 =======================
{
  const s = newSlide(4);
  s.background = { color: C.white };
  header(s, "原则", C.black, "总装总原则", { fs: 28 });
  rrect(s, 0.5, 1.45, 6.0, 3.95, C.greenT, null, 0, 0.08);
  brick(s, 0.8, 1.72, 1.5, 0.5, C.green, "要做", { fs: 15 });
  const dos = ["先装主体，再装锁销", "先插销，再试动作", "卡圈最后再完全锁紧", "先完成一套样机再并行复制经验"];
  let y = 2.5;
  dos.forEach(t => { y += checkItem(s, 0.85, y, 5.3, t, C.green, "ok", 14) + 0.2; });
  rrect(s, 6.85, 1.45, 5.98, 3.95, C.redT, null, 0, 0.08);
  brick(s, 7.15, 1.72, 1.8, 0.5, C.red, "不要做", { fs: 15 });
  const donts = ["不要混用不同方案/版本零件", "不要没试配就全部卡死", "不要强压、加热变形或强行钻孔", "不要把“已打印”当作“已验收”"];
  y = 2.5;
  donts.forEach(t => { y += checkItem(s, 7.2, y, 5.3, t, C.red, "no", 14) + 0.2; });
  txt(s, "优先顺序", 0.5, 5.62, 12.33, 0.4, { fontSize: 15, bold: true, color: C.gray, align: "center", name: "prioL" });
  const seq = [["F07", C.red], ["F09", C.blue], ["SCZ", C.green]];
  const bw = 2.3, aw = 0.75, total = 3 * bw + 2 * aw, x0 = (W - total) / 2;
  seq.forEach((q, i) => {
    const x = x0 + i * (bw + aw);
    brick(s, x, 6.1, bw, 0.72, q[1], q[0], { fs: 20 });
    if (i < 2) s.addShape(pres.ShapeType.rightArrow, { x: x + bw + 0.12, y: 6.31, w: aw - 0.24, h: 0.3, fill: { color: C.lgray }, line: { type: "none" } });
  });
  footer(s, 4);
}

// ======================= 5 分拣 =======================
{
  const s = newSlide(5);
  s.background = { color: C.white };
  header(s, "分拣", C.yellow, "先把零件分成四盒", { tc: C.black, fs: 28 });
  const cols = [
    { t: "L4 试件", c: C.yellow, tc: C.black, parts: [["CP-PIN5-LADDER", "销孔阶梯"], ["CP-SLIDER-BASE", "滑槽底座"], ["CP-HINGE-CLEVIS", "铰链叉耳"]] },
    { t: "F07", c: C.red, tc: C.white, parts: [["BASE", "底座"], ["TWR", "导向塔"], ["CAP", "可拆顶盖"], ["CAR", "滑座"], ["COL", "立柱"], ["ARM", "X臂"]] },
    { t: "F09", c: C.blue, tc: C.white, parts: [["BASE", "底座"], ["TWR ×2", "导向塔"], ["CAP ×2", "顶盖"], ["CAR ×2", "滑座"], ["COL ×2", "立柱"], ["SYNC", "同步杆"], ["XBAR", "顶横梁"], ["BRG", "中横梁"]] },
    { t: "SCZ", c: C.green, tc: C.white, parts: [["BASE", "底座"], ["POST ×2", "固定支座"], ["ARM ×4", "剪叉臂"], ["SLB ×2", "底滑块"], ["SLT ×2", "顶滑块"], ["PLAT", "顶部平台"]] },
  ];
  cols.forEach((col, i) => {
    const x = 0.5 + i * 3.13;
    brick(s, x, 1.5, 2.93, 0.55, col.c, col.t, { fs: 15, tc: col.tc });
    rrect(s, x, 2.2, 2.93, 4.15, C.white, C.line, 1, 0.07);
    let y = 2.45;
    col.parts.forEach(p => {
      txt(s, p[0], x + 0.18, y, 1.36, 0.36, { fontSize: i === 0 ? 10.5 : 11, fontFace: M, bold: true, valign: "middle", name: "sort" + p[0] });
      txt(s, p[1], x + 1.56, y, 1.28, 0.36, { fontSize: 10.5, color: C.gray, valign: "middle", name: "sortcn" });
      y += 0.48;
    });
  });
  rrect(s, 0.5, 6.5, 12.33, 0.5, C.light, null, 0, 0.06);
  txt(s, "读编号：PIN3-L14 = Ø3销轴、长14mm；CLIP3 = 配套卡圈。销轴与卡圈也按方案分开放。", 0.75, 6.5, 11.85, 0.5, { fontSize: 12.5, align: "center", valign: "middle", name: "sortNote" });
  footer(s, 5);
}

// ======================= 6 L4 总览 =======================
{
  const s = newSlide(6);
  s.background = { color: C.white };
  header(s, "L4", C.yellow, "先做L4接口试配", { tc: C.black, fs: 28 });
  const tests = [
    { t: "Ø5销孔\n转动试配", p: "CP-PIN5-LADDER" },
    { t: "滑槽试配", p: "CP-SLIDER-BASE" },
    { t: "SCZ孔系\n试配", p: "CP-SCZ-HOLES" },
    { t: "卡圈保持\n试配", p: "CP-CLIP-BOARD" },
  ];
  tests.forEach((t, i) => {
    const x = 0.5 + i * 3.13;
    rrect(s, x, 1.5, 2.93, 2.95, C.white, C.line, 1, 0.08);
    circ(s, x + 1.09, 1.78, 0.75, C.yellow);
    txt(s, String(i + 1), x + 1.09, 1.78, 0.75, 0.75, { fontSize: 26, bold: true, color: C.black, align: "center", valign: "middle", name: "l4num" });
    txt(s, t.t, x + 0.15, 2.72, 2.63, 0.85, { fontSize: 15, bold: true, align: "center", name: "l4t" });
    txt(s, t.p, x + 0.15, 3.72, 2.63, 0.4, { fontSize: 10, fontFace: M, color: C.gray, align: "center", name: "l4p" });
  });
  rrect(s, 0.5, 4.85, 12.33, 1.55, C.tip, null, 0, 0.08);
  txt(s, "结论", 0.85, 5.1, 2, 0.4, { fontSize: 15, bold: true, color: C.yellowD, name: "l4concH" });
  txt(s, "L4试配的目的是判断“能不能装、能不能动、会不会掉”，不是追求最终整机效果。", 0.85, 5.52, 11.6, 0.7, { fontSize: 15, bold: true, name: "l4conc" });
  footer(s, 6);
}

// ======================= 7-9 L4 试配 =======================
stepV2(7, {
  code: "T1", color: C.yellow, tc: C.black, title: "Ø5销孔转动试配",
  parts: [["CP-PIN5-LADDER", "×1", null, "PLA"], ["CP-PIN5", "×1", null, "PETG"], ["CP-CLIP5", "×1", "clip_3_seated.png", "PETG"]],
  steps: ["CP-PIN5 逐孔插入不同孔径档位；", "尾槽露出后，侧向卡入 CP-CLIP5；", "每档手动转动10次，记录过紧/晃动。"],
  checks: ["转动顺畅、径向晃动 ≤0.3mm；", "勾选最佳孔位：+0.2 / +0.3 / +0.4 / +0.5。"],
  image: "coupon_T1.png",
  caption: "真实试件：橙=销，红=卡圈；记录最佳孔径档并回写建模组",
  notes: "试配图中的 CP-PIN5 缩略图仅作销轴类型参考，实际使用 CP-PIN5（Ø5×16），不要用 PIN5-L34 长销代替。",
});
stepV2(8, {
  code: "T2", color: C.yellow, tc: C.black, title: "滑槽试配",
  parts: [["CP-SLIDER-BASE", "×1", null, "PLA"], ["CP-SLIDER-TONGUES", "×1", null, "PETG"]],
  steps: ["舌板插入滑槽；", "全程来回滑动20次，逐档试6.2/6.4/6.6槽宽。"],
  checks: ["顺滑无卡滞，侧隙 ≤0.4mm；", "记录：顺滑 / 偏紧 / 卡死 / 偏松。"],
  image: "coupon_T2.png",
  caption: "真实试件：橙=舌板，灰=滑槽底座",
});
stepV2(9, {
  code: "T3", color: C.yellow, tc: C.black, title: "SCZ孔系与卡圈试配",
  parts: [["CP-SCZ-HOLES", "×1", null, "PLA"], ["CP-PIN4", "×1", null, "PETG"], ["CP-CLIP4", "×1", "clip_3_seated.png", "PETG"], ["CP-CLIP-BOARD", "×1", null, "PLA"]],
  steps: ["CP-PIN4 逐档试插并装 CP-CLIP4；", "卡圈试板反复拆装10次；", "孔系往返摆动50次，检查扩孔/开裂。"],
  checks: ["插销顺利、卡圈不脱、孔边不裂；", "失效零件单独编号，标记“保持不足”。"],
  image: "coupon_T3.png",
  caption: "真实试件：左=Ø4孔系，右=卡圈试板",
});

// ======================= 10 销轴速查 =======================
{
  const s = newSlide(10);
  s.background = { color: C.white };
  header(s, "销轴", C.black, "销轴编号速查（按长度防混用）", { fs: 28 });
  const pins = [
    ["PIN3-L14", "Ø3 × 14 mm", "塔足固定 / 顶盖CAP", "F07/F09"],
    ["PIN3-L18", "Ø3 × 18 mm", "SYNC同步杆 / BRG", "F09"],
    ["PIN3-L22", "Ø3 × 22 mm", "XBAR顶横梁", "F09"],
    ["PIN3-L26", "Ø3 × 26 mm", "导柱抬升锁位", "F07/F09"],
    ["PIN3-L34", "Ø3 × 34 mm", "根部/臂0°↔90°移插锁销", "F07/F09"],
    ["PIN4-L16", "Ø4 × 16 mm", "臂B上下 / 中心铰", "SCZ"],
    ["PIN4-L18", "Ø4 × 18 mm", "臂A底部 / 臂A顶部", "SCZ"],
    ["PIN5-L34", "Ø5 × 34 mm", "根部主转轴 / 臂主转轴", "F07/F09"],
    ["PIN25-L10", "Ø2.5 × 10 mm", "SHB/SHT横销防转", "SCZ"],
  ];
  pins.forEach((p, i) => {
    const x = 0.5 + (i % 3) * 4.19, y = 1.45 + Math.floor(i / 3) * 1.78;
    rrect(s, x, y, 3.95, 1.62, C.white, C.line, 1, 0.07);
    fitImg(s, `pin_${p[0]}.png`, x + 0.12, y + 0.1, 0.85, 1.4);
    txt(s, p[0], x + 1.1, y + 0.12, 2.7, 0.3, { fontSize: 14, fontFace: M, bold: true, name: "pinref" + p[0] });
    txt(s, p[1], x + 1.1, y + 0.46, 2.7, 0.28, { fontSize: 14, bold: true, color: C.redD, name: "pinsize" });
    txt(s, p[2], x + 1.1, y + 0.79, 2.7, 0.34, { fontSize: 11, color: C.black, name: "pinuse" });
    txt(s, p[3] + " · PETG", x + 1.1, y + 1.22, 2.7, 0.22, { fontSize: 10, color: C.gray, name: "pincand" });
  });
  txt(s, "同直径不同长度不得混用；PIN25-L10 为带头横销但无独立 CLIP25，保持待验证；锁销移插不重复消耗。", 0.5, 6.85, 12.33, 0.28, { fontSize: 12, color: C.gray, align: "center", name: "pinNote" });
  footer(s, 10);
}

// ======================= 11 卡圈方法 =======================
{
  const s = newSlide(11);
  s.background = { color: C.white };
  header(s, "卡圈", C.black, "卡圈怎么装（销轴尾槽 + 侧向卡入）", { fs: 28 });
  const cards = [
    ["clip_1_groove.png", "① 找尾槽", "卡圈只能卡在销轴尾端环形槽内，不是随便夹在光轴上。"],
    ["clip_2_approach.png", "② 侧向推入", "卡圈开口朝向销轴，沿径向推入；不要从销轴端面轴向硬套。"],
    ["clip_3_seated.png", "③ 到位判断", "卡圈整圈进入槽底，轻拉销轴不脱出；可用小平口起子辅助拆卸。"],
    ["clip_4_wrong.png", "④ 错误示例", "卡在光轴中段、未入槽、半挂槽口都算未装好，必须重装。"],
  ];
  cards.forEach((cd, i) => {
    const x = 0.5 + (i % 2) * 6.33, y = 1.45 + Math.floor(i / 2) * 2.68;
    rrect(s, x, y, 6.0, 2.45, C.white, C.line, 1, 0.08);
    fitImg(s, cd[0], x + 0.12, y + 0.12, 2.45, 2.2);
    txt(s, cd[1], x + 2.75, y + 0.2, 3.0, 0.4, { fontSize: 16, bold: true, color: i === 3 ? C.redD : C.black, name: "clipH" + i });
    txt(s, cd[2], x + 2.75, y + 0.7, 3.0, 1.5, { fontSize: 13, color: C.black, name: "clipT" + i });
  });
  txt(s, "卡圈为 PETG 易损件，按 BOM 数量×2准备备件；反复拆装后开裂或保持力下降就更换。", 0.5, 6.85, 12.33, 0.28, { fontSize: 12, color: C.gray, align: "center", name: "clipNote" });
  footer(s, 11);
}

// ======================= 12 返工流程 =======================
{
  const s = newSlide(12);
  s.background = { color: C.white };
  header(s, "返工", C.red, "零件装不上 / 出问题怎么处理", { fs: 28 });
  const flow = ["零件装不上", "检查编号", "检查版本", "去毛刺", "测量尺寸", "判定返工"];
  flow.forEach((t, i) => {
    const x = 0.5 + i * 2.07;
    s.addShape(pres.ShapeType.chevron, { x, y: 1.65, w: 1.95, h: 0.85, fill: { color: i === 5 ? C.red : C.lgray }, line: { type: "none" } });
    txt(s, t, x + 0.1, 1.65, 1.75, 0.85, { fontSize: 14, bold: true, color: C.white, align: "center", valign: "middle", name: "rework" + i });
  });
  const stops = [
    ["版本不符", "V6 一体塔与 V6.1 可拆顶盖混用：停止该机构装配，核对 STL/STEP 版本。"],
    ["结构干涉", "去毛刺、测孔后仍装不进或全行程强卡滞：停止，不扩孔、不强压，反馈建模组。"],
    ["销轴/卡圈保持不足", "记录编号与失效形式；Ø2.5 横销无独立卡圈，靠压入配合，需实物验证。"],
  ];
  stops.forEach((t, i) => {
    const x = 0.5 + i * 4.19;
    rrect(s, x, 3.05, 3.95, 2.65, C.white, C.line, 1, 0.08);
    brick(s, x + 0.25, 3.3, 1.45, 0.45, C.red, "停止", { fs: 13 });
    txt(s, t[0], x + 0.25, 3.95, 3.45, 0.4, { fontSize: 16, bold: true, name: "stopH" + i });
    txt(s, t[1], x + 0.25, 4.45, 3.45, 1.05, { fontSize: 13, name: "stopT" + i });
  });
  txt(s, "禁止用强压、加热变形或强行钻孔掩盖 CAD 问题；返工后重新执行对应步骤与动作检查。", 0.5, 6.15, 12.33, 0.5, { fontSize: 14, bold: true, color: C.redD, align: "center", name: "reworkNote" });
  footer(s, 12);
}

// ======================= 总览页 =======================
function overviewV2(n, cfg) {
  const s = newSlide(n);
  s.background = { color: C.white };
  header(s, cfg.code, cfg.color, cfg.title, { fs: 28 });
  txt(s, cfg.intro, 0.5, 1.5, 4.05, 0.85, { fontSize: 14, name: "ovintro" });
  let y = 2.5;
  cfg.features.forEach(t => { y += checkItem(s, 0.55, y, 3.9, t, cfg.color, "ok", 14) + 0.14; });
  rrect(s, 0.5, y + 0.2, 4.05, 1.15, C.light, null, 0, 0.07);
  txt(s, cfg.partsText, 0.72, y + 0.36, 3.65, 0.85, { fontSize: 12.5, color: C.gray, name: "ovparts" });
  imgPanel(s, 4.85, 1.5, 7.98, 4.11, cfg.sheet, cfg.sheetCap);
  rrect(s, 4.85, 6.15, 7.98, 0.72, cfg.tint, null, 0, 0.06);
  txt(s, cfg.callout, 5.15, 6.15, 7.4, 0.72, { fontSize: 13.5, bold: true, color: cfg.callColor, valign: "middle", name: "ovcall" });
  footer(s, n);
  if (cfg.notes) s.addNotes(cfg.notes);
}

// ======================= 13 F07 总览 =======================
overviewV2(13, {
  code: "F07", color: C.red, title: "F07 单柱抬升机构",
  intro: "F07结构最简单，适合作为第一套样机。按本页零件核对后再开始。",
  features: ["X臂折叠", "滑座抬升", "根部前翻"],
  partsText: "构成：BASE / BED(可选) / TWR / CAP / CAR / COL / ARM + 销轴卡圈。V6.1 顶盖 CAP 为独立件。",
  sheet: "F07_contact_sheet.png", sheetCap: "F07 动作状态拼图（真实CAD）",
  tint: C.redT, callColor: C.redD,
  callout: "先塔后滑座，再锁顶盖；锁销在0°/90°孔间移插。",
});

// ======================= 14-18 F07 =======================
stepV2(14, {
  code: "F07-1", color: C.red, title: "底座 + 导向塔",
  parts: [["F07-BASE", "×1", "part_F07_BASE.png", "PLA"], ["F07-BED", "可选×1", "part_F07_BED.png", "PLA"], ["F07-TWR", "×1", "part_F07_TWR.png", "PLA"], ["F07-PIN3-L14", "×4", "pin_PIN3-L14.png", "PETG · 塔足"], ["F07-CLIP3", "×4", "clip_3_seated.png", "PETG · 底面"]],
  steps: ["平放 BASE，BED 搁在床支撑墙顶（可选）。", "TWR 对准中央塔位；4根 PIN3-L14 自上而下穿塔足+底座。", "翻转底座，在底面让位坑内卡入4个 CLIP3。"],
  checks: ["塔垂直、四脚稳固；", "4个卡圈均进入销轴尾槽。"],
  image: "F07_1_triptych.png",
  caption: "塔足 PIN3-L14×4：自上而下插入，底面坑内卡圈",
});
stepV2(15, {
  code: "F07-2A", color: C.red, title: "试装滑座 CAR",
  parts: [["F07-CAR", "×1", "part_F07_CAR.png", "PLA · 旋钮朝后"]],
  steps: ["CAR 从导柱顶端套入，旋钮朝后（背面）。", "不装顶盖，上下推动数次，检查双轴套配合。"],
  checks: ["能套入、能全程滑动、无强卡滞；", "装不进则停：去毛刺、测孔，不掰导柱。"],
  image: "F07_2A_triptych.png",
  caption: "V6.1 顶盖未装，CAR 可从上方套入；试配合格再进 F07-2B",
});
stepV2(16, {
  code: "F07-2B", color: C.red, title: "锁可拆顶盖 CAP",
  parts: [["F07-CAP", "×1", "part_F07_CAP.png", "PLA"], ["F07-PIN3-L14", "×2", "pin_PIN3-L14.png", "PETG · 顶盖"], ["F07-CLIP3", "×2", "clip_3_seated.png", "PETG · 外侧"]],
  steps: ["CAP 套入两导柱顶端，底面与塔顶贴合。", "2根 PIN3-L14 沿X横穿顶盖+导柱 z65 孔。", "两端外侧各卡入1个 CLIP3，轻拉顶盖确认不脱落。"],
  checks: ["顶盖不晃、销轴尾槽露出；", "CAR 仍能沿导柱全程滑动。"],
  image: "F07_2B_triptych.png",
  caption: "每塔顶盖消耗 PIN3-L14×2 + CLIP3×2；与塔足4根分开核对",
});
stepV2(17, {
  code: "F07-3", color: C.red, title: "立柱根部主转轴 + 0°锁销",
  parts: [["F07-COL", "×1", "part_F07_COL.png", "PLA"], ["F07-PIN5-L34", "×1", "pin_PIN5-L34.png", "PETG · 主转轴"], ["F07-CLIP5", "×1", "clip_3_seated.png", "PETG"], ["F07-PIN3-L34", "×1", "pin_PIN3-L34.png", "PETG · 0°锁销"], ["F07-CLIP3", "×1", "clip_3_seated.png", "PETG"]],
  steps: ["COL 根舌插入 CAR 叉耳；PIN5-L34 沿Y横穿，尾端卡 CLIP5。", "0°锁销 PIN3-L34 插 (14,·,11) 孔并卡 CLIP3；动作测试时拔出移插90°孔。"],
  checks: ["拔锁销后 COL 能绕根部转动；", "0°/90°锁孔均能插入锁销。"],
  image: "F07_3_triptych.png",
  caption: "主转轴 Ø5 与锁销 Ø3 不混用；锁销后续移插，不重复消耗",
});
stepV2(18, {
  code: "F07-4", color: C.red, title: "X臂主转轴 + 展开锁销",
  parts: [["F07-ARM", "×1", "part_F07_ARM.png", "PLA"], ["F07-PIN5-L34", "×1", "pin_PIN5-L34.png", "PETG · 主转轴"], ["F07-CLIP5", "×1", "clip_3_seated.png", "PETG"], ["F07-PIN3-L34", "×1", "pin_PIN3-L34.png", "PETG · 0°锁销"], ["F07-CLIP3", "×1", "clip_3_seated.png", "PETG"]],
  steps: ["ARM 根舌插入 COL 柱顶叉耳；PIN5-L34 沿Y横穿，卡 CLIP5。", "0°锁销 PIN3-L34 插臂锁孔并卡 CLIP3；下折前拔出，折后移插90°孔。"],
  checks: ["拔锁销后 X臂可向下折；", "展开与下折锁孔均能对上。"],
  image: "F07_4_triptych.png",
  caption: "F07 的臂铰在柱顶；不要按 F09 的 BRG 中央叉耳操作",
});
motionV2(19, {
  code: "F07-5", color: C.red, title: "F07整套动作测试（锁销移插）",
  strip: [
    { f: "F07_view_open.png", t: "起始 · 展开锁位" },
    { f: "F07_view_armfold.png", t: "① 拔臂锁销→下折90°" },
    { f: "F07_view_lifted.png", t: "② 抬升→顶孔插L26" },
    { f: "F07_view_folded.png", t: "③ 拔根锁销→前翻90°" },
  ],
  rev: "锁销在同一根的0°/90°孔间移插；④ 逆向恢复（先根部→再滑座→最后X臂）",
  parts: [["F07-PIN3-L26", "×2", "pin_PIN3-L26.png", "PETG · 导柱锁位"], ["F07-CLIP3", "×2", "clip_3_seated.png", "PETG · 锁位卡圈"]],
  checks: ["臂折/抬升/前翻均完成；", "各锁位能插，逆向恢复正常；", "全行程无强卡滞。"],
  notes: "抬升后用 PIN3-L26 横穿导柱 z48 锁孔并卡 CLIP3；臂和根的 PIN3-L34 锁销移插到90°孔，不新增。",
});

// ======================= 20 F09 总览 =======================
overviewV2(20, {
  code: "F09", color: C.blue, title: "F09 双柱龙门机构",
  intro: "F09比F07多了双侧同步、顶/中横梁与中央X臂。注意顶盖在 SYNC 之后锁。",
  features: ["双侧同步抬升；", "顶横梁 XBAR；", "中横梁 BRG；", "中央X臂连接。"],
  partsText: "构成：BASE/BED(可选) + TWR×2 + CAP×2 + CAR×2 + COL×2 + SYNC + XBAR + BRG + ARM。",
  sheet: "F09_contact_sheet.png", sheetCap: "F09 动作状态拼图（真实CAD）",
  tint: C.blueT, callColor: C.blueD,
  callout: "顺序关键：双滑座→SYNC→双立柱→顶盖→横梁→中央X臂。",
});

// ======================= 21-29 F09 =======================
stepV2(21, {
  code: "F09-1", color: C.blue, title: "底座 + 双导向塔",
  parts: [["F09-BASE", "×1", "part_F09_L82_BASE.png", "PLA"], ["F09-BED", "可选×1", "part_F09_L82_BED.png", "PLA"], ["F09-TWR", "×2", "part_F09_L82_TWR.png", "PLA"], ["F09-PIN3-L14", "×8", "pin_PIN3-L14.png", "PETG · 塔足"], ["F09-CLIP3", "×8", "clip_3_seated.png", "PETG · 底面"]],
  steps: ["左右各装1座 TWR（y=±65），每塔4根 PIN3-L14 自上而下穿塔足+底座。", "翻转底座，在底面让位坑内卡入8个 CLIP3。", "床板 BED 可选，搁在床支撑墙顶。"],
  checks: ["两塔平行、高度一致；", "8个卡圈全部进入尾槽。"],
  image: "F09_1_triptych.png",
  caption: "塔足共用 PIN3-L14×8 + CLIP3×8；顶盖销轴在 F09-3C 另计",
});
stepV2(22, {
  code: "F09-2", color: C.blue, title: "试装双滑座 CAR",
  parts: [["F09-CAR", "×2", "part_F09_L82_CAR.png", "PLA · 旋钮朝后"]],
  steps: ["左右 CAR 分别从各自导柱顶端套入，旋钮朝后。", "暂不装顶盖和 SYNC，分别上下推动测试。"],
  checks: ["左右均能套入并全程滑动；", "两侧手感一致，无强卡滞。"],
  image: "F09_2_triptych.png",
  caption: "任一侧装不进：暂停，去毛刺/测孔，不强行掰导柱",
});
stepV2(23, {
  code: "F09-3A", color: C.blue, title: "安装 SYNC 同步杆",
  parts: [["F09-SYNC", "×1", "part_F09_L82_SYNC.png", "PLA"], ["F09-PIN3-L18", "×4", "pin_PIN3-L18.png", "PETG · 每座2根"], ["F09-CLIP3", "×4", "clip_3_seated.png", "PETG"]],
  steps: ["SYNC 从上方套过两塔内侧导柱，放到两滑座顶面。", "每座用2根 PIN3-L18 沿X穿滑座凸台+SYNC杆端，共4根，卡 CLIP3。"],
  checks: ["推一侧滑座，另一侧跟随；", "SYNC 两端贴合，无翘曲。"],
  image: "F09_3A_triptych.png",
  caption: "SYNC 必须越过导柱，所以顶盖 CAP 留到 F09-3C 才锁",
});
stepV2(24, {
  code: "F09-3B", color: C.blue, title: "安装两根 COL 立柱",
  parts: [["F09-COL", "×2", "part_F09_L82_COL.png", "PLA"], ["F09-PIN5-L34", "×2", "pin_PIN5-L34.png", "PETG · 主转轴"], ["F09-CLIP5", "×2", "clip_3_seated.png", "PETG"], ["F09-PIN3-L34", "×2", "pin_PIN3-L34.png", "PETG · 0°锁销"], ["F09-CLIP3", "×2", "clip_3_seated.png", "PETG"]],
  steps: ["左右 COL 根舌分别插入滑座叉耳，各用1根 PIN5-L34 沿Y横穿并卡 CLIP5。", "每侧插0°锁销 PIN3-L34（(14,·,11)孔）并卡 CLIP3。"],
  checks: ["两柱姿态一致，能绕根部转动；", "0°/90°锁孔均可插。"],
  image: "F09_3B_triptych.png",
  caption: "主转轴 PIN5-L34×2、锁销 PIN3-L34×2，卡圈分别对应 CLIP5/CLIP3",
});
stepV2(25, {
  code: "F09-3C", color: C.blue, title: "锁两个可拆顶盖 CAP",
  parts: [["F09-CAP", "×2", "part_F09_L82_CAP.png", "PLA"], ["F09-PIN3-L14", "×4", "pin_PIN3-L14.png", "PETG · 每塔2根"], ["F09-CLIP3", "×4", "clip_3_seated.png", "PETG"]],
  steps: ["确认 SYNC 已越过导柱后，CAP×2 分别套入两塔导柱顶端。", "每塔用2根 PIN3-L14 沿X横穿顶盖+导柱 z65 孔，共4根，卡 CLIP3。"],
  checks: ["顶盖不晃、卡圈到位；", "双滑座与 SYNC 仍能整体滑动。"],
  image: "F09_3C_triptych.png",
  caption: "顶盖共消耗 PIN3-L14×4 + CLIP3×4；与塔足8根分开核对",
});
stepV2(26, {
  code: "F09-4A", color: C.blue, title: "安装顶横梁 XBAR",
  parts: [["F09-XBAR", "×1", "part_F09_L82_XBAR.png", "PLA"], ["F09-PIN3-L22", "×2", "pin_PIN3-L22.png", "PETG · 柱顶"], ["F09-CLIP3", "×2", "clip_3_seated.png", "PETG"]],
  steps: ["XBAR 两端榫插入两柱顶端。", "每端用1根 PIN3-L22 沿X横穿柱顶榫孔，共2根，卡 CLIP3。"],
  checks: ["顶横梁平直，两端榫完全入柱；", "柱顶无张口。"],
  image: "F09_4A_triptych.png",
  caption: "XBAR 用 PIN3-L22，不要拿 SYNC/BRG 的 PIN3-L18 代替",
});
stepV2(27, {
  code: "F09-4B", color: C.blue, title: "安装中横梁 BRG",
  parts: [["F09-BRG", "×1", "part_F09_L82_BRG.png", "PLA"], ["F09-PIN3-L18", "×2", "pin_PIN3-L18.png", "PETG · 端榫"], ["F09-CLIP3", "×2", "clip_3_seated.png", "PETG"]],
  steps: ["BRG 两端榫插入两柱内壁 z132 让位槽，中央叉耳朝前、位于 y=0。", "每端用1根 PIN3-L18 沿Y横穿，共2根，卡 CLIP3。"],
  checks: ["中横梁平直，中央叉耳方向正确；", "端榫到底、锁孔对齐。"],
  image: "F09_4B_triptych.png",
  caption: "BRG 中央叉耳是中央X臂的铰点；下一步不要装到柱顶",
});
stepV2(28, {
  code: "F09-5A", color: C.blue, title: "安装 BRG 中央X臂",
  parts: [["F09-ARM", "×1", "part_F09_L82_ARM.png", "PLA"], ["F09-PIN5-L34", "×1", "pin_PIN5-L34.png", "PETG · 主转轴"], ["F09-CLIP5", "×1", "clip_3_seated.png", "PETG"], ["F09-PIN3-L34", "×1", "pin_PIN3-L34.png", "PETG · 0°锁销"], ["F09-CLIP3", "×1", "clip_3_seated.png", "PETG"]],
  steps: ["ARM 根舌插入 BRG 中央叉耳（y=0）；PIN5-L34 沿Y横穿并卡 CLIP5。", "0°锁销 PIN3-L34 插臂锁孔并卡 CLIP3；下折前拔出移插90°孔。"],
  checks: ["臂铰位于 BRG 而非柱顶；", "拔锁销后臂可下折，锁孔可插。"],
  image: "F09_5A_triptych.png",
  caption: "F09 的臂铰在 BRG 中央叉耳；F07 才在柱顶",
});
motionV2(29, {
  code: "F09-5B", color: C.blue, title: "F09全行程测试（锁销移插）",
  strip: [
    { f: "F09_view_open.png", t: "起始 · 展开锁位" },
    { f: "F09_view_armfold.png", t: "① 拔臂锁销→下折90°" },
    { f: "F09_view_lifted.png", t: "② 双座抬升→顶孔锁位" },
    { f: "F09_view_folded.png", t: "③ 拔根锁销→龙门前翻" },
  ],
  rev: "锁销在同一根的0°/90°孔间移插；④ 逆向恢复（先龙门→再双座→最后X臂）",
  parts: [["F09-PIN3-L26", "×4", "pin_PIN3-L26.png", "PETG · 每塔2根"], ["F09-CLIP3", "×4", "clip_3_seated.png", "PETG · 锁位卡圈"]],
  checks: ["左右同步，中央X臂正常；", "各锁位可插，逆向恢复；", "全行程无强卡滞。"],
  notes: "抬升41mm后，每塔2根 PIN3-L26 横穿导柱 z48 锁孔并卡 CLIP3，共4根。",
});

// ======================= 30 SCZ 总览 =======================
overviewV2(30, {
  code: "SCZ", color: C.green, title: "SCZ 剪叉机构",
  intro: "SCZ是固定端+滑动端剪叉：底部输入，顶部平台保持水平。",
  features: ["剪叉展开 / 收拢；", "底部输入；", "顶部平台保持水平。"],
  partsText: "构成：BASE/BED(可选) + POST×2 + ARM×4 + SLB×2 + SLT×2 + SHB + SHT + PLAT。",
  sheet: "SCZ_contact_sheet.png", sheetCap: "SCZ 动作状态拼图（真实CAD）",
  tint: C.greenT, callColor: C.greenD,
  callout: "臂A用 PIN4-L18，臂B与中心铰用 PIN4-L16；先分销再装。",
});

// ======================= 31-36 SCZ =======================
stepV2(31, {
  code: "SCZ-1", color: C.green, title: "底座 + 固定支座",
  parts: [["SCZ-BASE", "×1", "part_SCZ_BASE.png", "PLA"], ["SCZ-BED", "可选×1", "part_SCZ_BED.png", "PLA"], ["SCZ-POST", "×2", "part_SCZ_POST.png", "PLA"], ["SCZ-PIN3-L13", "×4", null, "PETG · 支座"], ["SCZ-CLIP3", "×4", "clip_3_seated.png", "PETG · 底面"]],
  steps: ["BASE 平放、支脚朝下，BED 可选搁在床支撑墙顶。", "左右 POST 装到 x=155、y=±71；每座2根 PIN3-L13 竖直穿过支座+底座。", "翻转底座，在底面坑内卡入4个 CLIP3。"],
  checks: ["支座垂直、固定稳定；", "横轴窗贯通，支脚能撑住底座。"],
  image: "SCZ_1_triptych.png",
  caption: "PIN3-L13 为 SCZ 支座专用长度，勿与塔足 PIN3-L14 混用",
});
stepV2(32, {
  code: "SCZ-2", color: C.green, title: "底滑块 + 臂A底部",
  parts: [["SCZ-SLB", "×2", "part_SCZ_SLB.png", "PETG · 底滑块"], ["SCZ-ARM", "×2", "part_SCZ_ARM.png", "PETG · 臂A"], ["SCZ-PIN4-L18", "×2", "pin_PIN4-L18.png", "PETG · 臂A底"], ["SCZ-CLIP4", "×2", "clip_3_seated.png", "PETG"]],
  steps: ["SLB 吊耳插入底座舌槽（y=±62.5），能沿X滑动。", "臂A底孔入滑块叉耳，每侧1根 PIN4-L18 沿Y横穿并卡 CLIP4。"],
  checks: ["滑块能沿底座移动；", "臂A能转动，卡圈入槽。"],
  image: "SCZ_2_triptych.png",
  caption: "臂A底=PIN4-L18×2 + CLIP4×2；与臂B的 PIN4-L16 分开",
});
stepV2(33, {
  code: "SCZ-3A", color: C.green, title: "底部输入轴 SHB + 横销",
  parts: [["SCZ-SHB", "×1", "part_SCZ_SHB.png", "PETG · 带旋钮"], ["SCZ-PIN25-L10", "×2", "pin_PIN25-L10.png", "PETG · 横销"], ["SCZ-CLIP4", "×2", "clip_3_seated.png", "PETG · 轴端"]],
  steps: ["SHB 从底座下方沿Y穿入两滑块吊耳，旋钮留在横轴窗内。", "轴两端各卡入1个 CLIP4（共2个），限制轴向窜动。", "每侧从下方插1根 PIN25-L10 横销，穿过滑块吊耳与轴，防止相对转动。"],
  checks: ["推拉旋钮顺畅，轴不转、不窜；", "支脚保证旋钮离桌间隙。"],
  footnote: "注意：Ø2.5横销无独立卡圈，靠压入配合，防脱保持力待实物验证。",
  image: "SCZ_3A_triptych.png",
  caption: "SHB 端部 CLIP4×2 + 横销 PIN25-L10×2；横销不虚构卡圈",
});
stepV2(34, {
  code: "SCZ-3B", color: C.green, title: "臂B底部 + 中心交叉铰",
  parts: [["SCZ-ARM", "×2", "part_SCZ_ARM.png", "PETG · 臂B"], ["SCZ-PIN4-L16", "×4", "pin_PIN4-L16.png", "PETG · 底2+中2"], ["SCZ-CLIP4", "×4", "clip_3_seated.png", "PETG"]],
  steps: ["臂B底孔装到固定支座，每侧1根 PIN4-L16 沿Y横穿并卡 CLIP4。", "臂A/臂B中心孔对齐（错层8.5mm），每侧1根 PIN4-L16 穿两臂并卡 CLIP4。"],
  checks: ["剪叉能张开/收拢；", "中心铰不松脱，孔边无裂纹。"],
  image: "SCZ_3B_triptych.png",
  caption: "本步 PIN4-L16×4：臂B底2 + 中心铰2；CLIP4×4",
});
stepV2(35, {
  code: "SCZ-4A", color: C.green, title: "顶滑块 + 臂B顶 + 顶轴 SHT",
  parts: [["SCZ-SLT", "×2", "part_SCZ_SLT.png", "PETG · 顶滑块"], ["SCZ-PIN4-L16", "×2", "pin_PIN4-L16.png", "PETG · 臂B顶"], ["SCZ-SHT", "×1", "part_SCZ_SHT.png", "PETG · 顶轴"], ["SCZ-PIN25-L10", "×2", "pin_PIN25-L10.png", "PETG · 横销"], ["SCZ-CLIP4", "×4", "clip_3_seated.png", "PETG · 销2+轴端2"]],
  steps: ["顶滑块叉耳套臂B顶孔，每侧1根 PIN4-L16 沿Y横穿并卡 CLIP4。", "SHT 沿Y穿顶滑块舌板，两端各卡1个 CLIP4。", "每侧插1根 PIN25-L10 横销，穿舌板与顶轴，防止相对转动。"],
  checks: ["顶滑块能沿臂B顶转动；", "顶轴随顶滑块移动，不松脱。"],
  footnote: "补全上版漏列：臂B顶部 PIN4-L16×2；横销保持力待实物验证。",
  image: "SCZ_4A_triptych.png",
  caption: "臂B顶 PIN4-L16×2；SHT 端部 CLIP4×2 与销轴卡圈分开计",
});
stepV2(36, {
  code: "SCZ-4B", color: C.green, title: "平台 PLAT + 臂A顶部",
  parts: [["SCZ-PLAT", "×1", "part_SCZ_PLAT.png", "PLA"], ["SCZ-PIN4-L18", "×2", "pin_PIN4-L18.png", "PETG · 臂A顶"], ["SCZ-CLIP4", "×2", "clip_3_seated.png", "PETG"]],
  steps: ["平台叉耳套臂A顶孔，每侧1根 PIN4-L18 沿Y横穿并卡 CLIP4。", "顶滑块舌板入平台底槽，SHT 落入平台边部让位槽。", "轻压平台，检查四臂同步与平台水平。"],
  checks: ["平台基本水平；", "顶滑块在平台槽内顺畅移动。"],
  image: "SCZ_4B_triptych.png",
  caption: "臂A顶 PIN4-L18×2；至此 PIN4-L18共4、PIN4-L16共6",
});

// ======================= 37 SCZ 动作测试 =======================
{
  const s = newSlide(37);
  s.background = { color: C.white };
  header(s, "SCZ-5", C.green, "SCZ整机动作测试", { fs: 28 });
  const strip = [
    { f: "SCZ_view_folded.png", t: "最低位 · 收拢" },
    { f: "SCZ_view_midfold.png", t: "中间行程" },
    { f: "SCZ_view_open.png", t: "最高位 · 展开" },
  ];
  strip.forEach((v, i) => {
    const x = 0.5 + i * 4.19;
    imgPanel(s, x, 1.45, 3.95, 2.62, v.f, null);
    txt(s, v.t, x, 4.14, 3.95, 0.34, { fontSize: 12.5, bold: true, align: "center", name: "sczstrip" + i });
    if (i < 2) s.addShape(pres.ShapeType.rightArrow, { x: x + 3.98, y: 2.6, w: 0.18, h: 0.26, fill: { color: C.green }, line: { type: "none" } });
  });
  rrect(s, 0.5, 4.75, 4.05, 2.1, C.white, C.line, 1, 0.08);
  txt(s, "动作顺序", 0.8, 4.92, 3, 0.36, { fontSize: 14, bold: true, color: C.greenD, name: "sczseqH" });
  let y = 5.32;
  ["推动底部输入轴；", "观察剪叉展开与收拢；", "测试最低位与最高位锁位。"].forEach((t, i) => { y += numItem(s, 0.8, y, 3.5, i + 1, t, C.green, 12) + 0.07; });
  rrect(s, 4.75, 4.75, 3.6, 2.1, C.white, C.line, 1, 0.08);
  txt(s, "锁位销轴", 5.05, 4.92, 3, 0.36, { fontSize: 14, bold: true, color: C.greenD, name: "sczpartsH" });
  partChipV2(s, 5.05, 5.35, 3.0, "SCZ-PIN3-L24", "×2", null, "PETG");
  partChipV2(s, 5.05, 5.87, 3.0, "SCZ-CLIP3", "×2", "clip_3_seated.png", "PETG");
  rrect(s, 8.55, 4.75, 4.28, 2.1, C.greenT, null, 0, 0.08);
  txt(s, "通过标准（待现场验收）", 8.85, 4.92, 3.8, 0.36, { fontSize: 14, bold: true, color: C.greenD, name: "sczpassH" });
  y = 5.32;
  ["平台保持水平；", "左右运动一致；", "最高 / 最低位锁位可用。"].forEach(t => { y += checkItem(s, 8.85, y, 3.7, t, C.green, "ok", 12) + 0.07; });
  txt(s, "锁销 PIN3-L24 穿底滑块耳+底座定位孔（y=±66.2 / ±58.8），底面坑内卡圈。", 0.5, 6.9, 12.33, 0.24, { fontSize: 11.5, color: C.gray, align: "center", name: "sczlock" });
  footer(s, 37);
}

// ======================= 38 验收表 =======================
{
  const s = newSlide(38);
  s.background = { color: C.white };
  header(s, "验收", C.black, "三套机构统一验收（现场填写）", { fs: 28 });
  const rows = ["零件齐全", "主运动副可动", "锁位销可插", "全行程无强卡滞", "逆向恢复正常", "无明显裂纹"];
  const head = [
    { text: "验收项目", options: { fill: { color: C.black }, color: C.white, bold: true, fontSize: 15, align: "left", valign: "middle" } },
    { text: "F07", options: { fill: { color: C.red }, color: C.white, bold: true, fontSize: 15, align: "center", valign: "middle" } },
    { text: "F09", options: { fill: { color: C.blue }, color: C.white, bold: true, fontSize: 15, align: "center", valign: "middle" } },
    { text: "SCZ", options: { fill: { color: C.green }, color: C.white, bold: true, fontSize: 15, align: "center", valign: "middle" } },
  ];
  const body = rows.map((r, i) => [
    { text: r, options: { fill: { color: i % 2 ? "F5F5F5" : C.white }, fontSize: 13.5, align: "left", valign: "middle" } },
    ...[0, 1, 2].map(() => ({ text: "□", options: { fill: { color: i % 2 ? "F5F5F5" : C.white }, fontSize: 16, align: "center", valign: "middle" } })),
  ]);
  s.addTable([head, ...body], { x: 0.7, y: 1.55, w: 11.93, colW: [5.33, 2.2, 2.2, 2.2], rowH: 0.55, fontFace: F, border: { type: "solid", color: "DDDDDD", pt: 1 }, margin: 0.08 });
  rrect(s, 0.7, 5.75, 11.93, 0.8, C.tip, null, 0, 0.06);
  txt(s, "每套先做5次轻柔往返，再做20次完整动作循环；未实测项目保持空白，不预填通过。", 1.0, 5.75, 11.3, 0.8, { fontSize: 14, bold: true, valign: "middle", align: "center", name: "accNote" });
  footer(s, 38);
}

// ======================= 39 常见问题 =======================
{
  const s = newSlide(39);
  s.background = { color: C.white };
  header(s, "排故", C.red, "常见问题怎么处理", { fs: 28 });
  const qs = [
    { t: "滑座装不进导向塔", sol: ["先核对是否为可拆顶盖版本", "去毛刺、测轴套孔/导柱", "仍不行则暂停，反馈建模组"] },
    { t: "销能插入但转不动", sol: ["检查毛刺与孔径", "确认没把锁销当主转轴", "不要蛮力硬掰"] },
    { t: "卡圈总是掉", sol: ["检查是否真正进入尾槽", "单独记录零件编号", "标记“卡圈保持不足”"] },
    { t: "SCZ横销/横轴会滑出", sol: ["PIN25-L10 无独立卡圈，靠压入配合", "轴端 CLIP4 是否入槽", "记录为潜在缺陷，待实物验证"] },
  ];
  qs.forEach((q, i) => {
    const x = 0.5 + (i % 2) * 6.33, y = 1.45 + Math.floor(i / 2) * 2.72;
    rrect(s, x, y, 6.0, 2.45, C.white, C.line, 1, 0.08);
    brick(s, x + 0.25, y + 0.28, 0.85, 0.44, C.red, "Q" + (i + 1), { fs: 14, studs: 2 });
    txt(s, q.t, x + 1.3, y + 0.24, 4.5, 0.52, { fontSize: 15, bold: true, valign: "middle", name: "q" + i });
    let yy = y + 0.95;
    q.sol.forEach(t => { yy += checkItem(s, x + 0.3, yy, 5.4, t, C.lgray, null, 12.5) + 0.08; });
  });
  footer(s, 39);
}

// ======================= 40 展示 =======================
{
  const s = newSlide(40);
  s.background = { color: C.white };
  header(s, "展示", C.black, "汇报时怎么展示", { fs: 28 });
  const cards = [
    { n: "1", name: "F07", c: C.red, tag: "最直观" },
    { n: "2", name: "F09", c: C.blue, tag: "结构最完整" },
    { n: "3", name: "SCZ", c: C.green, tag: "路线最不同" },
  ];
  cards.forEach((cd, i) => {
    const x = 0.5 + i * 4.19;
    rrect(s, x, 1.45, 3.95, 2.45, C.white, C.line, 1, 0.08);
    circ(s, x + 0.3, 1.75, 0.62, cd.c);
    txt(s, cd.n, x + 0.3, 1.75, 0.62, 0.62, { fontSize: 22, bold: true, color: C.white, align: "center", valign: "middle", name: "showN" + i });
    txt(s, cd.name, x + 1.15, 1.78, 2.6, 0.56, { fontSize: 22, bold: true, fontFace: M, color: cd.c, valign: "middle", name: "showName" + i });
    txt(s, cd.tag, x + 0.3, 2.75, 3.35, 0.6, { fontSize: 16, bold: true, align: "center", valign: "middle", name: "showTag" + i });
  });
  rrect(s, 0.5, 4.2, 12.33, 1.75, C.light, null, 0, 0.08);
  txt(s, "每套都说三句话", 0.85, 4.4, 4, 0.4, { fontSize: 15, bold: true, name: "threeH" });
  let y = 4.85;
  ["这套机构是什么路线；", "它的动作顺序是什么；", "实物装配暴露了什么问题。"].forEach((t, i) => { y += numItem(s, 0.85, y, 11.4, i + 1, t, C.black, 13) + 0.05; });
  txt(s, "本轮重点是把三条候选路线推进到“实物可装、可动、可汇报”，未验收项如实说明。", 0.5, 6.1, 12.33, 0.75, { fontSize: 15, bold: true, color: C.redD, align: "center", valign: "middle", name: "showClose" });
  footer(s, 40);
}

// ======================= 41 成果与待验收 =======================
{
  const s = newSlide(41);
  s.background = { color: C.black };
  for (let i = 0; i < 12; i++) circ(s, 0.62 + i * 1.06, 0.14, 0.42, C.yellow, C.yellowD, 1);
  brick(s, 0.5, 0.85, 1.3, 0.55, C.yellow, "END", { fs: 15, tc: C.black });
  txt(s, "阶段成果与待验收", 2.05, 0.72, 8.5, 0.8, { fontSize: 30, bold: true, color: C.white, valign: "middle", name: "endTitle" });
  rrect(s, 0.5, 1.75, 6.0, 3.9, "2A2A2A", null, 0, 0.08);
  txt(s, "已完成", 0.8, 1.98, 3, 0.4, { fontSize: 17, bold: true, color: C.yellow, name: "doneH" });
  let y = 2.5;
  ["R1-V6相关打印任务（已确认）", "本地 V6.1 CAD 与可拆顶盖资料", "V6.1 L1–L3 CAD 级验证", "装配说明书与 BOM 闭环核对"].forEach(t => { y += checkItem(s, 0.85, y, 5.35, t, C.yellow, "ok", 13.5, C.white) + 0.22; });
  rrect(s, 6.85, 1.75, 5.98, 3.9, "2A2A2A", null, 0, 0.08);
  txt(s, "待现场验收", 7.15, 1.98, 4, 0.4, { fontSize: 17, bold: true, color: C.yellow, name: "todoH" });
  y = 2.5;
  ["L4关键接口配合与间隙冻结", "CAP顶盖及全套实物装配", "手动全行程与逆向恢复", "销轴/卡圈/横销保持与修模", "V6.1 同步 GitHub（未推送）"].forEach(t => { y += checkItem(s, 7.2, y, 5.3, t, C.lgray, null, 13.5, C.white) + 0.16; });
  txt(s, "让仿真决定值得试什么，让实物决定最终留下什么。", 0.5, 6.0, 12.33, 0.8, { fontSize: 20, bold: true, color: C.yellow, align: "center", valign: "middle", name: "endQuote" });
  footer(s, 41, true);
}

pres.writeFile({ fileName: path.join(__dirname, "R1-V6_乐高风总装说明书_V2.pptx") }).then(() => {
  console.log("WROTE V2 deck, slides:", 41);
  report();
});
