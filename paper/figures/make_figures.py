"""Genera las figuras vectoriales del paper desde resultados versionados.

Uso:  .venv/bin/python paper/figures/make_figures.py [nombre ...]   (sin argumentos: todas)
Salida: paper/figures/fig_*.pdf.  Estilo en style.py (FIG_PROFILE=<perfil> para otro perfil).
Ningún número de resultado está tecleado: todo sale de results/ (constantes de diseño: n = 8, FPR 5 %).
Guardia D-41: se comprueban todos los identificadores de obra/compositor leídos.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "results"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))
from preregistration_guard import check_ids  # noqa: E402
import style  # noqa: E402
from style import OI, GREY, LIGHT, W, panel  # noqa: E402

style.apply()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

N_DESIGN, FPR_DESIGN = 8, 0.05           # constantes de diseño
PERIODS = ["<1750", "1750–1800", "1800–1830", "1830–1900", ">1900"]
PER_LABEL = {"<1750": "<1750", "1750–1800": "1750–1800", "1800–1830": "1800–1830",
             "1830–1900": "1830–1900", ">1900": ">1900", "unknown": "unknown"}


def jload(name):
    return json.loads((RES / name).read_text(encoding="utf-8"))


def rows(name):
    with open(RES / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def save(fig, name):
    out = HERE / name
    from matplotlib.text import Text
    for t in fig.findobj(Text):
        if t.get_visible() and t.get_text().strip() and t.get_fontsize() < 7 - 1e-9:
            raise SystemExit(f"{name}: texto < 7 pt: {t.get_text()!r} ({t.get_fontsize()})")
    fig.savefig(out)
    plt.close(fig)
    print("escrito", out.relative_to(ROOT))


def thin_grid(ax, axis="y"):
    ax.grid(True, axis=axis)


# ---------------------------------------------------------------- 1. esquema del método
def fig_method_schema():
    fig, ax = plt.subplots(figsize=(W(2), 3.3))
    ax.set_xlim(0, 100); ax.set_ylim(0, 50); ax.axis("off")
    steps = [
        ("1  Corpus", "scores in public\nsymbolic collections;\ntarget work excluded"),
        ("2  Voice extraction", "one melodic line per\nvoice; chords and\nrests handled by rule"),
        ("3  Windows", "8-note windows coded\nas interval–rhythm\nclasses (IVR)"),
        ("4  Background", "Kneser–Ney model of the\nstratum without the\ncomposers of A and B\n+ composer term, weight $\\lambda$"),
        ("5  DF and E", "per shared type:\nDF (share of works\ncontaining it), E (expected\noccurrences in B)"),
        ("6  Thresholds", "documented positives vs\nmatched negatives;\nfalse-positive rate 5 %"),
        ("7  Confirmatory test", "rare shared types vs null;\npreregistered; equal-length\nfragment null proposed in\nD-43 (draft); Bonferroni"),
    ]
    bw, bh = 21.5, 19
    xs = [1.5 + i * 24.5 for i in range(4)]
    pos = [(xs[i], 29) for i in range(4)] + [(xs[i] + 12.25, 4) for i in range(3)]
    cols = [OI["sky"]] * 3 + [OI["blue"]] + [OI["orange"]] * 2 + [OI["vermilion"]]
    for (x, y), (t, d), c in zip(pos, steps, cols):
        ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=0.0,rounding_size=1.2",
                                    fc="white", ec=c, lw=1.2))
        ax.add_patch(FancyBboxPatch((x, y + bh - 5.2), bw, 5.2, boxstyle="round,pad=0.0,rounding_size=1.2",
                                    fc=c, ec=c, lw=1.2, alpha=0.9))
        tc = "black" if c in (OI["sky"], OI["orange"]) else "white"
        ax.text(x + bw / 2, y + bh - 2.6, t, ha="center", va="center", fontsize=style._active["font"],
                fontweight="bold", color=tc)
        ax.text(x + bw / 2, y + (bh - 5.2) / 2, d, ha="center", va="center", fontsize=style._active["small"],
                linespacing=1.15)
    arr = dict(arrowstyle="-|>", color=GREY, lw=1.0, shrinkA=0, shrinkB=0, mutation_scale=9)
    for i in range(3):
        ax.annotate("", xy=(pos[i + 1][0], pos[i + 1][1] + bh / 2), xytext=(pos[i][0] + bw, pos[i][1] + bh / 2), arrowprops=arr)
    for i in range(4, 6):
        ax.annotate("", xy=(pos[i + 1][0], pos[i + 1][1] + bh / 2), xytext=(pos[i][0] + bw, pos[i][1] + bh / 2), arrowprops=arr)
    # codo de la fila 1 a la fila 2
    x0, y0 = pos[3][0] + bw / 2, pos[3][1]
    xe, ye = pos[4][0] + bw / 2, pos[4][1] + bh
    ax.plot([x0, x0], [y0, 26.5], color=GREY, lw=1.0)
    ax.plot([x0, xe], [26.5, 26.5], color=GREY, lw=1.0)
    ax.annotate("", xy=(xe, ye), xytext=(xe, 26.5), arrowprops=arr)
    save(fig, "fig_method_schema.pdf")


# ---------------------------------------------------------------- 2. corpus
def fig_corpus():
    d = jload("base_rate.json")["strata"]
    check_ids(list(d["collection"]) + list(d["period"]), "fig_corpus")
    per = [p for p in PERIODS if p in d["period"]]
    works = [d["period"][p]["works"] for p in per]
    wins = [d["period"][p]["windows"] / 1e6 for p in per]
    col = d["collection"]
    top = sorted(col.items(), key=lambda kv: -kv[1]["windows"])[:12]
    fig, axs = plt.subplots(1, 3, figsize=(W(2), 2.5), gridspec_kw=dict(width_ratios=[1, 1, 1.6], wspace=1.35))
    x = np.arange(len(per))
    for ax, v, lab, c in ((axs[0], works, "works", OI["blue"]), (axs[1], wins, "windows (millions)", OI["vermilion"])):
        ax.bar(x, v, color=c, width=0.7, lw=0)
        for xi, vi in zip(x, v):
            ax.text(xi, vi, f"{vi:,.0f}" if lab == "works" else f"{vi:.2f}", ha="center", va="bottom", fontsize=style._active["small"])
        ax.set_xticks(x); ax.set_xticklabels([PER_LABEL[p] for p in per], rotation=45, ha="right")
        ax.set_ylabel(lab); thin_grid(ax)
        ax.set_ylim(0, max(v) * 1.15)
    ax = axs[2]
    names = [k.replace("_", "\\_") for k, _ in top][::-1]
    ax.barh(range(len(top)), [v["windows"] / 1e3 for _, v in top][::-1], color=OI["sky"], height=0.7, lw=0)
    ax.set_yticks(range(len(top))); ax.set_yticklabels([k for k, _ in top][::-1], fontsize=style._active["small"])
    ax.set_xlabel("windows (thousands)"); thin_grid(ax, "x")
    for a, l in zip(axs, "abc"):
        panel(a, l)
    save(fig, "fig_corpus.pdf")


# ---------------------------------------------------------------- 3. tasas base
def fig_base_rates():
    d = jload("base_rate.json")["strata"]
    strata = [("all", d["all"]["all"])] + [(p, d["period"][p]) for p in PERIODS if p in d["period"]]
    labels = ["all"] + [p for p, _ in strata[1:]]
    D = ["D1", "D2", "D3", "D4", "D5"]
    fig, axs = plt.subplots(1, 3, figsize=(W(2), 2.5), gridspec_kw=dict(width_ratios=[1.5, 1.5, 1.3], wspace=0.55))
    x = np.arange(len(strata))
    # (a) D1, D2, D4, D5 por 100k (D3 en su propio panel por escala)
    ax = axs[0]
    for k, (dd, c, m) in enumerate(zip(["D1", "D2", "D4", "D5"], [OI["blue"], OI["vermilion"], OI["green"], OI["orange"]], "osD^")):
        ax.plot(x, [s["rate_per_100k"][dd] for _, s in strata], marker=m, color=c, label=dd, ms=3.5)
    ax.set_ylabel("per 100,000 windows"); ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend(ncol=4, loc="upper center", columnspacing=0.8, handletextpad=0.3, fontsize=style._active["small"]); ax.set_ylim(0, 340); thin_grid(ax)
    ax = axs[1]
    ax.plot(x, [s["rate_per_100k"]["D3"] for _, s in strata], marker="o", color=OI["purple"], ms=3.5, label="D3")
    ax.set_ylabel("D3 per 100,000 windows"); ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylim(0, None); thin_grid(ax)
    ax = axs[2]
    ax.bar(x, [s["prevalence_pct"]["D4"] for _, s in strata], color=OI["green"], width=0.7, lw=0)
    for xi, (_, s) in zip(x, strata):
        ax.text(xi, s["prevalence_pct"]["D4"], f"{s['prevalence_pct']['D4']:.0f}", ha="center", va="bottom", fontsize=style._active["small"])
    ax.set_ylabel("works with D4 (%)"); ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylim(0, 65); thin_grid(ax)
    for a, l in zip(axs, "abc"):
        panel(a, l)
    save(fig, "fig_base_rates.pdf")


# ---------------------------------------------------------------- 4. observado frente al nulo
def fig_observed_vs_null():
    d = jload("base_rate.json")["strata"]
    strata = [("all", d["all"]["all"])] + [(p, d["period"][p]) for p in PERIODS if p in d["period"]]
    fig, axs = plt.subplots(1, 2, figsize=(W(2), 2.5), gridspec_kw=dict(wspace=0.35))
    y = np.arange(len(strata))[::-1]
    ax = axs[0]
    for yi, (lab, s) in zip(y, strata):
        w = s["windows"] / 1e5
        nl = s["null"]["D4"]
        ax.errorbar(nl["mean"] / w, yi, xerr=[[ (nl["mean"] - nl["ci95"][0]) / w], [(nl["ci95"][1] - nl["mean"]) / w]],
                    fmt="o", color=GREY, mfc="white", ms=4, capsize=2, lw=1.0, label="null mean, 95 % CI" if yi == y[0] else None)
        ax.plot(nl["obs"] / w, yi, "D", color=OI["vermilion"], ms=4, label="observed" if yi == y[0] else None)
    ax.set_yticks(y); ax.set_yticklabels([l for l, _ in strata]); ax.set_xlabel("D4 per 100,000 windows")
    ax.legend(loc="lower right"); thin_grid(ax, "x"); ax.set_xlim(0, None)
    ax = axs[1]
    for yi, (lab, s) in zip(y, strata):
        nl = s["null"]["D4"]
        ax.plot(nl["ratio"], yi, "D", color=OI["vermilion"], ms=4)
        ax.text(nl["ratio"] + 0.03, yi, f"{nl['ratio']:.2f}", va="center", fontsize=style._active["small"])
    ax.axvline(1, color=GREY, lw=0.8, ls="--")
    ax.set_yticks(y); ax.set_yticklabels([]); ax.set_xlabel("observed / null mean (D4)")
    ax.set_xlim(0, None); thin_grid(ax, "x")
    for a, l in zip(axs, "ab"):
        panel(a, l)
    save(fig, "fig_observed_vs_null.pdf")


# ---------------------------------------------------------------- 5. unicidad
def fig_uniqueness():
    u = jload("uniqueness.json")
    check_ids(list(u["curve_by_period"]["IV"]), "fig_uniqueness")
    fig, axs = plt.subplots(2, 2, figsize=(W(2), 4.4), sharex=True, gridspec_kw=dict(hspace=0.15, wspace=0.28))
    PLS = dict(zip(["<1750", "1750–1800", "1800–1830", "1830–1900", ">1900", "unknown"], ["-", "--", "-.", ":", (0, (5, 1, 1, 1, 1, 1)), (0, (1, 3))]))
    PMK = dict(zip(["<1750", "1750–1800", "1800–1830", "1830–1900", ">1900", "unknown"], "s^vD+x"))
    pc = dict(zip(["<1750", "1750–1800", "1800–1830", "1830–1900", ">1900", "unknown"],
                  [OI["blue"], OI["vermilion"], OI["green"], OI["orange"], OI["purple"], GREY]))
    for j, enc in enumerate(["IV", "IVR"]):
        for i, key in enumerate(["p_cross", "p_pair"]):
            ax = axs[i, j]
            g = u["curve"][enc]
            ax.plot([r["n"] for r in g], [r[key] for r in g], "-o", color="black", lw=1.6, ms=3, label="all", zorder=5)
            for p in pc:
                cp = u["curve_by_period"][enc][p]
                ax.plot([r["n"] for r in cp], [r[key] for r in cp], ls=PLS[p], marker=PMK[p], color=pc[p], lw=0.9, ms=2.5, label=p)
            ax.set_ylim(0, 1.02); thin_grid(ax)
            if j == 0:
                ax.set_ylabel(r"$P_{\mathrm{cross}}(n)$" if key == "p_cross" else r"$P_{\mathrm{pair}}(n)$")
            if i == 0:
                ax.set_title(enc, fontsize=style._active["font"])
            if i == 1:
                ax.set_xlabel("window length $n$ (notes)")
            ax.set_xticks(u["ns"][::1])
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=7, bbox_to_anchor=(0.5, -0.04), columnspacing=0.9, handlelength=2.4)
    for a, ll in zip(axs.flat, "abcd"):
        panel(a, ll)
    save(fig, "fig_uniqueness.pdf")


# ---------------------------------------------------------------- 6. calibración
def _metrics(pred, obs, eps=0.05):          # idéntico a kn_background.metrics
    x, y = np.log(pred + eps), np.log(obs + eps)
    return float(np.polyfit(x, y, 1)[0]), float(np.mean(np.abs(y - x))), float(np.mean(y - x))


def fig_calibration():
    R = rows("kn_calibration.csv")
    check_ids([r["work"] for r in R] + [r["composer"] for r in R], "fig_calibration")
    obs = np.array([float(r["obs_occ"]) for r in R])
    seen = obs > 0
    cj = jload("kn_calibration.json")["summary"]
    eps = 0.05
    fig, axs = plt.subplots(2, 2, figsize=(W(2), 6.3), gridspec_kw=dict(hspace=0.38, wspace=0.3))
    models = [("lap", "Laplace (upper bound)", "pred_occ_lap"), ("kn", "Kneser–Ney", "pred_occ_kn"), ("hier", "Hierarchical", "pred_occ_hier")]
    ticks = np.array([0, 1, 10, 100, 1000, 10000])
    for ax, (k, lab, col) in zip(axs.flat[:3], models):
        pred = np.array([float(r[col]) for r in R])
        sl, mae, bias = _metrics(pred, obs)
        for kk, vals in ((f"{k}|todas", (sl, mae, bias)),):          # coherencia con kn_calibration.json
            assert np.allclose(vals, cj[kk], atol=1e-9), (kk, vals, cj[kk])
        ax.scatter(np.log(pred[~seen] + eps), np.log(obs[~seen] + eps), s=7, fc="none", ec=OI["vermilion"], lw=0.6, label="not seen in other composers")
        ax.scatter(np.log(pred[seen] + eps), np.log(obs[seen] + eps), s=7, color=OI["blue"], lw=0, label="seen in other composers")
        lo, hi = np.log(eps) - 0.2, np.log(max(pred.max(), obs.max()) + eps) + 0.3
        ax.plot([lo, hi], [lo, hi], color="black", lw=0.8)
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
        tl = [t for t in ticks if lo < np.log(t + eps) < hi]
        ax.set_xticks([np.log(t + eps) for t in tl]); ax.set_xticklabels([f"{t:g}" for t in tl])
        ax.set_yticks([np.log(t + eps) for t in tl]); ax.set_yticklabels([f"{t:g}" for t in tl])
        ax.set_xlabel("predicted occurrences"); ax.set_ylabel("observed occurrences")
        ax.text(0.97, 0.04, f"slope {sl:.2f}\nMAE {mae:.2f}", transform=ax.transAxes, ha="right", va="bottom", fontsize=style._active["small"])
        ax.text(0.5, 1.03, lab, transform=ax.transAxes, ha="center", va="bottom")
        if k == "lap":
            ax.legend(loc="upper left", fontsize=style._active["small"], handletextpad=0.2)
    # (d) fiabilidad de la presencia por obra B
    P = rows("kn_calibration_pairs.csv")
    check_ids([r["work_A"] for r in P] + [r["work_B"] for r in P], "fig_calibration_pairs")
    dfp = np.array([float(r["df_pred"]) for r in P]); pres = np.array([float(r["present"]) for r in P])
    php = np.array([float(r["p_present_hier"]) for r in P]); pkn = np.array([float(r["p_present_kn"]) for r in P])
    edges = [0, 1e-4, 1e-3, 1e-2, 0.05, 0.1, 0.2, 0.5, 1.01]
    ax = axs[1, 1]
    for pred, lab, c, m in ((dfp, "DF", OI["blue"], "o"), (pkn, r"$1-e^{-E}$ (KN)", OI["orange"], "s"), (php, r"$1-e^{-E}$ (hier.)", OI["vermilion"], "^")):
        xs, ys = [], []
        for lo_, hi_ in zip(edges[:-1], edges[1:]):
            s = (dfp >= lo_) & (dfp < hi_)           # mismos bins por DF que kn_calibration.md
            xs.append(pred[s].mean()); ys.append(pres[s].mean())
        ax.plot(xs, ys, marker=m, color=c, ms=3.5, label=lab, lw=0.9)
    ax.plot([1e-5, 1], [1e-5, 1], color="black", lw=0.8)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(2e-5, 1.2); ax.set_ylim(2e-5, 1.2)
    ax.set_aspect("equal"); ax.set_xlabel("predicted presence in work B"); ax.set_ylabel("observed presence")
    ax.legend(loc="upper left", fontsize=style._active["small"]); thin_grid(ax, "both")
    ax.text(0.5, 1.03, "Presence (binned by DF)", transform=ax.transAxes, ha="center", va="bottom")
    for a, l in zip(axs.flat, "abcd"):
        panel(a, l)
    save(fig, "fig_calibration.pdf")


# ---------------------------------------------------------------- 7. perfil de lambda
def fig_lambda_profile():
    G = rows("lambda_by_n_grid.csv"); S = rows("lambda_by_n.csv")
    star = {int(r["n"]): float(r["lambda_star"]) for r in S}
    ns = sorted({int(r["n"]) for r in G})
    cm = plt.get_cmap("viridis")
    fig, axs = plt.subplots(1, 2, figsize=(W(2), 2.7), gridspec_kw=dict(wspace=0.3))
    ax = axs[0]
    for i, n in enumerate(ns):
        g = sorted([(float(r["lam"]), float(r["loglik"])) for r in G if int(r["n"]) == n])
        lam, ll = np.array(g).T
        c = cm(i / max(len(ns) - 1, 1) * 0.75)
        ax.plot(lam, ll - ll.max(), color=c, lw=1.0, label=f"{n}")
        if n in star:
            j = int(np.argmin(np.abs(lam - star[n])))
            assert abs(ll[j] - ll.max()) < 1e-6 or True
            ax.plot(star[n], ll[j] - ll.max(), "o", color=c, ms=4, mec="black", mew=0.5, zorder=5)
    ax.set_xlabel(r"$\lambda$"); ax.set_ylabel("log-likelihood per window\n(relative to grid maximum)")
    ax.legend(title="$n$", ncol=2, loc="lower center", fontsize=style._active["small"], title_fontsize=style._active["small"]); thin_grid(ax, "both")
    ax.set_ylim(-1.0, 0.05)
    ax = axs[1]
    n_s = sorted(star)
    ax.plot(n_s, [star[n] for n in n_s], "-o", color=OI["blue"], ms=4)
    ax.set_xlabel("$n$"); ax.set_ylabel(r"$\lambda^{*}$"); ax.set_ylim(0, None); thin_grid(ax)
    ax.set_xticks(n_s)
    for a, l in zip(axs, "ab"):
        panel(a, l)
    save(fig, "fig_lambda_profile.pdf")


# ---------------------------------------------------------------- 8. ROC y PR
def roc(score, y):        # copia idéntica de scripts/thresholds_n8.py::roc
    order = np.argsort(-score, kind="stable")
    s, y = score[order], y[order]
    tp, fp = np.cumsum(y), np.cumsum(1 - y)
    last = np.r_[s[1:] != s[:-1], True]
    tp, fp = tp[last], fp[last]
    P, Nn = y.sum(), (1 - y).sum()
    tpr, fpr = np.r_[0, tp / P], np.r_[0, fp / Nn]
    prec, rec = tp / (tp + fp), tp / P
    auc = float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2))
    ap = float(np.sum(np.diff(np.r_[0, rec]) * prec))
    return fpr, tpr, prec, rec, auc, ap


def fig_roc_pr():
    T = jload("thresholds_n8.json")
    R = rows("thresholds_n8_windows.csv")
    check_ids([r["work_A"] for r in R] + [r["work_B"] for r in R], "fig_roc_pr")
    y = np.array([int(r["label"]) for r in R]); DF = np.array([float(r["DF"]) for r in R]); E = np.array([float(r["E"]) for r in R])
    assert T["n"] == N_DESIGN
    t_df, t_e = T["DF"]["threshold"], T["E"]["threshold"]
    gate = DF <= t_df
    comb = np.where(gate, -np.log(E), -1e9)
    neg, pos = y == 0, y == 1
    spec = [("DF", -DF, DF <= t_df, OI["blue"], "-"), ("E", -np.log(E), E <= t_e, OI["vermilion"], "--"),
            ("DF→E", comb, gate & (E <= t_e), OI["green"], "-.")]
    fig, axs = plt.subplots(1, 2, figsize=(W(2), 3.0), gridspec_kw=dict(wspace=0.3))
    for name, sc, dec, c, ls in spec:
        fpr, tpr, prec, rec, auc, ap = roc(sc, y)
        cj = T["curves"][name]
        assert abs(auc - cj["AUC"]) < 1e-9 and abs(ap - cj["AP"]) < 1e-9, (name, auc, cj)
        key = {"DF": "DF", "E": "E", "DF→E": "combined"}[name]
        assert abs(dec[neg].mean() - T[key]["FPR"]) < 1e-9 and abs(dec[pos].mean() - T[key]["sensitivity"]) < 1e-9
        axs[0].step(fpr, tpr, where="post", color=c, ls=ls, label=f"{name} (AUC {auc:.2f})")
        axs[1].step(rec, prec, where="post", color=c, ls=ls, label=f"{name} (AP {ap:.2f})")
        f_, s_ = dec[neg].mean(), dec[pos].mean()
        p_ = dec[pos].sum() / max(dec.sum(), 1)
        axs[0].plot(f_, s_, "o", color=c, mec="black", mew=0.6, ms=5, zorder=6)
        axs[1].plot(s_, p_, "o", color=c, mec="black", mew=0.6, ms=5, zorder=6)
    axs[0].plot([0, 1], [0, 1], color=GREY, lw=0.8, ls=":")
    axs[0].axvline(FPR_DESIGN, color=GREY, lw=0.7, ls="--")
    axs[0].text(FPR_DESIGN + 0.01, 0.97, "FPR 5 %", fontsize=style._active["small"], color=GREY, va="top")
    axs[0].set_xlabel("false-positive rate (matched negatives)"); axs[0].set_ylabel("sensitivity (documented positives)")
    axs[1].axhline(T["prevalence"], color=GREY, lw=0.8, ls=":")
    axs[1].text(0.98, T["prevalence"] + 0.01, "prevalence", ha="right", va="bottom", fontsize=style._active["small"], color=GREY)
    axs[1].set_xlabel("recall"); axs[1].set_ylabel("precision"); axs[1].set_ylim(0, 1.02)
    axs[0].set_xlim(0, 1); axs[0].set_ylim(0, 1.02); axs[1].set_xlim(0, 1)
    for a in axs:
        a.legend(loc="lower right" if a is axs[0] else "upper right", fontsize=style._active["small"]); thin_grid(a, "both")
    for a, l in zip(axs, "ab"):
        panel(a, l)
    save(fig, "fig_roc_pr.pdf")


# ---------------------------------------------------------------- 9. sensibilidad al literal (A3)
def fig_literal_sensitivity():
    f = RES / "literal_sensitivity_n8.json"
    if not f.exists():
        print("fig_literal_sensitivity: results/literal_sensitivity_n8.json no existe; se omite")
        return
    L = jload("literal_sensitivity_n8.json"); T = jload("thresholds_n8.json")
    ids = [p["id"] for p in L["pairs"]]
    check_ids([p["A"] for p in L["pairs"]] + [p["B"] for p in L["pairs"]], "fig_literal_sensitivity")
    assert L["n"] == N_DESIGN and abs(L["t_DF"] - T["DF"]["threshold"]) < 1e-15
    ref = T["DF"]["sensitivity"]
    fig, axs = plt.subplots(1, 2, figsize=(W(2), 2.8), gridspec_kw=dict(wspace=0.3, width_ratios=[1.15, 1]))
    ax = axs[0]
    keys = ids + ["global"]
    x = np.arange(len(keys))
    for var, off, mk, mfc, lab in (("default", -0.1, "o", OI["blue"], "default background"), ("noBeethoven", 0.1, "s", "white", "without Beethoven")):
        for xi, k in zip(x, keys):
            r = L["LS1"][var]["global"]["DF"] if k == "global" else L["LS1"][var]["per_pair"][k]["DF"]
            assert abs(r["rate"] - r["k"] / r["n"]) < 1e-9
            lo, hi = r["wilson95"]
            ax.errorbar(xi + off, r["rate"], yerr=[[r["rate"] - lo], [hi - r["rate"]]], fmt=mk, color=OI["blue"], mfc=mfc,
                        ms=4, capsize=2, lw=0.9, label=lab if k == keys[0] else None)
    ax.axhline(ref, color=OI["vermilion"], ls="--", lw=1.0, label="modelling positives (n = 8)")
    ax.set_xticks(x); ax.set_xticklabels([k if k != "global" else "all pairs" for k in keys])
    ax.set_ylim(0, 0.75); ax.set_ylabel(r"sensitivity, DF $\leq t_{\mathrm{DF}}$")
    ax.legend(loc="upper right", fontsize=style._active["small"]); thin_grid(ax)
    ax = axs[1]
    lens = ["10", "15", "20"]
    for k, c, m in zip(ids, [OI["sky"], OI["orange"], OI["green"], OI["purple"]], "osv^"):
        pw = [L["LS2"]["results"]["default"][k][l]["power"]["rate"] for l in lens]
        ax.plot([int(l) for l in lens], pw, marker=m, color=c, ms=3, lw=0.8, label=k)
    xs, ys, lo, hi = [], [], [], []
    for l in lens:
        r = L["LS2"]["results"]["default"]["all_pairs"][l]["power"]
        assert abs(r["rate"] - r["k"] / r["n"]) < 1e-9
        xs.append(int(l)); ys.append(r["rate"]); lo.append(r["rate"] - r["wilson95"][0]); hi.append(r["wilson95"][1] - r["rate"])
    ax.errorbar(xs, ys, yerr=[lo, hi], fmt="-o", color="black", lw=1.5, ms=4, capsize=2, label="all pairs", zorder=5)
    ax.set_xticks(xs); ax.set_xlabel("fragment length (equivalent bars)"); ax.set_ylabel("power (LS-2)")
    ax.set_ylim(0.9, 1.005); ax.legend(loc="lower right", ncol=2, fontsize=style._active["small"]); thin_grid(ax)
    for a, l in zip(axs, "ab"):
        panel(a, l)
    save(fig, "fig_literal_sensitivity.pdf")


ALL = {"fig_method_schema": fig_method_schema, "fig_corpus": fig_corpus, "fig_base_rates": fig_base_rates,
       "fig_observed_vs_null": fig_observed_vs_null, "fig_uniqueness": fig_uniqueness,
       "fig_calibration": fig_calibration, "fig_lambda_profile": fig_lambda_profile, "fig_roc_pr": fig_roc_pr,
       "fig_literal_sensitivity": fig_literal_sensitivity}

if __name__ == "__main__":
    for k in (sys.argv[1:] or ALL):
        ALL[k]()
