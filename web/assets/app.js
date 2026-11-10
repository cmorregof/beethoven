// app.js — companion site behaviour (W2). ES module, no build step.
// Loads web/data/*.json (written by web/build_data.py from versioned results), fills every
// [data-num] placeholder, injects the method text, renders the protocol status panel and draws
// the charts. No result number is typed here: every value shown comes from web/data.
// The confirmatory case (Cherubini → op. 67) has not been run; nothing here shows or implies a
// result for it.

import {
  el, fmt, linear, log10, band, niceMax, logExtent, frame, axes, legend, bindTip, dataTable,
  segmented, emptyNote, linePath, marker, DASHES,
} from "./charts.js";

// ---------------------------------------------------------------- contract (see web/README.md)
const DATA = "data/";
const FILES = {
  numbers: "numbers.json", corpus: "corpus.json", base_rates: "base_rates.json",
  observed_null: "observed_null.json", uniqueness: "uniqueness.json",
  calibration: "calibration.json", lambda: "lambda.json", thresholds: "thresholds.json",
  literal: "literal.json", status: "status.json",
};
const PERIOD_CLASS = { "<1750": "c1", "1750–1800": "c2", "1800–1830": "c3", "1830–1900": "c4", ">1900": "c5", unknown: "c7" };
const MODEL_CLASS = { lap: "c6", kn: "c1", hier: "c3" };
const MODEL_LABEL = { lap: "Laplace", kn: "Kneser–Ney", hier: "Hierarchical" };
const CURVE_CLASS = { DF: "c1", E: "c2", "DF→E": "c3" };
const ALPHA_CLASS = { IV: "c1", IVR: "c2" };
const ALPHA_LABEL = { IV: "Intervals (IV)", IVR: "Intervals + rhythm (IVR)" };

const cache = new Map();
async function load(name) {
  if (!cache.has(name)) {
    cache.set(name, fetch(DATA + FILES[name], { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(`${FILES[name]}: HTTP ${r.status}`);
      return r.json();
    }));
  }
  return cache.get(name);
}

// ---------------------------------------------------------------- numbers
let NUMBERS = null;
async function fillNumbers(root = document) {
  if (!NUMBERS) {
    try { NUMBERS = (await load("numbers")).numbers || {}; }
    catch (e) { console.error("[numbers]", e); NUMBERS = {}; }
  }
  for (const node of root.querySelectorAll("[data-num]")) {
    const key = node.dataset.num;
    const rec = NUMBERS[key];
    if (rec && rec.text !== undefined && rec.text !== null) {
      node.textContent = rec.text;
      node.classList.remove("num-missing");
      if (rec.source) node.title = `Source: ${rec.source}`;
    } else {
      node.textContent = `[missing: ${key}]`;
      node.classList.add("num-missing");
      console.warn(`[numbers] missing key: ${key}`);
    }
  }
}

// ---------------------------------------------------------------- method text
async function injectMethod() {
  let host = document.getElementById("method-content");
  if (!host) {
    // Fallback: append after the method summary written by W1.
    const sec = document.getElementById("method");
    if (!sec) return;
    host = el("div", { id: "method-content" });
    sec.appendChild(host);
  }
  try {
    const r = await fetch("assets/content/method.html", { cache: "no-cache" });
    if (!r.ok) throw new Error(`method.html: HTTP ${r.status}`);
    host.innerHTML = await r.text();
  } catch (e) { console.error("[method]", e); }
}

// ---------------------------------------------------------------- status panel
const ICONS = {
  done: '<svg class="status-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
  "not-run": '<svg class="status-icon" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="3" width="10" height="10" rx="1" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
  pending: '<svg class="status-icon" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 5v3.5l2 1.5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
};
function statusCard(ul, state, badge, title, body, level = "h3") {
  const li = el("li", { class: `status-card ${state}` }, ul);
  const h = el(level, {}, li);
  h.innerHTML = ICONS[state];
  h.appendChild(document.createTextNode(title + " "));
  el("span", { class: "badge", text: badge }, h);
  if (body) { const p = el("p", {}, li); if (body instanceof Node) p.appendChild(body); else p.textContent = body; }
  return li;
}
async function renderStatus() {
  let host = document.getElementById("status-panel");
  if (!host) {
    const sec = document.getElementById("protocol");
    if (!sec) return;
    host = el("div", { id: "status-panel" });
    const h = sec.querySelector("h2");
    host.className = "status-summary";
    if (h && h.nextSibling) sec.insertBefore(host, h.nextSibling); else sec.appendChild(host);
  }
  host.textContent = "";
  let s;
  try { s = await load("status"); } catch (e) { emptyNote(host, "Protocol status unavailable", String(e.message)); return; }
  el("h3", { class: "visually-hidden", text: "Preregistration status" }, host);
  const ul = el("ul", { class: "status-panel", "aria-label": "Preregistration status" }, host);
  const pr = s.preregistration || {};
  const frag = document.createDocumentFragment();
  frag.append("Decision ", el("code", { text: pr.id || "D-41" }), " frozen at commit ",
    el("code", { text: pr.frozen_commit_short || pr.frozen_commit || "?", title: pr.frozen_commit || "" }),
    pr.file ? "; text in " : ".", ...(pr.file ? [el("code", { text: pr.file }), "."] : []));
  statusCard(ul, "done", "Frozen", "Preregistration", frag);
  const cc = s.confirmatory_case || {};
  statusCard(ul, "not-run", cc.executed ? "Executed" : "Not run", "Confirmatory case",
    cc.note || "The preregistered test has not been executed. No result is shown on this site.");
  const pend = [...(s.pending || [])];
  const pendHost = document.getElementById("status-pending");
  let pendUl = ul;
  if (pendHost) { pendHost.textContent = ""; pendHost.classList.add("status-panel"); pendUl = pendHost; }
  // Protocol items not (yet) in status.json; plain text, no numbers. Added only if absent.
  for (const extra of EXTRA_PENDING) if (!pend.some((p) => extra.match.test(`${p.item} ${p.state || ""}`))) pend.push(extra);
  for (const p of pend) {
    const st = String(p.state || "open");
    const done = /^done/i.test(st);
    const rest = st.replace(/^(done|open)\s*:?\s*/i, "");
    statusCard(pendUl, done ? "done" : "pending", done ? "Done" : "Open", p.item, rest ? rest.charAt(0).toUpperCase() + rest.slice(1) : "", pendHost ? "h4" : "h3");
  }
}
const EXTRA_PENDING = [
  { match: /transcri/i, item: "Transcribe the Cherubini works named in the hypothesis", state: "open: they are not encoded in the corpus" },
  { match: /D-43/i, item: "Amendment D-43 to the protocol (null built from equal-length fragments, eligible works, literal controls)", state: "open: draft in preparation, to be frozen before the case is run" },
  { match: /OSF/i, item: "Register the preregistration on OSF", state: "open: to be filed together with D-43 once approved" },
];

// ---------------------------------------------------------------- chart plumbing
const renderers = {};
function chart(id, name, draw, extras = []) { renderers[id] = { name, draw, extras }; }

async function renderChart(id) {
  const host = document.getElementById(id);
  if (!host) return;
  const { name, draw, extras } = renderers[id];
  let data;
  const extra = {};
  try {
    data = await load(name);
    for (const x of extras) { try { extra[x] = await load(x); } catch (e) { console.warn(`[${id}] optional ${x}:`, e); } }
  }
  catch (e) {
    console.error(`[${id}]`, e);
    host.querySelector(".chart-empty")?.remove();
    if (!host.dataset.fallbackKept) { host.dataset.fallbackKept = "1"; }
    emptyNote(host, "Data not available", `${FILES[name]} could not be loaded. Run web/build_data.py.`);
    return;
  }
  host.dataset.rendered = "1";
  // The container may carry role="img" for the no-JS fallback; once interactive content is drawn
  // the role must go (role=img hides focusable children from assistive technology).
  host.removeAttribute("role");
  host.removeAttribute("aria-label");
  const state = host._state || (host._state = {});
  const redraw = () => {
    // Keep keyboard focus on the control the user just operated (controls are rebuilt).
    const a = document.activeElement;
    let keep = null;
    if (a && host.contains(a) && (a.tagName === "INPUT" || a.tagName === "SELECT")) {
      keep = { legend: a.closest("fieldset")?.querySelector("legend")?.textContent, tag: a.tagName, value: a.value };
    }
    host.textContent = "";
    host.classList.add("chart-host");
    try { draw(host, data, state, redraw, extra); }
    catch (e) { console.error(`[${id}]`, e); emptyNote(host, "Chart could not be drawn", String(e.message)); }
    if (keep) {
      const fs = [...host.querySelectorAll("fieldset")].find((f) => f.querySelector("legend")?.textContent === keep.legend);
      const target = keep.tag === "SELECT" ? fs?.querySelector("select") : fs?.querySelector(`input[value="${CSS.escape(keep.value)}"]`);
      target?.focus();
    }
  };
  host._redraw = redraw;
  redraw();
}

function controls(host) { return el("div", { class: "chart-controls" }, host); }

// ---------------------------------------------------------------- 1. corpus
chart("chart-corpus", "corpus", (host, d, st, redraw) => {
  st.metric ||= "works";
  const metrics = [
    { value: "works", label: "Works" }, { value: "windows", label: "4-note windows" }, { value: "units", label: "Files / movements" },
  ];
  segmented(controls(host), { label: "Measure", options: metrics, value: st.metric, onChange: (v) => { st.metric = v; redraw(); } });
  const order = d.period_order || d.by_period.map((r) => r.period);
  const rows = order.map((p) => d.by_period.find((r) => r.period === p)).filter(Boolean);
  const label = metrics.find((m) => m.value === st.metric).label;
  const f = frame(host, { height: 40 + rows.length * 38, margin: { left: 92, right: 70, bottom: 36 }, ariaLabel: `Corpus size by period: ${label.toLowerCase()}. Data table below.` });
  const vmax = niceMax(Math.max(...rows.map((r) => r[st.metric] || 0)));
  const x = linear(0, vmax, f.m.left, f.m.left + f.iw);
  const y = band(rows.map((r) => r.period), f.m.top, f.m.top + f.ih, 0.3);
  const g = el("g", {}, f.svg);
  for (const t of x.ticks(Math.max(2, Math.floor(f.iw / 90)))) {
    el("line", { class: "gridline", x1: x(t), x2: x(t), y1: f.m.top, y2: f.m.top + f.ih }, g);
    el("text", { x: x(t), y: f.m.top + f.ih + 16, "text-anchor": "middle", text: fmt(t) }, g);
  }
  el("text", { class: "axis-title", x: f.m.left + f.iw / 2, y: f.h - 4, "text-anchor": "middle", text: label }, g);
  for (const r of rows) {
    const v = r[st.metric] || 0, yy = y(r.period);
    el("text", { x: f.m.left - 8, y: yy + y.bandwidth / 2, "text-anchor": "end", "dominant-baseline": "middle", text: r.period }, g);
    const bar = el("rect", { class: `${PERIOD_CLASS[r.period] || "c7"} fill mark`, x: x(0), y: yy, width: Math.max(1, x(v) - x(0)), height: y.bandwidth, rx: 3 }, g);
    el("text", { class: "direct-label", x: x(v) + 6, y: yy + y.bandwidth / 2, "dominant-baseline": "middle", text: fmt(v) }, g);
    bindTip(f, bar, `<b>${r.period}</b><br>${fmt(r.works)} works · ${fmt(r.units)} files/movements<br>${fmt(r.windows)} windows · ${fmt(r.notes)} notes`);
  }
  dataTable(host, {
    caption: "Corpus by period (target work and Cherubini excluded)",
    columns: [{ key: "period", label: "Period" }, { key: "works", label: "Works" }, { key: "units", label: "Files/movements" }, { key: "windows", label: "4-note windows" }, { key: "notes", label: "Notes" }],
    rows: d.totals ? [...rows, { period: "Total", ...d.totals }] : rows,
  });
  if (Array.isArray(d.by_collection) && d.by_collection.length) {
    dataTable(host, {
      summary: "Show collections table",
      caption: "Corpus by collection (aggregates)",
      columns: [{ key: "collection", label: "Collection" }, { key: "works", label: "Works" }, { key: "units", label: "Files/movements" }, { key: "windows", label: "Windows" }, { key: "periods", label: "Periods", fmt: (v) => (Array.isArray(v) ? v.join(", ") : fmt(v)) }],
      rows: [...d.by_collection].sort((a, b) => (b.windows || 0) - (a.windows || 0)),
    });
  }
});

// ---------------------------------------------------------------- 2. base rates D1–D5
chart("chart-baserates", "base_rates", (host, d) => {
  const order = d.period_order || d.by_period.map((r) => r.period);
  const rows = order.map((p) => d.by_period.find((r) => r.period === p)).filter(Boolean);
  const motifs = d.motifs || ["D1", "D2", "D3", "D4", "D5"].map((id) => ({ id, label: id }));
  legend(host, rows.map((r) => ({ label: r.period, cls: PERIOD_CLASS[r.period] || "c7" })).concat(d.all ? [{ label: "Whole corpus", kind: "line", cls: "c7" }] : []));
  const defs = el("dl", { class: "motif-defs" }, host);
  for (const mo of motifs) { el("dt", { text: mo.id }, defs); el("dd", { text: mo.label || mo.id }, defs); }
  const grid = el("div", { class: "small-multiples" }, host);
  const panelsList = motifs.map((mo) => { const panel = el("div", {}, grid); el("p", { class: "chart-title", text: mo.id }, panel); return panel; });
  for (const [mi, mo] of motifs.entries()) {
    const panel = panelsList[mi];
    const vals = rows.map((r) => r.rate_per_100k?.[mo.id] ?? 0);
    const f = frame(panel, { height: 210, margin: { left: 62, bottom: 40, right: 8 }, ariaLabel: `${mo.id} occurrences per 100,000 windows by period`, minWidth: 240 });
    const ymax = niceMax(Math.max(...vals, d.all?.rate_per_100k?.[mo.id] || 0));
    const y = linear(0, ymax, f.m.top + f.ih, f.m.top);
    const x = band(rows.map((r) => r.period), f.m.left, f.m.left + f.iw, 0.25);
    axes(f, x, y, { xBand: true, yTitle: "per 100k windows", xFmt: (k) => (f.iw < 260 ? k.replace("unknown", "unk.") : k) });
    // rotate x labels if crowded
    if (f.iw / rows.length < 52) f.svg.querySelectorAll("g text[text-anchor=middle]").forEach((t) => { if (!t.classList.contains("axis-title") && +t.getAttribute("y") > f.m.top + f.ih) { const xx = t.getAttribute("x"), yy = t.getAttribute("y"); t.setAttribute("transform", `rotate(-30 ${xx} ${yy})`); t.setAttribute("text-anchor", "end"); } });
    const g = el("g", {}, f.svg);
    rows.forEach((r, i) => {
      const v = vals[i];
      const bar = el("rect", { class: `${PERIOD_CLASS[r.period] || "c7"} fill mark`, x: x(r.period), y: y(v), width: x.bandwidth, height: Math.max(0, y(0) - y(v)), rx: 3 }, g);
      bindTip(f, bar, `<b>${mo.id}, ${r.period}</b><br>${fmt(v)} per 100k windows<br>${fmt(r.counts?.[mo.id])} occurrences in ${fmt(r.windows)} windows${r.prevalence_pct ? `<br>${fmt(r.prevalence_pct[mo.id])} % of works contain it` : ""}`);
    });
    if (d.all?.rate_per_100k?.[mo.id] !== undefined) {
      const ya = y(d.all.rate_per_100k[mo.id]);
      el("line", { class: "ref-line", x1: f.m.left, x2: f.m.left + f.iw, y1: ya, y2: ya, "aria-hidden": "true" }, g);
    }
  }
  const all = d.all ? [{ period: "Whole corpus", ...d.all }] : [];
  dataTable(host, {
    caption: "Base rate of nested motifs D1–D5 per 100,000 windows",
    columns: [{ key: "period", label: "Period" }, { key: "works", label: "Works" }, { key: "windows", label: "Windows" },
      ...motifs.map((mo) => ({ label: mo.id, value: (r) => r.rate_per_100k?.[mo.id] }))],
    rows: [...all, ...rows],
  });
});

// ---------------------------------------------------------------- 3. observed vs null
chart("chart-null", "observed_null", (host, d, st, redraw) => {
  const sets = { [d.motif || "D4"]: d.strata };
  for (const [k, v] of Object.entries(d.other_motifs || {})) if (Array.isArray(v) && v.length) sets[k] = v;
  st.motif ||= d.motif || "D4";
  if (Object.keys(sets).length > 1) segmented(controls(host), { label: "Motif", options: Object.keys(sets).map((k) => ({ value: k, label: k })), value: st.motif, onChange: (v) => { st.motif = v; redraw(); } });
  const rows = sets[st.motif];
  legend(host, [{ label: "Observed", cls: "c1" }, { label: "Null mean with 95 % interval", kind: "band", cls: "c7" }]);
  const f = frame(host, { height: 30 + rows.length * 34, margin: { left: 100, right: 24, bottom: 40 }, ariaLabel: `${st.motif}: observed count versus null-model mean and 95 % interval by stratum. Data table below.` });
  const xmax = niceMax(Math.max(...rows.flatMap((r) => [r.obs, r.ci95?.[1] ?? r.null_mean])));
  const x = linear(0, xmax, f.m.left, f.m.left + f.iw);
  const y = band(rows.map((r) => r.stratum), f.m.top, f.m.top + f.ih, 0.2);
  const g = el("g", {}, f.svg);
  for (const t of x.ticks(Math.max(2, Math.floor(f.iw / 90)))) {
    el("line", { class: "gridline", x1: x(t), x2: x(t), y1: f.m.top, y2: f.m.top + f.ih }, g);
    el("text", { x: x(t), y: f.m.top + f.ih + 16, "text-anchor": "middle", text: fmt(t) }, g);
  }
  el("text", { class: "axis-title", x: f.m.left + f.iw / 2, y: f.h - 4, "text-anchor": "middle", text: `${st.motif} occurrences (count)` }, g);
  for (const r of rows) {
    const cy = y(r.stratum) + y.bandwidth / 2;
    const lab = r.kind === "all" ? "All periods" : r.stratum;
    el("text", { x: f.m.left - 8, y: cy, "text-anchor": "end", "dominant-baseline": "middle", text: lab, "font-weight": r.kind === "all" ? 600 : null }, g);
    if (r.ci95) el("rect", { class: "null-band", x: x(r.ci95[0]), y: cy - 7, width: Math.max(2, x(r.ci95[1]) - x(r.ci95[0])), height: 14, rx: 2 }, g);
    el("line", { class: "ci", x1: x(r.null_mean), x2: x(r.null_mean), y1: cy - 9, y2: cy + 9 }, g);
    const dot = marker(g, 0, x(r.obs), cy, 6, "c1");
    bindTip(f, dot, `<b>${lab}</b> (${fmt(r.works ?? r.works_perm)} works)<br>Observed: ${fmt(r.obs)}<br>Null mean: ${fmt(r.null_mean)}${r.ci95 ? ` (95 %: ${fmt(r.ci95[0])}–${fmt(r.ci95[1])})` : ""}<br>Ratio ${fmt(r.ratio, 2)} · p = ${fmt(r.p, 3)} · ${fmt(r.n_perm)} permutations`);
  }
  dataTable(host, {
    caption: `${st.motif}: observed versus within-voice shuffle null`,
    columns: [{ key: "stratum", label: "Stratum" }, { label: "Works", value: (r) => r.works ?? r.works_perm }, { key: "obs", label: "Observed" }, { key: "null_mean", label: "Null mean" },
      { label: "95 % interval", value: (r) => (r.ci95 ? `${fmt(r.ci95[0])}–${fmt(r.ci95[1])}` : "–") }, { key: "ratio", label: "Ratio", fmt: (v) => fmt(v, 2) }, { key: "p", label: "p", fmt: (v) => fmt(v, 3) }, { key: "n_perm", label: "Permutations" }],
    rows,
  });
});

// ---------------------------------------------------------------- 4. uniqueness
chart("chart-uniqueness", "uniqueness", (host, d, st, redraw) => {
  st.measure ||= "p_cross"; st.scope ||= "global"; st.alpha ||= "IVR";
  const c = controls(host);
  segmented(c, { label: "Measure", options: [{ value: "p_cross", label: "P_cross(n)" }, { value: "p_pair", label: "P_pair(n)" }], value: st.measure, onChange: (v) => { st.measure = v; redraw(); } });
  segmented(c, { label: "Scope", options: [{ value: "global", label: "Global" }, { value: "period", label: "By period" }], value: st.scope, onChange: (v) => { st.scope = v; redraw(); } });
  if (st.scope === "period") segmented(c, { label: "Alphabet", options: (d.alphabets || ["IV", "IVR"]).map((a) => ({ value: a, label: a })), value: st.alpha, onChange: (v) => { st.alpha = v; redraw(); } });

  let series;
  if (st.scope === "global") series = (d.alphabets || ["IV", "IVR"]).map((a, i) => ({ key: a, label: ALPHA_LABEL[a] || a, cls: ALPHA_CLASS[a], idx: i, pts: d.global[a] }));
  else {
    const per = d.by_period[st.alpha] || {};
    series = Object.keys(per).map((p, i) => ({ key: p, label: `${p}${d.works_by_period?.[p] !== undefined ? ` (${fmt(d.works_by_period[p])} works)` : ""}`, cls: PERIOD_CLASS[p] || "c7", idx: i, pts: per[p] }));
  }
  legend(host, series.map((s) => ({ label: s.label, kind: "line", cls: s.cls })));
  const ml = st.measure === "p_pair" ? "P_pair(n): share of windows of work A found in a given work B" : "P_cross(n): share of windows found in at least one other work";
  const f = frame(host, { height: 340, margin: { left: 62, right: 20 }, ariaLabel: `${ml}, by window length n. ${st.scope === "global" ? "Global" : `By period, ${st.alpha}`}. Data table below.` });
  const ns = d.ns || series[0].pts.map((p) => p.n);
  const x = linear(Math.min(...ns), Math.max(...ns), f.m.left, f.m.left + f.iw);
  const vals = series.flatMap((s) => s.pts.map((p) => p[st.measure]));
  const y = st.measure === "p_pair" ? (() => { const [a, b] = logExtent(vals, 1.2); return log10(a, Math.min(1, b), f.m.top + f.ih, f.m.top); })() : linear(0, 1, f.m.top + f.ih, f.m.top);
  axes(f, x, y, { xTitle: "Window length n (notes)", yTitle: st.measure === "p_pair" ? "P_pair (log scale)" : "P_cross", xTicks: ns, xFmt: (v) => String(v), yFmt: st.measure === "p_pair" ? (v) => String(v) : (v) => fmt(v, 1) });
  if (ns.includes(8)) el("line", { class: "ref-line", x1: x(8), x2: x(8), y1: f.m.top, y2: f.m.top + f.ih, "aria-hidden": "true" }, f.svg);
  if (ns.includes(8)) el("text", { x: x(8) + 4, y: f.m.top + 10, text: "n = 8 (preregistered)", "aria-hidden": "true" }, f.svg);
  const g = el("g", {}, f.svg);
  for (const s of series) {
    const pts = s.pts.filter((p) => p[st.measure] > 0 || st.measure !== "p_pair");
    el("path", { class: `series-line stroke ${s.cls}`, d: linePath(pts.map((p) => [x(p.n), y(p[st.measure])])), "stroke-dasharray": DASHES[s.idx % DASHES.length] || null }, g);
    for (const p of pts) {
      const mk = marker(g, s.idx, x(p.n), y(p[st.measure]), 4, s.cls);
      bindTip(f, mk, `<b>${s.label}</b>, n = ${p.n}<br>P_cross ${fmt(p.p_cross, 3)} · P_pair ${fmt(p.p_pair)}<br>${fmt(p.types)} distinct of ${fmt(p.tokens)} windows`);
    }
  }
  const cols = [{ key: "n", label: "n", fmt: String }, ...series.map((s) => ({ label: s.key, value: (r) => r[s.key], fmt: (v) => (st.measure === "p_cross" ? fmt(v, 3) : fmt(v)) }))];
  const rows = ns.map((n) => { const r = { n }; for (const s of series) r[s.key] = s.pts.find((p) => p.n === n)?.[st.measure]; return r; });
  dataTable(host, { caption: `${st.measure === "p_pair" ? "P_pair" : "P_cross"}(n), ${st.scope === "global" ? "global" : `by period (${st.alpha})`}`, columns: cols, rows });
});

// ---------------------------------------------------------------- 5. calibration
chart("chart-calibration", "calibration", (host, d) => {
  const avail = Object.keys(d.bins?.[0]?.pred_mean || {});
  const models = ["lap", "kn", "hier"].filter((m) => avail.includes(m) || (d.models || []).includes(m));
  const labels = { ...MODEL_LABEL, ...(d.labels || {}) };
  const bins = d.bins || [];
  legend(host, models.map((m) => ({ label: `${labels[m]}${m === d.choice ? " (chosen)" : ""}`, cls: MODEL_CLASS[m] || "c7" })).concat([{ label: "Perfect calibration (y = x)", kind: "line", cls: "c7" }]));
  const all = bins.flatMap((b) => [b.obs_mean, ...models.map((m) => b.pred_mean?.[m])]);
  const [lo, hi] = logExtent(all, 1.3);
  const f = frame(host, { height: 360, margin: { left: 64, right: 20 }, ariaLabel: "Calibration: observed versus predicted occurrences for the three background models, log–log, by bins of predicted value. Data table below." });
  const x = log10(lo, hi, f.m.left, f.m.left + f.iw);
  const y = log10(lo, hi, f.m.top + f.ih, f.m.top);
  const sci = (v) => (v >= 1 ? fmt(v) : String(+v.toPrecision(1)));
  axes(f, x, y, { xTitle: "Predicted occurrences (bin mean)", yTitle: "Observed (bin mean)", xFmt: sci, yFmt: sci });
  const g = el("g", {}, f.svg);
  el("line", { class: "ref-line", x1: x(lo), y1: y(lo), x2: x(hi), y2: y(hi), "aria-hidden": "true" }, g);
  let zeros = 0;
  models.forEach((m, i) => {
    const pts = bins.filter((b) => b.pred_mean?.[m] > 0 && b.obs_mean > 0);
    zeros += bins.length - pts.length;
    el("path", { class: `series-line stroke ${MODEL_CLASS[m]}`, d: linePath(pts.map((b) => [x(b.pred_mean[m]), y(b.obs_mean)])), "stroke-dasharray": DASHES[i], opacity: 0.6 }, g);
    for (const b of pts) {
      const mk = marker(g, i, x(b.pred_mean[m]), y(b.obs_mean), 5, MODEL_CLASS[m]);
      bindTip(f, mk, `<b>${labels[m]}</b><br>Bin of ${fmt(b.k)} queries<br>Predicted ${fmt(b.pred_mean[m])} · observed ${fmt(b.obs_mean)}`);
    }
  });
  if (zeros) el("p", { class: "chart-note", text: "Bins with a zero mean cannot be drawn on a log scale; they are listed in the data table." }, host);
  if (d.summary) {
    const keys = Object.keys(d.summary);
    dataTable(host, {
      summary: "Show calibration summary",
      caption: d.summary_note ? `Calibration summary. ${d.summary_note}` : "Calibration summary (slope, mean absolute log error, log bias)",
      columns: [{ key: "k", label: "Model | windows" }, ...["Slope", "MAE (log)", "Bias (log)"].slice(0, Math.max(...Object.values(d.summary).map((v) => v.length))).map((n, i) => ({ label: n, value: (r) => r.v[i], fmt: (v) => fmt(v, 3) }))],
      rows: keys.map((k) => { const [m, sc] = k.split("|"); return { k: `${labels[m] || m} | ${sc === "todas" ? "all" : sc === "vistas" ? "seen" : sc}`, v: d.summary[k] }; }),
    });
  }
  dataTable(host, {
    caption: `Observed versus predicted by bin (binned on ${d.bin_by || "predicted value"})`,
    columns: [{ label: "Bin", value: (r) => (r.unseen ? "unseen windows" : `${fmt(r.lo)}–${fmt(r.hi)}`) }, { key: "k", label: "Queries" }, { key: "obs_mean", label: "Observed" }, ...models.map((m) => ({ label: labels[m], value: (r) => r.pred_mean?.[m] }))],
    rows: d.unseen ? [...bins, { lo: null, hi: null, k: d.unseen.k, obs_mean: d.unseen.obs, pred_mean: d.unseen.pred_mean, unseen: true }] : bins,
  });
  if (d.bins_subset || d.design) el("p", { class: "chart-note", text: [d.design, d.bins_subset ? `Bins: ${d.bins_subset}, grouped by ${d.bin_by}.` : "", d.unseen ? "Windows never seen elsewhere are summarised in the last table row." : ""].filter(Boolean).join(" · ") }, host);
});

// ---------------------------------------------------------------- 6. lambda profiles
chart("chart-lambda", "lambda", (host, d, st, redraw) => {
  const ns = d.by_n.map((r) => r.n);
  st.n ??= ns.includes(8) ? 8 : ns[0];
  st.range ||= "interior";
  const c = controls(host);
  const fs = el("fieldset", {}, c); el("legend", { text: "Window length" }, fs);
  const sel = el("select", { "aria-label": "Window length n" }, fs);
  for (const n of ns) { const o = el("option", { value: n, text: `n = ${n}` }, sel); if (n === st.n) o.selected = true; }
  sel.addEventListener("change", () => { st.n = +sel.value; redraw(); });
  segmented(c, { label: "λ range", options: [{ value: "interior", label: "Interior" }, { value: "full", label: "Full 0–1" }], value: st.range, onChange: (v) => { st.range = v; redraw(); } });

  const grid = el("div", { class: "small-multiples" }, host);
  // (a) profile for chosen n
  const pa = el("div", {}, grid);
  el("p", { class: "chart-title", text: `Held-out log-likelihood per window, n = ${st.n}` }, pa);
  const pb = el("div", {}, grid);
  el("p", { class: "chart-title", text: "Selected λ* by window length" }, pb);
  const prof = (d.grid[String(st.n)] || []).filter((p) => st.range === "full" || (p.lambda > 0 && p.lambda < 1));
  const row = d.by_n.find((r) => r.n === st.n);
  const f = frame(pa, { height: 300, margin: { left: 64, right: 16 }, ariaLabel: `Log-likelihood profile over the interpolation weight λ for n = ${st.n}; maximum at λ* marked.`, minWidth: 260 });
  const ll = prof.map((p) => p.loglik);
  const pad = (Math.max(...ll) - Math.min(...ll)) * 0.08 || 0.01;
  const x = linear(st.range === "full" ? 0 : Math.min(...prof.map((p) => p.lambda)), st.range === "full" ? 1 : Math.max(...prof.map((p) => p.lambda)), f.m.left, f.m.left + f.iw);
  const y = linear(Math.min(...ll) - pad, Math.max(...ll) + pad, f.m.top + f.ih, f.m.top);
  axes(f, x, y, { xTitle: "λ (interpolation weight)", yTitle: "log-likelihood / window", xFmt: (v) => fmt(v, 2), yFmt: (v) => fmt(v, 2) });
  const g = el("g", {}, f.svg);
  el("path", { class: "series-line stroke c1", d: linePath(prof.map((p) => [x(p.lambda), y(p.loglik)])) }, g);
  for (const p of prof) {
    const star = row && Math.abs(p.lambda - row.lambda_star) < 1e-9;
    const mk = marker(g, star ? 3 : 0, x(p.lambda), y(p.loglik), star ? 7 : 3.5, star ? "c6" : "c1");
    if (star) mk.classList.add("op-point");
    bindTip(f, mk, `<b>λ = ${fmt(p.lambda, 2)}</b>${star ? " (λ*)" : ""}<br>log-lik ${fmt(p.loglik, 3)}<br>slope ${fmt(p.slope, 3)} · obs/pred ${fmt(p.obs_pred, 3)}`);
  }
  if (row) el("text", { class: "direct-label", x: Math.min(x(row.lambda_star) + 10, f.m.left + f.iw - 40), y: f.m.top + 12, text: `λ* = ${fmt(row.lambda_star, 2)}` }, g);
  // (b) λ*(n)
  const f2 = frame(pb, { height: 300, margin: { left: 50, right: 16 }, ariaLabel: "λ* by window length n.", minWidth: 260 });
  const x2 = linear(Math.min(...ns) - 0.5, Math.max(...ns) + 0.5, f2.m.left, f2.m.left + f2.iw);
  const y2 = linear(0, 1, f2.m.top + f2.ih, f2.m.top);
  axes(f2, x2, y2, { xTitle: "n", yTitle: "λ*", xTicks: ns, xFmt: String, yFmt: (v) => fmt(v, 1) });
  const g2 = el("g", {}, f2.svg);
  el("path", { class: "series-line stroke c6", d: linePath(d.by_n.map((r) => [x2(r.n), y2(r.lambda_star)])), opacity: 0.6 }, g2);
  for (const r of d.by_n) {
    const mk = marker(g2, 3, x2(r.n), y2(r.lambda_star), r.n === st.n ? 7 : 5, "c6");
    if (r.n === st.n) mk.classList.add("op-point");
    bindTip(f2, mk, `<b>n = ${r.n}</b><br>λ* = ${fmt(r.lambda_star, 2)}<br>slope ${fmt(r.slope, 3)} · MAE(log) ${fmt(r.mae_log, 3)}<br>${fmt(r.n_windows)} held-out windows`);
  }
  dataTable(host, {
    caption: "λ* and calibration by window length",
    columns: [{ key: "n", label: "n", fmt: String }, { key: "lambda_star", label: "λ*", fmt: (v) => fmt(v, 2) }, { key: "slope", label: "Slope", fmt: (v) => fmt(v, 3) }, { key: "mae_log", label: "MAE (log)", fmt: (v) => fmt(v, 3) }, { key: "bias_log", label: "Bias (log)", fmt: (v) => fmt(v, 3) }, { key: "obs_pred", label: "Obs/pred", fmt: (v) => fmt(v, 3) }, { key: "loglik_per_window", label: "Log-lik/window", fmt: (v) => fmt(v, 3) }, { key: "n_windows", label: "Windows" }],
    rows: d.by_n,
  });
  dataTable(host, {
    summary: `Show full λ grid for n = ${st.n}`,
    caption: `Log-likelihood over the full λ grid, n = ${st.n}`,
    columns: [{ key: "lambda", label: "λ", fmt: (v) => fmt(v, 2) }, { key: "loglik", label: "Log-lik/window", fmt: (v) => fmt(v, 3) }, { key: "slope", label: "Slope", fmt: (v) => fmt(v, 3) }, { key: "obs_pred", label: "Obs/pred", fmt: (v) => fmt(v, 3) }],
    rows: d.grid[String(st.n)] || [],
  });
});

// ---------------------------------------------------------------- 7. ROC and PR
chart("chart-rocpr", "thresholds", (host, d) => {
  const curves = Object.keys(d.curves || {});
  const label = (k) => (k === "DF→E" ? "DF then E" : k);
  legend(host, curves.map((k) => ({ label: `${label(k)} (AUC ${fmt(d.curves[k].AUC, 2)}, AP ${fmt(d.curves[k].AP, 2)})`, kind: "line", cls: CURVE_CLASS[k] || "c7" }))
    .concat([{ label: "Chance / prevalence", kind: "line", cls: "c7" }]));
  const grid = el("div", { class: "small-multiples" }, host);
  // ROC
  const pa = el("div", {}, grid);
  el("p", { class: "chart-title", text: "ROC: true-positive vs false-positive rate" }, pa);
  const pb = el("div", {}, grid);
  el("p", { class: "chart-title", text: "Precision–recall" }, pb);
  const f = frame(pa, { height: 320, margin: { left: 54, right: 16 }, ariaLabel: "ROC curves for DF, E and DF then E on the control pairs, with the 5 % false-positive-rate operating points. Summary table below.", minWidth: 260 });
  const x = linear(0, 1, f.m.left, f.m.left + f.iw), y = linear(0, 1, f.m.top + f.ih, f.m.top);
  axes(f, x, y, { xTitle: "False-positive rate", yTitle: "Sensitivity (TPR)", xFmt: (v) => fmt(v, 1), yFmt: (v) => fmt(v, 1) });
  const g = el("g", {}, f.svg);
  el("line", { class: "ref-line", x1: x(0), y1: y(0), x2: x(1), y2: y(1), "aria-hidden": "true" }, g);
  el("line", { class: "ref-line", x1: x(0.05), y1: y(0), x2: x(0.05), y2: y(1), "aria-hidden": "true", "stroke-dasharray": "1 3" }, g);
  el("text", { x: x(0.05) + 4, y: f.m.top + 10, text: "FPR 5 %", "aria-hidden": "true" }, g);
  curves.forEach((k, i) => {
    const roc = d.curves[k].roc || [];
    el("path", { class: `series-line stroke ${CURVE_CLASS[k]}`, d: linePath(roc.map(([a, b]) => [x(a), y(b)]), f.iw * 0.2), "stroke-dasharray": DASHES[i] }, g);
  });
  const ops = [["DF", d.DF], ["E", d.E], ["DF→E", d.combined]].filter(([, v]) => v && v.FPR !== undefined);
  ops.forEach(([k, v], i) => {
    const mk = marker(g, i, x(v.FPR), y(v.sensitivity), 6, CURVE_CLASS[k]);
    mk.classList.add("op-point");
    bindTip(f, mk, `<b>${label(k)} at its preregistered threshold</b><br>FPR ${fmt(v.FPR, 3)} · sensitivity ${fmt(v.sensitivity, 3)}`);
  });
  // PR
  const f2 = frame(pb, { height: 320, margin: { left: 54, right: 16 }, ariaLabel: "Precision–recall curves for DF, E and DF then E, with the prevalence baseline.", minWidth: 260 });
  const x2 = linear(0, 1, f2.m.left, f2.m.left + f2.iw), y2 = linear(0, 1, f2.m.top + f2.ih, f2.m.top);
  axes(f2, x2, y2, { xTitle: "Recall (sensitivity)", yTitle: "Precision", xFmt: (v) => fmt(v, 1), yFmt: (v) => fmt(v, 1) });
  const g2 = el("g", {}, f2.svg);
  if (d.prevalence !== undefined) {
    el("line", { class: "ref-line", x1: x2(0), x2: x2(1), y1: y2(d.prevalence), y2: y2(d.prevalence), "aria-hidden": "true" }, g2);
    el("text", { x: x2(1) - 4, y: y2(d.prevalence) - 5, "text-anchor": "end", text: `prevalence ${fmt(d.prevalence, 2)}`, "aria-hidden": "true" }, g2);
  }
  curves.forEach((k, i) => {
    const pr = d.curves[k].pr || [];
    el("path", { class: `series-line stroke ${CURVE_CLASS[k]}`, d: linePath(pr.map(([a, b]) => [x2(a), y2(b)]), f2.iw * 0.2), "stroke-dasharray": DASHES[i] }, g2);
  });
  ops.forEach(([k, v], i) => {
    el("line", { class: `stroke ${CURVE_CLASS[k]}`, x1: x2(v.sensitivity), x2: x2(v.sensitivity), y1: f2.m.top + f2.ih, y2: f2.m.top + f2.ih - 14, "stroke-width": 3, "aria-hidden": "true" }, g2);
  });
  dataTable(host, {
    caption: "Discrimination on the control pairs and operating points at FPR ≤ 5 %",
    columns: [{ key: "k", label: "Score" }, { key: "AUC", label: "ROC AUC", fmt: (v) => fmt(v, 3) }, { key: "AP", label: "Average precision", fmt: (v) => fmt(v, 3) }, { key: "FPR", label: "FPR at threshold", fmt: (v) => fmt(v, 3) }, { key: "sens", label: "Sensitivity at threshold", fmt: (v) => fmt(v, 3) }],
    rows: curves.map((k) => { const op = ops.find(([kk]) => kk === k)?.[1] || {}; return { k: label(k), AUC: d.curves[k].AUC, AP: d.curves[k].AP, FPR: op.FPR, sens: op.sensitivity }; }),
  });
  if (d.n_instances) el("p", { class: "chart-note", text: `Control instances: ${fmt(d.n_instances.pos)} positive and ${fmt(d.n_instances.neg)} negative shared windows (n = ${d.n}, stratum ${d.stratum}). Curves are dense; the table gives the summary. A gap in a curve means no threshold value falls in that range (it is not interpolated).` }, host);
});

// ---------------------------------------------------------------- 8. literal sensitivity
chart("chart-literal", "literal", (host, d, st, redraw, extra) => {
  if (!d || d.status !== "measured" || !d.LS1) {
    emptyNote(host, "Not yet measured", d?.note || "The sensitivity of the thresholds to literal quotation has not been measured yet.");
    return;
  }
  const variants = Object.keys(d.LS1.results || {});
  st.variant ||= variants.includes("default") ? "default" : variants[0];
  const vLabel = (v) => (v === "default" ? "Default background" : v === "noBeethoven" ? "Without Beethoven" : v);
  if (variants.length > 1) segmented(controls(host), { label: "Background", options: variants.map((v) => ({ value: v, label: vLabel(v) })), value: st.variant, onChange: (v) => { st.variant = v; redraw(); } });
  if (d.variants?.[st.variant]) el("p", { class: "chart-note", text: `Background: ${d.variants[st.variant]}.` }, host);
  const pairName = Object.fromEntries((d.pairs || []).map((p) => [p.id, p.work || p.id]));
  const PAIR_CLASS = ["c1", "c2", "c3", "c4"];
  const ls1 = d.LS1.results[st.variant] || {};
  const pairIds = (d.pairs || []).map((p) => p.id).filter((id) => ls1[id]);
  const rows1 = [...pairIds.map((id, i) => ({ id, label: pairName[id], cls: PAIR_CLASS[i % 4], idx: i, ...ls1[id] })),
    ...(ls1.global ? [{ id: "global", label: "All pairs", cls: "c6", idx: 4, ...ls1.global }] : [])];
  const modelSens = extra.thresholds?.DF?.sensitivity;

  legend(host, [
    ...pairIds.map((id, i) => ({ label: pairName[id], cls: PAIR_CLASS[i % 4] })),
    { label: "All pairs", cls: "c6" },
    ...(modelSens !== undefined ? [{ label: "Sensitivity on documented modelling (reference)", kind: "line", cls: "c7" }] : []),
  ]);
  const grid = el("div", { class: "small-multiples" }, host);
  const pa = el("div", {}, grid);
  el("p", { class: "chart-title", text: "Sensitivity of DF ≤ t_DF, literal arrangements" }, pa);
  const pb = el("div", {}, grid);
  el("p", { class: "chart-title", text: "Fragment-test power by passage length" }, pb);

  // Panel 1: sensitivity per pair and overall
  const f = frame(pa, { height: 40 + rows1.length * 40, margin: { left: 112, right: 16, bottom: 40 }, ariaLabel: "Share of shared 8-note windows of literal arrangements flagged by DF at the frozen threshold, per pair and overall, with 95 % Wilson intervals and the sensitivity on documented modelling as reference.", minWidth: 260 });
  const x = linear(0, 1, f.m.left, f.m.left + f.iw);
  const y = band(rows1.map((r) => r.id), f.m.top, f.m.top + f.ih, 0.3);
  const g = el("g", {}, f.svg);
  for (const t of x.ticks(5)) {
    el("line", { class: "gridline", x1: x(t), x2: x(t), y1: f.m.top, y2: f.m.top + f.ih }, g);
    el("text", { x: x(t), y: f.m.top + f.ih + 16, "text-anchor": "middle", text: fmt(t, 1) }, g);
  }
  el("text", { class: "axis-title", x: f.m.left + f.iw / 2, y: f.h - 4, "text-anchor": "middle", text: "Sensitivity (share of shared windows)" }, g);
  if (modelSens !== undefined) {
    el("line", { class: "ref-line", x1: x(modelSens), x2: x(modelSens), y1: f.m.top, y2: f.m.top + f.ih, "aria-hidden": "true" }, g);
    el("text", { x: x(modelSens) + 4, y: f.m.top + 2, "dominant-baseline": "hanging", text: `modelling: ${fmt(modelSens, 3)}`, "aria-hidden": "true" }, g);
  }
  for (const r of rows1) {
    const cy = y(r.id) + y.bandwidth / 2;
    el("text", { x: f.m.left - 8, y: cy, "text-anchor": "end", "dominant-baseline": "middle", text: r.label, "font-weight": r.id === "global" ? 600 : null }, g);
    if (r.DF?.ci95) el("line", { class: "ci", x1: x(r.DF.ci95[0]), x2: x(r.DF.ci95[1]), y1: cy, y2: cy }, g);
    const mk = marker(g, r.idx, x(r.DF.rate), cy, 6, r.cls);
    bindTip(f, mk, `<b>${r.label}</b><br>DF: ${fmt(r.DF.k)} of ${fmt(r.DF.n)} shared windows (${fmt(r.DF.rate, 3)}; 95 % ${fmt(r.DF.ci95[0], 3)}–${fmt(r.DF.ci95[1], 3)})<br>E: ${fmt(r.E?.rate, 3)}${modelSens !== undefined ? `<br>Reference, documented modelling: ${fmt(modelSens, 3)}` : ""}`);
  }

  // Panel 2: LS-2 power by fragment length
  const ls2 = d.LS2?.results?.[st.variant] || {};
  const series = [...pairIds.filter((id) => ls2[id]).map((id, i) => ({ id, label: pairName[id], cls: PAIR_CLASS[i % 4], idx: i, pts: ls2[id] })),
    ...(ls2.all_pairs ? [{ id: "all", label: "All pairs", cls: "c6", idx: 4, pts: ls2.all_pairs, bold: true }] : [])];
  const lens = [...new Set(series.flatMap((s) => s.pts.map((p) => p.length_bars)))].sort((a, b) => a - b);
  const f2 = frame(pb, { height: 40 + rows1.length * 40, margin: { left: 54, right: 16, bottom: 40 }, ariaLabel: "Power of the fragment test against passage length in bars, per pair and overall, with 95 % Wilson intervals.", minWidth: 260 });
  const lo = Math.min(...series.flatMap((s) => s.pts.map((p) => p.power.ci95[0])));
  const ymin = Math.max(0, Math.floor(lo * 20) / 20 - 0.05);
  const x2 = linear(lens[0] - 2, lens[lens.length - 1] + 2, f2.m.left, f2.m.left + f2.iw);
  const y2 = linear(ymin, 1, f2.m.top + f2.ih, f2.m.top);
  axes(f2, x2, y2, { xTitle: "Passage length (bars)", yTitle: `Power (axis from ${fmt(ymin, 2)})`, xTicks: lens, xFmt: String, yFmt: (v) => fmt(v, 2) });
  const g2 = el("g", {}, f2.svg);
  series.forEach((s, si) => {
    const off = (si - (series.length - 1) / 2) * 3; // small horizontal dodge so intervals do not overlap
    el("path", { class: `series-line stroke ${s.cls}`, d: linePath(s.pts.map((p) => [x2(p.length_bars) + off, y2(p.power.rate)])), "stroke-dasharray": DASHES[si % DASHES.length] || null, "stroke-width": s.bold ? 3 : 2 }, g2);
    for (const p of s.pts) {
      const px = x2(p.length_bars) + off;
      el("line", { class: "ci", x1: px, x2: px, y1: y2(p.power.ci95[0]), y2: y2(p.power.ci95[1]) }, g2);
      const mk = marker(g2, s.idx, px, y2(p.power.rate), s.bold ? 5 : 4, s.cls);
      bindTip(f2, mk, `<b>${s.label}</b>, ${p.length_bars} bars${p.length_windows ? ` (${fmt(p.length_windows)} windows)` : ""}<br>Power ${fmt(p.power.rate, 3)}: ${fmt(p.power.k)} of ${fmt(p.power.n)} fragments (95 % ${fmt(p.power.ci95[0], 3)}–${fmt(p.power.ci95[1], 3)})`);
    }
  });

  const cav = el("ul", { class: "chart-note caveats" }, host);
  for (const c of d.caveats_en || []) el("li", { text: c }, cav);
  if (d.note) el("p", { class: "chart-note", text: d.note }, host);

  dataTable(host, {
    caption: `Literal-quotation sensitivity of the frozen thresholds (${vLabel(st.variant).toLowerCase()})`,
    columns: [{ key: "label", label: "Pair" }, { label: "Shared windows", value: (r) => r.instances },
      { label: "DF flagged", value: (r) => r.DF?.k }, { label: "DF sensitivity", value: (r) => r.DF?.rate, fmt: (v) => fmt(v, 3) },
      { label: "95 % interval", value: (r) => `${fmt(r.DF?.ci95?.[0], 3)}–${fmt(r.DF?.ci95?.[1], 3)}` },
      { label: "E sensitivity", value: (r) => r.E?.rate, fmt: (v) => fmt(v, 3) }],
    rows: rows1,
  });
  const rows2 = series.flatMap((s) => s.pts.map((p) => ({ label: s.label, ...p })));
  dataTable(host, {
    summary: "Show fragment-test power table",
    caption: `Fragment test (LS-2) power by passage length; α = ${fmt(d.LS2?.alpha)}, ${fmt(d.LS2?.n_obs)} fragments per pair and length, ${fmt(d.LS2?.n_null)} null fragments`,
    columns: [{ key: "label", label: "Pair" }, { key: "length_bars", label: "Bars", fmt: String }, { label: "Fragments detected", value: (r) => `${fmt(r.power.k)} / ${fmt(r.power.n)}` },
      { label: "Power", value: (r) => r.power.rate, fmt: (v) => fmt(v, 3) }, { label: "95 % interval", value: (r) => `${fmt(r.power.ci95[0], 3)}–${fmt(r.power.ci95[1], 3)}` }],
    rows: rows2,
  });
}, ["thresholds"]);

// ---------------------------------------------------------------- nav: mark current section
function navCurrent() {
  const links = [...document.querySelectorAll('#site-nav a[href^="#"]')];
  if (!links.length || !("IntersectionObserver" in window)) return;
  const byId = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) {
      links.forEach((a) => a.removeAttribute("aria-current"));
      byId.get(e.target.id)?.setAttribute("aria-current", "true");
    }
  }, { rootMargin: "-40% 0px -55% 0px" });
  for (const id of byId.keys()) { const s = document.getElementById(id); if (s) io.observe(s); }
}

// ---------------------------------------------------------------- init
async function init() {
  await injectMethod();
  await Promise.all([fillNumbers(), renderStatus(), ...Object.keys(renderers).map(renderChart)]);
  navCurrent();
  // Print: closed <details> content is not printed by browsers, so open data tables while printing.
  let opened = [];
  window.addEventListener("beforeprint", () => { opened = [...document.querySelectorAll("details.data-table:not([open])")]; opened.forEach((d) => (d.open = true)); });
  window.addEventListener("afterprint", () => { opened.forEach((d) => (d.open = false)); opened = []; });
  // Re-render charts on width change (responsive SVG geometry), debounced.
  let lastW = window.innerWidth, timer;
  window.addEventListener("resize", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (Math.abs(window.innerWidth - lastW) < 24) return;
      lastW = window.innerWidth;
      for (const id of Object.keys(renderers)) document.getElementById(id)?._redraw?.();
    }, 150);
  });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
else init();
