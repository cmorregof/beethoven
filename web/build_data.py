"""Exporta los agregados de la web de acompañamiento (web/data/*.json) desde resultados versionados.

Uso (desde la raíz del repo):  /Users/cmorregof/Personal/Beethoven/.venv/bin/python web/build_data.py

Reglas (paper/AGENTS_RULES.md):
- Solo lee archivos versionados del repo (results/**, corpus/works.csv, docs/DECISIONES.md,
  decisions/D-41_preregistro.md). No lee cachés, parquet ni partituras.
- Solo escribe agregados: nada de filas por obra, puntuaciones por ventana ni secuencias de
  intervalos (licencia NC de DCML, D-12).
- Guardia D-41: toda columna de work_id leída pasa por scripts/preregistration_guard.py; el
  catálogo se filtra con filter_catalog_rows y se comprueba con check_catalog_rows.
- Si dos fuentes no cuadran, el script aborta (MismatchError) y no escribe nada: se informa, no se arregla.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from preregistration_guard import check_catalog_rows, check_ids, filter_catalog_rows  # noqa: E402
from thresholds_n8 import roc  # noqa: E402  (misma lógica que las curvas versionadas)

OUT = ROOT / "web" / "data"
GEN = "web/build_data.py"
PERIODS = ["<1750", "1750–1800", "1800–1830", "1830–1900", ">1900", "unknown"]
MOTIFS = [
    ("D1", "exact pitches (0, 0, −4): three repeated notes and a falling major third"),
    ("D2", "generalised pitches (0, 0, −3 | −4): repeated notes and a falling third"),
    ("D3", "rhythm only: three equal durations followed by one at least twice as long"),
    ("D4", "D2 and D3 together (the generalised short-short-short-long motif)"),
    ("D5", "D4 with the attack of the long note on a weak metrical position"),
]
TODAY = date.today().isoformat()
NUMBERS: dict[str, dict] = {}
NUM_SOURCES: set[str] = set()


class MismatchError(SystemExit):
    def __init__(self, msg: str):
        super().__init__(4)
        self.msg = msg

    def __str__(self) -> str:
        return self.msg


def mismatch(what: str, a, b):
    print(f"NO CUADRA: {what}: {a!r} != {b!r}", file=sys.stderr)
    raise MismatchError(f"NO CUADRA: {what}: {a!r} != {b!r}. No se escribe nada; informar a la torre.")


def same(what: str, a, b, tol: float = 0.0):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if abs(a - b) > tol:
            mismatch(what, a, b)
    elif a != b:
        mismatch(what, a, b)


def read_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def read_csv(rel: str) -> list[dict]:
    with open(ROOT / rel, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------- formateo de números para numbers.json ----------
def f_int(x) -> str:
    return f"{int(round(x)):,}"


def f_fix(d: int):
    return lambda x: f"{x:,.{d}f}".replace("-", "−")


def f_pct(d: int):
    return lambda x: f"{x:.{d}f} %"


def f_sci(d: int = 2):
    def f(x):
        e = int(math.floor(math.log10(abs(x))))
        m = x / 10 ** e
        sup = str(e).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))
        return f"{m:.{d}f} × 10{sup}"
    return f


def num(key: str, value, fmt, source: str):
    assert re.fullmatch(r"[a-z0-9_]+", key), key
    if key in NUMBERS:
        same(f"clave duplicada {key}", NUMBERS[key]["value"], value)
    v = value.item() if hasattr(value, "item") else value
    NUMBERS[key] = {"value": v, "text": fmt(v), "source": source}
    NUM_SOURCES.add(source.split(":")[0])


def pkey(p: str) -> str:
    return {"<1750": "pre1750", "1750–1800": "1750_1800", "1800–1830": "1800_1830",
            "1830–1900": "1830_1900", ">1900": "post1900", "unknown": "unknown"}[p]


def meta(sources: list[str]) -> dict:
    return {"source": sources, "generated_by": GEN, "generated_at": TODAY}


def write(name: str, obj: dict, store: dict):
    store[name] = obj


# ---------- corpus ----------
def build_corpus(br: dict) -> dict:
    src_cat, src_br = "corpus/works.csv", "results/base_rate.json"
    rows = read_csv(src_cat)
    allowed = filter_catalog_rows(rows)
    check_catalog_rows(allowed, context="build_data:corpus")
    prim = [r for r in allowed if r["is_primary"] == "1" and r["in_analysis"] == "1"]
    works_cat = {r["work_id"] for r in prim}
    same("obras del catálogo (works.csv sin objetivo) vs base_rate.works_in_catalog",
         len(works_cat), br["works_in_catalog"])
    missing = br["works_missing_cache"]
    check_ids(missing, context="build_data:works_missing_cache")
    S = br["strata"]
    allw = S["all"]["all"]
    same("obras analizadas = catálogo − sin caché", len(works_cat) - len(missing), allw["works"])
    for k in ("works", "windows", "notes"):
        same(f"suma por periodo de {k}", sum(S["period"][p][k] for p in PERIODS), allw[k])
        same(f"suma por colección de {k}", sum(v[k] for v in S["collection"].values()), allw[k])
    check_ids(S["composer"].keys(), context="build_data:strata.composer")
    check_ids(S["collection"].keys(), context="build_data:strata.collection")

    by_period = []
    for p in PERIODS:
        st = S["period"][p]
        by_period.append({"period": p, "units": sum(r["period"] == p for r in prim),
                          "works_catalog": len({r["work_id"] for r in prim if r["period"] == p}),
                          "works": st["works"], "windows": st["windows"], "notes": st["notes"]})
    by_coll = []
    for c, st in sorted(S["collection"].items()):
        us = [r for r in prim if r["collection"] == c]
        cps = sorted({k.split("|")[1] for k in S["collection_x_period"] if k.split("|")[0] == c},
                     key=PERIODS.index)
        by_coll.append({"collection": c, "units": len(us), "works_catalog": len({r["work_id"] for r in us}),
                        "works": st["works"], "windows": st["windows"], "notes": st["notes"], "periods": cps,
                        "licenses": sorted({r["license"] for r in us})})
    same("unidades por colección suman el total", sum(c["units"] for c in by_coll), len(prim))
    tot = {"units": len(prim), "works_catalog": len(works_cat), "works_missing_cache": len(missing),
           "works": allw["works"], "windows": allw["windows"], "notes": allw["notes"],
           "collections": len(by_coll)}
    loc = "results/base_rate.json:strata.all.all"
    num("corpus_units", tot["units"], f_int, "corpus/works.csv:is_primary=1,in_analysis=1,sin objetivo")
    num("corpus_works_catalog", tot["works_catalog"], f_int, "results/base_rate.json:works_in_catalog")
    num("corpus_works_missing_cache", tot["works_missing_cache"], f_int, "results/base_rate.json:works_missing_cache")
    num("corpus_works", tot["works"], f_int, loc + ".works")
    num("corpus_windows", tot["windows"], f_int, loc + ".windows")
    num("corpus_windows_millions", tot["windows"] / 1e6, f_fix(2), loc + ".windows")
    num("corpus_notes", tot["notes"], f_int, loc + ".notes")
    num("corpus_collections", tot["collections"], f_int, "results/base_rate.json:strata.collection")
    for row in by_period:
        num(f"corpus_works_{pkey(row['period'])}", row["works"], f_int, f"{src_br}:strata.period.{row['period']}.works")
        num(f"corpus_windows_{pkey(row['period'])}", row["windows"], f_int, f"{src_br}:strata.period.{row['period']}.windows")
    return {**meta([src_cat, src_br]), "windows_n": 4, "period_order": PERIODS, "totals": tot,
            "note": "Units = primary files/movements in analysis; works_catalog from corpus/works.csv; works, "
                    "windows and notes = works actually analysed (results/base_rate.json). The two preregistered "
                    "target works are excluded everywhere.",
            "by_period": by_period, "by_collection": by_coll}


# ---------- tasas base y nulo ----------
def build_base_rates(br: dict) -> dict:
    S = br["strata"]
    keep = ("works", "windows", "counts", "rate_per_100k", "prevalence", "prevalence_pct")
    by_period = [{"period": p, **{k: S["period"][p][k] for k in keep}} for p in PERIODS]
    src = "results/base_rate.json"
    for row in by_period + [{"period": "all", **{k: S["all"]["all"][k] for k in keep}}]:
        for d in ("D1", "D2", "D3", "D4", "D5"):
            same(f"tasa {d} {row['period']}", row["rate_per_100k"][d], row["counts"][d] / row["windows"] * 1e5, 1e-9)
    for p in PERIODS + ["all"]:
        st = S["all"]["all"] if p == "all" else S["period"][p]
        loc = f"{src}:strata.{'all.all' if p == 'all' else 'period.' + p}"
        k = "all" if p == "all" else pkey(p)
        num(f"baserate_d4_rate_{k}", st["rate_per_100k"]["D4"], f_fix(2), loc + ".rate_per_100k.D4")
        num(f"baserate_d4_prev_{k}", st["prevalence_pct"]["D4"], f_pct(1), loc + ".prevalence_pct.D4")
        num(f"baserate_d2_rate_{k}", st["rate_per_100k"]["D2"], f_fix(2), loc + ".rate_per_100k.D2")
    a, b = S["period"]["1750–1800"], S["period"]["1800–1830"]
    num("baserate_d4_rate_1750_1830", (a["counts"]["D4"] + b["counts"]["D4"]) / (a["windows"] + b["windows"]) * 1e5,
        f_fix(2), f"{src}:strata.period.(1750–1800+1800–1830).counts.D4/windows")
    return {**meta([src]), "motifs": [{"id": i, "label": l} for i, l in MOTIFS], "window": "4 notes",
            "period_order": PERIODS, "by_period": by_period,
            "all": {k: S["all"]["all"][k] for k in keep}}


def build_null(br: dict) -> dict:
    S, src = br["strata"], "results/base_rate.json"

    def rows_for(m):
        out = []
        for kind, keys in (("all", ["all"]), ("period", PERIODS)):
            for k in keys:
                st = S["all"]["all"] if kind == "all" else S["period"][k]
                nl = st["null"][m]
                same(f"ratio nulo {m} {k}", nl["ratio"], nl["obs"] / nl["mean"] if nl["mean"] else 0.0, 1e-9)
                out.append({"stratum": k, "kind": kind, "works_perm": st["perm_works"], "obs": nl["obs"],
                            "null_mean": nl["mean"], "ci95": nl["ci95"], "ratio": nl["ratio"], "p": nl["p"],
                            "n_perm": nl["n_perm"]})
        return out

    d4 = rows_for("D4")
    for r in d4:
        same(f"n_perm {r['stratum']}", r["n_perm"], br["n_perm"])
        k = "all" if r["kind"] == "all" else pkey(r["stratum"])
        loc = f"{src}:strata.{'all.all' if k == 'all' else 'period.' + r['stratum']}.null.D4"
        num(f"null_d4_obs_{k}", r["obs"], f_int, loc + ".obs")
        num(f"null_d4_mean_{k}", r["null_mean"], f_fix(1), loc + ".mean")
        num(f"null_d4_ci_lo_{k}", r["ci95"][0], f_int, loc + ".ci95[0]")
        num(f"null_d4_ci_hi_{k}", r["ci95"][1], f_int, loc + ".ci95[1]")
        num(f"null_d4_ratio_{k}", r["ratio"], f_fix(2), loc + ".ratio")
        num(f"null_d4_p_{k}", r["p"], f_fix(3), loc + ".p")
    num("null_n_perm", br["n_perm"], f_int, f"{src}:n_perm")
    num("null_works_perm_all", S["all"]["all"]["perm_works"], f_int, f"{src}:strata.all.all.perm_works")
    num("null_min_windows", br["min_windows_for_perm"], f_int, f"{src}:min_windows_for_perm")
    return {**meta([src]), "motif": "D4", "seed": br["seed"], "n_perm": br["n_perm"],
            "null": "independent within-voice shuffle of intervals and durations (works with ≥ "
                    f"{br['min_windows_for_perm']} notes)",
            "strata": d4, "other_motifs": {"D2": rows_for("D2"), "D3": rows_for("D3")}}


# ---------- unicidad ----------
def build_uniqueness(br: dict) -> dict:
    src = "results/uniqueness.json"
    u = read_json(src)
    same("obras en unicidad vs base_rate", u["works"], br["strata"]["all"]["all"]["works"])
    for p in PERIODS:
        same(f"obras por periodo en unicidad {p}", u["works_by_period"][p], br["strata"]["period"][p]["works"])
    same("tokens n=4 IV vs ventanas de 4 notas", next(r["tokens"] for r in u["curve"]["IV"] if r["n"] == 4),
         br["strata"]["all"]["all"]["windows"])
    keep = ("n", "p_cross", "p_pair", "types", "unique_types", "tokens", "works")
    glob = {a: [{k: r[k] for k in keep} for r in u["curve"][a]] for a in ("IV", "IVR")}
    byp = {a: {p: [{k: r[k] for k in keep} for r in u["curve_by_period"][a][p]] for p in PERIODS} for a in ("IV", "IVR")}
    for a in ("IV", "IVR"):
        for r in glob[a]:
            if r["n"] in (4, 6, 8, 10, 12):
                loc = f"{src}:curve.{a}[n={r['n']}]"
                num(f"uniq_pcross_{a.lower()}_n{r['n']}", 100 * r["p_cross"], f_pct(1), loc + ".p_cross")
                num(f"uniq_ppair_{a.lower()}_n{r['n']}", 100 * r["p_pair"], f_pct(2), loc + ".p_pair")
    for p in ("1750–1800", "1800–1830"):
        r = next(x for x in byp["IVR"][p] if x["n"] == 8)
        num(f"uniq_pcross_ivr_n8_{pkey(p)}", 100 * r["p_cross"], f_pct(1), f"{src}:curve_by_period.IVR.{p}[n=8].p_cross")
    return {**meta([src]), "ns": u["ns"], "alphabets": ["IV", "IVR"],
            "alphabet_labels": {"IV": "intervals only", "IVR": "intervals + rhythm class"},
            "definitions": {"p_cross": "share of n-gram tokens whose type also occurs in another work",
                            "p_pair": "probability that a random pair of works shares the type of a random token"},
            "period_order": PERIODS, "works_by_period": u["works_by_period"], "global": glob, "by_period": byp}


# ---------- calibración ----------
def _metrics(obs, pred):
    lo, lp = np.log(obs + 0.05), np.log(pred + 0.05)
    slope = float(np.polyfit(lp, lo, 1)[0])
    return slope, float(np.mean(np.abs(lo - lp))), float(np.mean(lo - lp))


def build_calibration() -> dict:
    src_j, src_c, src_m = "results/kn_calibration.json", "results/kn_calibration.csv", "results/kn_calibration.md"
    kj = read_json(src_j)
    rows = read_csv(src_c)
    check_ids([r["work"] for r in rows], context="build_data:kn_calibration.work")
    check_ids([r["composer"] for r in rows], context="build_data:kn_calibration.composer")
    obs = np.array([float(r["obs_occ"]) for r in rows])
    pred = {m: np.array([float(r[f"pred_occ_{m}"]) for r in rows]) for m in ("lap", "kn", "hier")}
    seen = obs >= 1
    summ = {}
    for m in ("lap", "kn", "hier"):
        for sname, sel in (("todas", np.ones_like(seen)), ("vistas", seen)):
            got = _metrics(obs[sel], pred[m][sel])
            for i, field in enumerate(("pendiente", "MAE", "sesgo")):
                same(f"calibración {m}|{sname} {field} (recalculado vs kn_calibration.json)",
                     round(got[i], 6), round(kj["summary"][f"{m}|{sname}"][i], 6))
            summ[f"{m}|{sname}"] = kj["summary"][f"{m}|{sname}"]
    # tabla del .md: obs/pred por tramo de E predicho (KN), ventanas vistas
    md = (ROOT / src_m).read_text(encoding="utf-8")
    md_rows = re.findall(r"^\| \[([\d.e+]+), ([\d.e+]+)\) \| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", md, re.M)
    if len(md_rows) != 6:
        mismatch("filas de tramos E en kn_calibration.md", len(md_rows), 6)
    edges = [float(r[0]) for r in md_rows] + [float(md_rows[-1][1])]
    bins = []
    for i, r in enumerate(md_rows):
        lo, hi = edges[i], edges[i + 1]
        sel = seen & (pred["kn"] >= lo) & (pred["kn"] < hi)
        k = int(sel.sum())
        same(f"n del tramo [{lo}, {hi}) vs kn_calibration.md", k, int(r[2]))
        ratio = {m: float(obs[sel].sum() / pred[m][sel].sum()) for m in ("lap", "kn", "hier")}
        for j, m in enumerate(("lap", "kn", "hier")):
            same(f"obs/pred {m} tramo [{lo}, {hi}) vs kn_calibration.md", round(ratio[m], 2), float(r[3 + j]), 0.0051)
        bins.append({"lo": lo, "hi": None if hi >= 1e12 else hi, "k": k, "obs_sum": float(obs[sel].sum()),
                     "obs_mean": float(obs[sel].mean()),
                     "pred_mean": {m: float(pred[m][sel].mean()) for m in ("lap", "kn", "hier")},
                     "obs_pred": ratio})
    total_ratio = {m: float(obs.sum() / pred[m].sum()) for m in ("lap", "kn", "hier")}
    for m, lab in (("lap", "Laplace \\(cota superior\\)"), ("kn", "Kneser-Ney"), ("hier", "jerárquico")):
        mm = re.search(rf"^\| {lab} \| todas \| \d+ \|.*\| ([\d.]+) \|$", md, re.M)
        if not mm:
            mismatch(f"fila {m}|todas en kn_calibration.md", None, "presente")
        same(f"obs/pred total {m} vs kn_calibration.md", round(total_ratio[m], 2), float(mm.group(1)), 0.0051)
    unseen = ~seen
    loc = f"{src_j}:summary"
    num("calib_lambda", kj["lambda"], f_fix(2), f"{src_j}:lambda")
    num("calib_n_queries", len(rows), f_int, f"{src_c}:filas")
    num("calib_n_seen", int(seen.sum()), f_int, f"{src_c}:obs_occ>=1")
    num("calib_n_unseen", int(unseen.sum()), f_int, f"{src_c}:obs_occ==0")
    for m in ("lap", "kn", "hier"):
        for sname, tag in (("todas", "all"), ("vistas", "seen")):
            s = kj["summary"][f"{m}|{sname}"]
            num(f"calib_{m}_slope_{tag}", s[0], f_fix(3), f"{loc}.{m}|{sname}[0]")
            num(f"calib_{m}_mae_{tag}", s[1], f_fix(3), f"{loc}.{m}|{sname}[1]")
            num(f"calib_{m}_bias_{tag}", s[2], f_fix(3), f"{loc}.{m}|{sname}[2]")
        num(f"calib_{m}_obs_pred", total_ratio[m], f_fix(2), f"{src_c}:sum(obs_occ)/sum(pred_occ_{m})")
        num(f"calib_{m}_unseen_pred_mean", float(pred[m][unseen].mean()), f_fix(3), f"{src_c}:mean(pred_occ_{m}|obs_occ==0)")
    return {**meta([src_j, src_c, src_m]), "lambda": kj["lambda"], "choice": kj["choice"],
            "stratum": "1750-1830", "n": 8, "design": "200 windows sampled uniformly, leave-both-composers-out",
            "models": ["lap", "kn", "hier"],
            "labels": {"lap": "Laplace (upper bound)", "kn": "Kneser–Ney", "hier": "Hierarchical"},
            "summary_fields": ["slope", "mae_log", "bias_log"],
            "summary_note": "metrics on log(x + 0.05): OLS slope of log obs on log pred, mean |log obs − log pred|, "
                            "mean (log obs − log pred); 'todas' = all windows, 'vistas' = windows seen in another composer",
            "summary": summ,
            "summary_named": {k: dict(zip(("slope", "mae_log", "bias_log"), v)) for k, v in summ.items()},
            "obs_pred_total": total_ratio,
            "bin_by": "pred_occ_kn", "bins_subset": "seen windows (obs_occ ≥ 1)", "bins": bins,
            "unseen": {"k": int(unseen.sum()), "obs": 0,
                       "pred_mean": {m: float(pred[m][unseen].mean()) for m in ("lap", "kn", "hier")}},
            "n_queries": len(rows)}


# ---------- λ(n) ----------
def build_lambda() -> dict:
    src, src_g = "results/lambda_by_n.csv", "results/lambda_by_n_grid.csv"
    rows, grid_rows = read_csv(src), read_csv(src_g)
    grid: dict[str, list] = {}
    for r in grid_rows:
        grid.setdefault(r["n"], []).append({"lambda": float(r["lam"]), "loglik": float(r["loglik"]),
                                            "slope": float(r["pendiente"]), "mae_log": float(r["MAE_log"]),
                                            "bias_log": float(r["sesgo_log"]), "obs_pred": float(r["obs_pred"])})
    by_n, srcs = [], [src, src_g]
    for r in rows:
        n = int(r["n"]); ls = float(r["lambda_star"])
        g = grid[r["n"]]
        best = max(g, key=lambda x: x["loglik"])
        same(f"λ* n={n}: lambda_by_n.csv vs argmax de la rejilla", ls, best["lambda"], 1e-9)
        same(f"loglik en λ* n={n}", round(best["loglik"], 4), float(r["loglik_por_ventana"]), 1e-4)
        js = f"results/kn_lambda_n{n}.json"
        if (ROOT / js).exists():
            kj = read_json(js)
            check_ids(kj.get("holdout_works_used", []), context=f"build_data:{js}.holdout_works_used")
            same(f"λ* n={n}: lambda_by_n.csv vs {js}", ls, float(kj["lambda"]), 1e-9)
            srcs.append(js)
        by_n.append({"n": n, "lambda_star": ls, "slope": float(r["pendiente"]), "mae_log": float(r["MAE_log"]),
                     "bias_log": float(r["sesgo_log"]), "obs_pred": float(r["obs_pred"]),
                     "loglik_per_window": float(r["loglik_por_ventana"]), "n_windows": int(r["n_ventanas_lambda"])})
        num(f"lambda_star_n{n}", ls, f_fix(2), f"{src}:n={n}.lambda_star")
        num(f"lambda_slope_n{n}", float(r["pendiente"]), f_fix(3), f"{src}:n={n}.pendiente")
        num(f"lambda_obs_pred_n{n}", float(r["obs_pred"]), f_fix(2), f"{src}:n={n}.obs_pred")
    num("lambda_n_windows_n8", next(b["n_windows"] for b in by_n if b["n"] == 8), f_int, f"{src}:n=8.n_ventanas_lambda")
    return {**meta(srcs), "method": "deleted interpolation on 20 % held-out works (seed 20260903), stratum 1750-1830",
            "by_n": by_n, "grid": grid}


# ---------- umbrales ----------
def build_thresholds() -> dict:
    src_j, src_c = "results/thresholds_n8.json", "results/thresholds_n8_windows.csv"
    tj = read_json(src_j)
    rows = read_csv(src_c)
    ids = [r["work_A"] for r in rows] + [r["work_B"] for r in rows]
    check_ids(ids, context="build_data:thresholds_n8_windows")
    check_ids([p[k] for p in tj["positives"] + tj["negatives"] for k in ("A", "B")], context="build_data:thresholds_n8.json")
    y = np.array([int(r["label"]) for r in rows])
    DF = np.array([float(r["DF"]) for r in rows]); E = np.array([float(r["E"]) for r in rows])
    neg, pos = y == 0, y == 1
    same("n positivos", int(pos.sum()), tj["n_instances"]["pos"]); same("n negativos", int(neg.sum()), tj["n_instances"]["neg"])
    t_df, t_e = tj["DF"]["threshold"], tj["E"]["threshold"]
    gate = DF <= t_df
    for name, rule in (("DF", DF <= t_df), ("E", E <= t_e), ("combined", gate & (E <= t_e))):
        same(f"FPR {name}", float(rule[neg].mean()), tj[name]["FPR"], 1e-12)
        same(f"sensibilidad {name}", float(rule[pos].mean()), tj[name]["sensitivity"], 1e-12)
    same("prevalencia", float(pos.mean()), tj["prevalence"], 1e-12)
    comb = np.where(gate, -np.log(E), -1e9)
    curves = {}
    for name, sc in (("DF", -DF), ("E", -np.log(E)), ("DF→E", comb)):
        fpr, tpr, prec, rec, auc, ap = roc(sc, y)
        same(f"AUC {name} recalculado vs thresholds_n8.json", auc, tj["curves"][name]["AUC"], 1e-12)
        same(f"AP {name} recalculado vs thresholds_n8.json", ap, tj["curves"][name]["AP"], 1e-12)
        curves[name] = {"AUC": auc, "AP": ap,
                        "roc": [[round(float(a), 6), round(float(b), 6)] for a, b in zip(fpr, tpr)],
                        "pr": [[round(float(a), 6), round(float(b), 6)] for a, b in zip(rec, prec)]}
    per_pair = {}
    for pid, d in tj["per_pair"].items():
        sel = np.array([r["pair"] == pid for r in rows])
        same(f"tipos compartidos {pid}", int(sel.sum()), d["shared_types"])
        per_pair[pid] = {k: d[k] for k in ("shared_types", "pass_DF", "pass_E", "pass_both")}
    # etiquetas legibles desde el catálogo (filas permitidas solamente)
    cat = {r["work_id"]: r for r in filter_catalog_rows(read_csv("corpus/works.csv"))}

    def label(w):
        r = cat.get(w)
        if r is None:
            mismatch(f"obra de los pares {w} no está en el catálogo permitido", None, w)
        return f"{r['composer']}, {r['title']}"

    pairs = {"positives": [{"id": p["id"], "A": label(p["A"]), "B": label(p["B"]), "basis": p["ref"].replace("cap.", "ch.")} for p in tj["positives"]],
             "negatives": [{"id": p["id"], "A": label(p["A"]), "B": label(p["B"])} for p in tj["negatives"]]}
    loc = src_j
    num("thresh_n", tj["n"], f_int, f"{loc}:n")
    num("thresh_lambda", tj["lambda"], f_fix(2), f"{loc}:lambda")
    num("thresh_n_pos", tj["n_instances"]["pos"], f_int, f"{loc}:n_instances.pos")
    num("thresh_n_neg", tj["n_instances"]["neg"], f_int, f"{loc}:n_instances.neg")
    num("thresh_n_pairs_pos", len(tj["positives"]), f_int, f"{loc}:positives")
    num("thresh_n_pairs_neg", len(tj["negatives"]), f_int, f"{loc}:negatives")
    num("thresh_t_df", t_df, f_sci(2), f"{loc}:DF.threshold")
    num("thresh_t_e", t_e, f_sci(2), f"{loc}:E.threshold")
    for name, tag in (("DF", "df"), ("E", "e"), ("combined", "comb")):
        num(f"thresh_fpr_{tag}", 100 * tj[name]["FPR"], f_pct(1), f"{loc}:{name}.FPR")
        num(f"thresh_sens_{tag}", 100 * tj[name]["sensitivity"], f_pct(1), f"{loc}:{name}.sensitivity")
    num("thresh_pos_pass_e", int(round(tj["E"]["sensitivity"] * tj["n_instances"]["pos"])), f_int, f"{loc}:E.sensitivity*n_instances.pos")
    num("thresh_pos_pass_df", int(round(tj["DF"]["sensitivity"] * tj["n_instances"]["pos"])), f_int, f"{loc}:DF.sensitivity*n_instances.pos")
    for name, tag in (("DF", "df"), ("E", "e"), ("DF→E", "dfe")):
        num(f"thresh_auc_{tag}", tj["curves"][name]["AUC"], f_fix(2), f"{loc}:curves.{name}.AUC")
        num(f"thresh_ap_{tag}", tj["curves"][name]["AP"], f_fix(2), f"{loc}:curves.{name}.AP")
    num("thresh_prevalence", tj["prevalence"], f_fix(2), f"{loc}:prevalence")
    return {**meta([src_j, src_c, "corpus/works.csv", "scripts/thresholds_n8.py:roc"]),
            "n": tj["n"], "lambda": tj["lambda"], "stratum": tj["stratum"], "prevalence": tj["prevalence"],
            "n_instances": tj["n_instances"], "pairs": pairs,
            "instance": "type of 8-note window of A that also occurs in B",
            "DF": {k: tj["DF"][k] for k in ("threshold", "FPR", "sensitivity")},
            "E": {k: tj["E"][k] for k in ("threshold", "FPR", "sensitivity")},
            "combined": {k: tj["combined"][k] for k in ("FPR", "sensitivity")},
            "rules": {"DF": "largest DF with FPR ≤ 5 % on negatives; significant presence if DF ≤ threshold",
                      "E": "5th percentile of E under the stratified null (negative pairs)",
                      "combined": "DF ≤ t_DF, then E ≤ t_E"},
            "per_pair": per_pair, "curves": curves}


# ---------- sensibilidad a cita literal (A3) ----------
def build_literal() -> dict:
    src = "results/literal_sensitivity_n8.json"
    if not (ROOT / src).exists():
        return {**meta([]), "status": "pending",
                "note": "Sensitivity to literal quotation has not been measured yet. It is a precondition of the "
                        "preregistered protocol (D-41, pending item 1)."}
    from literal_sensitivity_n8 import wilson  # misma fórmula que A3
    src_c = "results/literal_sensitivity_n8.csv"
    lj = read_json(src)
    tj = read_json("results/thresholds_n8.json")
    # guardia sobre todo identificador de obra/unidad que aparece en el JSON y en el CSV
    ids = [p[k] for p in lj["pairs"] for k in ("A", "B")] + list(lj.get("windows", {}))
    ids += [r.get(k, "") for r in lj.get("extract_logs", []) for k in ("work_id", "unit_id")]
    ids += list(lj["LS2"].get("pool", [])) + list(lj.get("vivaldi_check", {}).get("widx_B", {}))
    ids += list(lj.get("vivaldi_check", {}).get("A_in_tables", {}))
    check_ids(ids, context="build_data:literal_sensitivity_n8.json")
    rows = read_csv(src_c)
    check_ids([r["work_A"] for r in rows] + [r["work_B"] for r in rows], context="build_data:literal_sensitivity_n8.csv")
    same("t_DF literal vs thresholds_n8.json", lj["t_DF"], tj["DF"]["threshold"])
    same("t_E literal vs thresholds_n8.json", lj["t_E"], tj["E"]["threshold"])
    same("n literal", lj["n"], tj["n"]); same("λ literal", lj["lambda"], tj["lambda"])
    t_df, t_e = lj["t_DF"], lj["t_E"]

    def check_rate(what, d, k, n):
        same(f"{what} k", d["k"], k); same(f"{what} n", d["n"], n)
        same(f"{what} rate", d["rate"], k / n, 1e-12)
        lo, hi = wilson(k, n)
        same(f"{what} wilson lo", d["wilson95"][0], lo, 1e-12); same(f"{what} wilson hi", d["wilson95"][1], hi, 1e-12)

    def agg_rate(d):
        return {"k": d["k"], "n": d["n"], "rate": d["rate"], "ci95": d["wilson95"]}

    ls1 = {}
    for variant, vd in lj["LS1"].items():
        vrows = [r for r in rows if r["variant"] == variant]
        out = {}
        for scope, sel in [("global", vrows)] + [(p, [r for r in vrows if r["pair"] == p]) for p in vd["per_pair"]]:
            d = vd["global"] if scope == "global" else vd["per_pair"][scope]
            DF = np.array([float(r["DF"]) for r in sel]); E = np.array([float(r["E"]) for r in sel])
            nonu = np.array([r["uniform_rhythm"] == "0" for r in sel])
            for col, rule in (("pass_DF", DF <= t_df), ("pass_E", E <= t_e), ("pass_both", (DF <= t_df) & (E <= t_e))):
                same(f"LS1 {variant} {scope} columna {col} vs umbral", [int(r[col]) for r in sel], rule.astype(int).tolist())
            same(f"LS1 {variant} {scope} instancias", d["instances"], len(sel))
            check_rate(f"LS1 {variant} {scope} DF", d["DF"], int((DF <= t_df).sum()), len(sel))
            check_rate(f"LS1 {variant} {scope} E", d["E"], int((E <= t_e).sum()), len(sel))
            check_rate(f"LS1 {variant} {scope} combined", d["combined"], int(((DF <= t_df) & (E <= t_e)).sum()), len(sel))
            same(f"LS1 {variant} {scope} DF y ritmo no uniforme", d["pass_DF_nonuniform"], int(((DF <= t_df) & nonu).sum()))
            out[scope] = {"instances": d["instances"], "DF": agg_rate(d["DF"]), "E": agg_rate(d["E"]),
                          "combined": agg_rate(d["combined"]), "pass_DF_nonuniform": d["pass_DF_nonuniform"]}
        ls1[variant] = out
    L2 = lj["LS2"]
    ls2 = {}
    for variant, vd in L2["results"].items():
        ls2[variant] = {}
        for scope, byl in vd.items():
            ls2[variant][scope] = []
            for length, d in sorted(byl.items(), key=lambda kv: int(kv[0])):
                check_rate(f"LS2 {variant} {scope} {length}", d["power"], d["power"]["k"], d["power"]["n"])
                if scope == "all_pairs":
                    per = [vd[q][length]["power"] for q in vd if q != "all_pairs"]
                    same(f"LS2 {variant} all_pairs {length} n = suma de pares", d["power"]["n"], sum(x["n"] for x in per))
                    same(f"LS2 {variant} all_pairs {length} k = suma de pares", d["power"]["k"], sum(x["k"] for x in per))
                else:
                    same(f"LS2 {variant} {scope} {length} n_obs", d["power"]["n"], L2["n_obs"])
                if scope == "all_pairs":
                    ls2[variant][scope].append({"length_bars": int(length), "power": agg_rate(d["power"])})
                    continue
                same(f"LS2 {variant} {scope} {length} n_null", d["n_null"], L2["n_null"])
                same(f"LS2 {variant} {scope} {length} length_bars", d["length_bars"], int(length))
                ls2[variant][scope].append({"length_bars": d["length_bars"], "length_windows": d["length_windows"],
                                            "power": agg_rate(d["power"]), "obs_mean": d["obs_mean"],
                                            "null_mean": d["null_mean"], "null_q95": d["null_q95"]})
    cat = {r["work_id"]: r for r in filter_catalog_rows(read_csv("corpus/works.csv"))}

    def label(w):
        r = cat.get(w)
        return f"{r['composer']}, {r['title']}" if r else w

    pairs = [{"id": p["id"], "work": f"Vivaldi, RV {p['id'][1:]}", "A": label(p["A"]), "B": label(p["B"]),
              "A_source": "Le Cène print (original)", "B_source": "Anne Dawson's Book (keyboard arrangement)"}
             for p in lj["pairs"]]
    # numbers.json
    for variant, tag in (("default", "default"), ("noBeethoven", "nobeethoven")):
        g = ls1[variant]["global"]
        for rule, rt in (("DF", "df"), ("E", "e"), ("combined", "comb")):
            loc = f"{src}:LS1.{variant}.global.{rule}"
            num(f"literal_ls1_{tag}_{rt}", 100 * g[rule]["rate"], f_pct(1), loc + ".rate")
            num(f"literal_ls1_{tag}_{rt}_lo", 100 * g[rule]["ci95"][0], f_pct(1), loc + ".wilson95[0]")
            num(f"literal_ls1_{tag}_{rt}_hi", 100 * g[rule]["ci95"][1], f_pct(1), loc + ".wilson95[1]")
        num(f"literal_ls1_{tag}_instances", g["instances"], f_int, f"{src}:LS1.{variant}.global.instances")
        for pid in lj["LS1"][variant]["per_pair"]:
            d = ls1[variant][pid]["DF"]
            num(f"literal_ls1_{tag}_df_{pid.lower()}", 100 * d["rate"], f_pct(1), f"{src}:LS1.{variant}.per_pair.{pid}.DF.rate")
        for r in ls2[variant].get("all_pairs", []):
            loc = f"{src}:LS2.results.{variant}.all_pairs.{r['length_bars']}.power"
            num(f"literal_ls2_{tag}_power_{r['length_bars']}bars", 100 * r["power"]["rate"], f_pct(1), loc + ".rate")
            num(f"literal_ls2_{tag}_power_{r['length_bars']}bars_lo", 100 * r["power"]["ci95"][0], f_pct(1), loc + ".wilson95[0]")
    num("literal_n_pairs", len(lj["pairs"]), f_int, f"{src}:pairs")
    num("literal_ls2_n_obs", L2["n_obs"], f_int, f"{src}:LS2.n_obs")
    num("literal_ls2_n_null", L2["n_null"], f_int, f"{src}:LS2.n_null")
    num("literal_ls2_alpha", L2["alpha"], f_fix(3), f"{src}:LS2.alpha")
    num("literal_ls2_pool_works", L2["pool_size_used"], f_int, f"{src}:LS2.pool_size_used")
    return {**meta([src, src_c, "results/thresholds_n8.json", "corpus/works.csv",
                    "scripts/literal_sensitivity_n8.py:wilson"]),
            "status": "measured", "n": lj["n"], "lambda": lj["lambda"], "stratum": lj["stratum"],
            "t_DF": t_df, "t_E": t_e, "pairs": pairs,
            "variants": {"default": "background of the 1750–1830 stratum excluding the composers of A and B",
                         "noBeethoven": "same background with Beethoven also removed (the background of the target case)"},
            "LS1": {"description": "share of 8-note window types of the original (A) present in the literal "
                                   "arrangement (B) that pass the frozen thresholds; Wilson 95 % intervals",
                    "results": ls1},
            "LS2": {"description": "power of the fragment test: share of 200 contiguous fragments of A whose count of "
                                   f"types in B with DF ≤ t_DF has p ≤ {L2['alpha']} against {L2['n_null']} null "
                                   "fragments of the same length from other composers' string music before 1750",
                    "n_obs": L2["n_obs"], "n_null": L2["n_null"], "alpha": L2["alpha"], "seed": L2["seed"],
                    "pool_works": L2["pool_size_used"], "results": ls2},
            "caveats_en": [
                "Upper bound for literal quotation with a change of medium: keyboard arrangements of pre-1750 string "
                "concertos, against thresholds calibrated on string quartets of 1750–1830.",
                "Vivaldi has no works in the 1750–1830 stratum, so the composer term of the hierarchical background is "
                "empty and the background reduces to the stratum model.",
                "Instances (shared types) are correlated within each pair; the Wilson intervals treat them as "
                "independent and are optimistic."],
            "note": "Exploratory measurement of a protocol precondition; formal adoption is part of the proposed "
                    "amendment D-43. It says nothing about the confirmatory case."}


# ---------- estado del preregistro ----------
def build_status() -> dict:
    src_d, src_p = "docs/DECISIONES.md", "decisions/D-41_preregistro.md"
    dec = (ROOT / src_d).read_text(encoding="utf-8")
    m = re.search(r"Commit congelado D-41:\s*`([0-9a-f]{40})`", dec)
    if not m:
        mismatch("hash congelado D-41 en docs/DECISIONES.md", None, "presente")
    frozen = m.group(1)
    pre = (ROOT / src_p).read_text(encoding="utf-8")
    if "NO se ha ejecutado" not in pre:
        mismatch("estado 'no ejecutado' en el preregistro", None, "NO se ha ejecutado")
    tests = re.search(r"La suite `tests/` pasa en ese commit \((\d+) de (\d+)\)", dec)
    literal_done = (ROOT / "results/literal_sensitivity_n8.json").exists()
    return {**meta([src_d, src_p]),
            "preregistration": {"id": "D-41", "file": src_p, "frozen_commit": frozen, "frozen_commit_short": frozen[:7],
                                "frozen_date": "2026-09-23", "registered": "2026-09-21"},
            "confirmatory_case": {
                "hypothesis": "Beethoven's Fifth Symphony (op. 67) shares with Cherubini's pre-1808 works more "
                              "low-documentary-frequency 8-note windows (DF ≤ t_DF) than the hierarchical background "
                              "of the 1750–1830 stratum (without Beethoven or Cherubini) predicts.",
                "executed": False,
                "note": "Not run. No window of op. 67 or of any Cherubini work has been read, compared or computed."},
            "frozen_parameters": {"n": 8, "lambda": 0.45, "stratum": "1750-1830", "n_null_pairs": 1000,
                                  "seed": 20260903, "target_fpr": 0.05, "secondary_n": [6, 10]},
            "pending": [
                {"item": "Measure sensitivity to literal quotation (arrangements, fugue subjects) with encoded positives",
                 "state": ("in progress: first measurement on four literal keyboard arrangements (Anne Dawson's Book "
                           "against the Le Cène print); formal adoption as a control is part of D-43")
                          if literal_done else "open"},
                {"item": "Amendment D-43 to the protocol: null built from fragments of equal length and literal-quotation "
                         "controls (Dawson / Le Cène)",
                 "state": "open: proposed, pending the author's approval; to be frozen before the case is run"},
                {"item": "Register the preregistration on OSF",
                 "state": "open: not registered; plan is a single registration of D-41 + D-43 after D-43 is approved "
                          "and before the Cherubini works are transcribed"},
                {"item": "Confirm the list of Cherubini works composed before 1808 present in the corpus "
                         "(without looking at their windows)",
                 "state": "open: none is encoded; the two works of the hypothesis (1794) need manual transcription"},
                {"item": "Run the tests/ suite at the frozen commit",
                 "state": f"done ({tests.group(1)} of {tests.group(2)})" if tests else "unknown"},
            ]}


def main():
    br = read_json("results/base_rate.json")
    if br.get("include_target") is not False:
        mismatch("base_rate.json include_target", br.get("include_target"), False)
    store: dict[str, dict] = {}
    write("corpus", build_corpus(br), store)
    write("base_rates", build_base_rates(br), store)
    write("observed_null", build_null(br), store)
    write("uniqueness", build_uniqueness(br), store)
    write("calibration", build_calibration(), store)
    write("lambda", build_lambda(), store)
    write("thresholds", build_thresholds(), store)
    write("literal", build_literal(), store)
    st = build_status()
    write("status", st, store)
    num("status_frozen_commit_short", st["preregistration"]["frozen_commit_short"], str, "docs/DECISIONES.md:D-41")
    write("numbers", {**meta(sorted(NUM_SOURCES)), "numbers": dict(sorted(NUMBERS.items()))}, store)
    # todo cuadra: se escribe
    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in store.items():
        (OUT / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n",
                                          encoding="utf-8")
    print(f"OK: {len(store)} archivos en {OUT.relative_to(ROOT)}; {len(NUMBERS)} claves en numbers.json")


if __name__ == "__main__":
    main()
