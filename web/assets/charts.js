// charts.js — small, dependency-free SVG chart toolkit for the companion site (W2).
// Accessible by construction: every chart gets role="img" + aria-label, focusable marks
// with tooltips, a legend for >= 2 series and a data-table alternative.

const SVGNS = "http://www.w3.org/2000/svg";
export const NF = {
  int: new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }),
  d1: new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, minimumFractionDigits: 1 }),
  d2: new Intl.NumberFormat("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 }),
  d3: new Intl.NumberFormat("en-US", { maximumFractionDigits: 3, minimumFractionDigits: 3 }),
};
/** Generic display formatter for values that come from the data files (axes, tooltips, tables). */
export function fmt(v, digits) {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  if (typeof v !== "number") return String(v);
  if (digits !== undefined) return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v);
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (Number.isInteger(v)) return NF.int.format(v);
  if (a >= 100) return NF.int.format(v);
  if (a >= 10) return NF.d1.format(v);
  if (a >= 0.1) return NF.d2.format(v);
  if (a >= 0.001) return new Intl.NumberFormat("en-US", { maximumSignificantDigits: 3 }).format(v);
  return v.toExponential(2);
}

export function el(tag, attrs = {}, parent) {
  const isSvg = ["svg", "g", "path", "line", "rect", "circle", "text", "polygon", "title", "desc", "clipPath", "tspan"].includes(tag);
  const node = isSvg ? document.createElementNS(SVGNS, tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v === true ? "" : v);
  }
  if (parent) parent.appendChild(node);
  return node;
}

// ---------- scales ----------
export function linear(d0, d1, r0, r1) {
  const s = (v) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);
  s.domain = [d0, d1]; s.range = [r0, r1];
  s.ticks = (n = 5) => niceTicks(d0, d1, n);
  return s;
}
export function log10(d0, d1, r0, r1) {
  const l0 = Math.log10(d0), l1 = Math.log10(d1);
  const s = (v) => r0 + ((Math.log10(v) - l0) / (l1 - l0 || 1)) * (r1 - r0);
  s.domain = [d0, d1]; s.range = [r0, r1]; s.log = true;
  s.ticks = () => {
    const out = [];
    for (let e = Math.floor(l0); e <= Math.ceil(l1); e++) { const t = 10 ** e; if (t >= d0 * 0.999 && t <= d1 * 1.001) out.push(t); }
    return out;
  };
  return s;
}
export function band(keys, r0, r1, pad = 0.25) {
  const step = (r1 - r0) / Math.max(keys.length, 1);
  const s = (k) => r0 + keys.indexOf(k) * step + (step * pad) / 2;
  s.bandwidth = step * (1 - pad); s.step = step; s.keys = keys;
  return s;
}
export function niceTicks(a, b, n = 5) {
  if (a === b) return [a];
  const span = b - a, raw = span / n, mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= n) || 10 * mag;
  const out = [];
  for (let t = Math.ceil(a / step) * step; t <= b + step * 1e-9; t += step) out.push(+t.toPrecision(12));
  return out;
}
export function niceMax(v) {
  if (v <= 0) return 1;
  const t = niceTicks(0, v, 5); const last = t[t.length - 1];
  return last >= v ? last : last + (t[1] - t[0]);
}
export function logExtent(vals, padFactor = 1.5) {
  const pos = vals.filter((v) => v > 0 && Number.isFinite(v));
  if (!pos.length) return [0.1, 1];
  const lo = Math.min(...pos), hi = Math.max(...pos);
  return [10 ** Math.floor(Math.log10(lo / padFactor)), 10 ** Math.ceil(Math.log10(hi * padFactor))];
}

// ---------- marker shapes (secondary encoding for CVD) ----------
const SHAPES = ["circle", "square", "triangle", "diamond", "triangle-down", "circle-open", "square-open"];
export function marker(g, shapeIdx, x, y, r = 5, cls = "", attrs = {}) {
  const shape = SHAPES[shapeIdx % SHAPES.length];
  let node;
  if (shape.startsWith("circle")) node = el("circle", { cx: x, cy: y, r, ...attrs }, g);
  else if (shape.startsWith("square")) node = el("rect", { x: x - r, y: y - r, width: 2 * r, height: 2 * r, rx: 1.5, ...attrs }, g);
  else if (shape === "triangle") node = el("polygon", { points: `${x},${y - r * 1.2} ${x + r * 1.1},${y + r * 0.8} ${x - r * 1.1},${y + r * 0.8}`, ...attrs }, g);
  else if (shape === "triangle-down") node = el("polygon", { points: `${x},${y + r * 1.2} ${x + r * 1.1},${y - r * 0.8} ${x - r * 1.1},${y - r * 0.8}`, ...attrs }, g);
  else node = el("polygon", { points: `${x},${y - r * 1.3} ${x + r * 1.1},${y} ${x},${y + r * 1.3} ${x - r * 1.1},${y}`, ...attrs }, g);
  node.setAttribute("class", `${cls} mark fill`);
  return node;
}
export const DASHES = ["", "6 3", "2 3", "8 3 2 3", "1 2", "10 4"];

// ---------- frame ----------
/**
 * Creates the chart scaffold inside `host`: title, controls slot, legend, svg, tooltip,
 * data table. Returns handles.
 */
export function frame(host, { height = 320, margin = {}, ariaLabel = "", minWidth = 300 } = {}) {
  const w = Math.max(minWidth, Math.floor(host.clientWidth || host.getBoundingClientRect().width || 640));
  const m = { top: 16, right: 16, bottom: 44, left: 56, ...margin };
  const wrap = el("div", { class: "chart-wrap" }, host);
  const svg = el("svg", { viewBox: `0 0 ${w} ${height}`, role: "group", "aria-label": `${ariaLabel} Use arrow keys to move between data points.`, focusable: "false" }, wrap);
  const tip = el("div", { class: "tooltip", role: "status", "aria-live": "polite", hidden: true }, wrap);
  return { wrap, svg, tip, w, h: height, m, iw: w - m.left - m.right, ih: height - m.top - m.bottom };
}

export function axes(f, x, y, { xTitle = "", yTitle = "", xFmt = fmt, yFmt = fmt, xTicks, yTicks, xBand = false, grid = true } = {}) {
  const g = el("g", { "aria-hidden": "true" }, f.svg);
  const { m, iw, ih } = f;
  const yt = yTicks || y.ticks(5);
  for (const t of yt) {
    const py = y(t);
    if (grid) el("line", { class: "gridline", x1: m.left, x2: m.left + iw, y1: py, y2: py }, g);
    el("text", { x: m.left - 6, y: py, "text-anchor": "end", "dominant-baseline": "middle", text: yFmt(t) }, g);
  }
  el("line", { class: "axis-line", x1: m.left, x2: m.left + iw, y1: m.top + ih, y2: m.top + ih }, g);
  if (xBand) {
    for (const k of x.keys) el("text", { x: x(k) + x.bandwidth / 2, y: m.top + ih + 16, "text-anchor": "middle", text: xFmt(k) }, g);
  } else {
    const xt = xTicks || x.ticks(Math.max(2, Math.min(8, Math.floor(iw / 70))));
    for (const t of xt) {
      const px = x(t);
      el("line", { class: "axis-line", x1: px, x2: px, y1: m.top + ih, y2: m.top + ih + 4 }, g);
      el("text", { x: px, y: m.top + ih + 16, "text-anchor": "middle", text: xFmt(t) }, g);
    }
  }
  if (xTitle) el("text", { class: "axis-title", x: m.left + iw / 2, y: f.h - 6, "text-anchor": "middle", text: xTitle }, g);
  if (yTitle) el("text", { class: "axis-title", x: 12, y: m.top + ih / 2, "text-anchor": "middle", transform: `rotate(-90 12 ${m.top + ih / 2})`, text: yTitle }, g);
  return g;
}

// ---------- legend ----------
export function legend(host, items, { before } = {}) {
  const ul = el("ul", { class: "legend" });
  for (const it of items) {
    const li = el("li", {}, ul);
    el("span", { class: `swatch ${it.kind || ""} ${it.cls || ""}`, "aria-hidden": "true" }, li);
    li.appendChild(document.createTextNode(it.label));
  }
  if (before) host.insertBefore(ul, before); else host.appendChild(ul);
  return ul;
}

// ---------- tooltip / focus ----------
export function bindTip(f, node, html, label) {
  // Roving tabindex: one Tab stop per chart; arrow keys move between data marks.
  node.setAttribute("data-tip", "");
  node.setAttribute("tabindex", f.svg.querySelector('[data-tip][tabindex="0"]') ? "-1" : "0");
  node.setAttribute("role", "img");
  const tmp = document.createElement("div");
  tmp.innerHTML = html.replace(/<br>/g, ". ");
  node.setAttribute("aria-label", label || tmp.textContent.replace(/\s+/g, " ").trim());
  const show = () => {
    f.tip.innerHTML = html;
    f.tip.hidden = false;
    const wr = f.wrap.getBoundingClientRect();
    const nb = node.getBoundingClientRect();
    const tw = f.tip.offsetWidth, th = f.tip.offsetHeight;
    let left = nb.left - wr.left + nb.width / 2 + 10;
    if (left + tw > wr.width) left = Math.max(0, nb.left - wr.left - tw - 10);
    let top = nb.top - wr.top - th - 8;
    if (top < 0) top = nb.bottom - wr.top + 8;
    f.tip.style.left = `${left}px`;
    f.tip.style.top = `${top}px`;
  };
  const hide = () => { f.tip.hidden = true; };
  node.addEventListener("mouseenter", show);
  node.addEventListener("mouseleave", hide);
  node.addEventListener("focus", show);
  node.addEventListener("blur", hide);
  node.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { hide(); return; }
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    const list = [...f.svg.querySelectorAll("[data-tip]")];
    let i = list.indexOf(node);
    if (step) i = Math.min(list.length - 1, Math.max(0, i + step));
    else if (e.key === "Home") i = 0;
    else if (e.key === "End") i = list.length - 1;
    else return;
    e.preventDefault();
    list.forEach((n) => n.setAttribute("tabindex", "-1"));
    list[i].setAttribute("tabindex", "0");
    list[i].focus();
  });
}

// ---------- data table ----------
export function dataTable(host, { caption, columns, rows, summary = "Show data table" }) {
  const det = el("details", { class: "data-table" }, host);
  el("summary", { text: summary }, det);
  const sc = el("div", { class: "table-scroll", tabindex: "0", role: "region", "aria-label": caption }, det);
  const t = el("table", {}, sc);
  el("caption", { text: caption }, t);
  const thr = el("tr", {}, el("thead", {}, t));
  for (const c of columns) el("th", { scope: "col", text: c.label }, thr);
  const tb = el("tbody", {}, t);
  for (const r of rows) {
    const tr = el("tr", {}, tb);
    columns.forEach((c, i) => {
      const v = typeof c.value === "function" ? c.value(r) : r[c.key];
      el(i === 0 ? "th" : "td", { scope: i === 0 ? "row" : undefined, text: c.fmt ? c.fmt(v) : fmt(v) }, tr);
    });
  }
  return det;
}

// ---------- segmented control ----------
let segId = 0;
export function segmented(host, { label, options, value, onChange }) {
  const fs = el("fieldset", {}, host);
  el("legend", { text: label }, fs);
  const seg = el("div", { class: "seg" }, fs);
  const name = `seg-${++segId}`;
  for (const o of options) {
    const lab = el("label", {}, seg);
    const inp = el("input", { type: "radio", name, value: o.value }, lab);
    if (o.value === value) inp.checked = true;
    el("span", { text: o.label }, lab);
    inp.addEventListener("change", () => inp.checked && onChange(o.value));
  }
  return fs;
}

export function emptyNote(host, title, text) {
  const d = el("div", { class: "chart-empty", role: "note" }, host);
  el("strong", { text: title }, d);
  if (text) el("p", { text }, d);
  return d;
}

export function linePath(pts, maxGap = Infinity) {
  // maxGap (in px along x): a jump wider than this starts a new sub-path instead of interpolating.
  return pts.map((p, i) => `${i && Math.abs(p[0] - pts[i - 1][0]) <= maxGap ? "L" : "M"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join("");
}
