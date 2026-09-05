"""Figuras de Fase 1 (PNG, matplotlib) a partir de results/base_rate.json y results/uniqueness.json.

  fig/base_rate_strata.png   tasa base anidada D1–D5 por estrato (periodo y colección)
  fig/observed_vs_null.png   D4 observado frente al nulo permutacional por estrato
  fig/p_cross.png            P_cross(n) por representación (global) y por periodo
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402

RES = sl.ROOT / "results"
FIG = RES / "fig"
PILOT = {"D1": 77.71, "D2": 275.78, "D3": 6367.10, "D4": 16.53, "D5": 13.56}
COLORS = ["#4c72b0", "#55a868", "#c44e52", "#8172b2", "#ccb974"]


def fig_base_rate(br):
    periods = [p for p in sl.PERIODS if p in br["strata"]["period"]]
    colls = sorted(br["strata"]["collection"].items(), key=lambda kv: -kv[1]["windows"])
    colls = [(k, v) for k, v in colls if v["windows"] >= 20000][:18]
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={"height_ratios": [1, 1.6]})
    for ax, items, title in ((axes[0], [(p, br["strata"]["period"][p]) for p in periods], "por periodo"),
                             (axes[1], colls, "por colección (≥ 20k ventanas)")):
        labels = [f"{k}\n(n={v['works']}, {v['windows']/1000:.0f}k)" for k, v in items]
        x = np.arange(len(items))
        w = 0.16
        for j, d in enumerate(sl.DEFS):
            vals = [v["rate_per_100k"][d] or 0 for _, v in items]
            ax.bar(x + (j - 2) * w, vals, w, label=d, color=COLORS[j])
            ax.axhline(PILOT[d], color=COLORS[j], ls=":", lw=0.8)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7, rotation=0 if len(items) < 8 else 60, ha="center" if len(items) < 8 else "right")
        ax.set_ylabel("ocurrencias por 100k ventanas (log)")
        ax.set_title(f"Tasa base anidada D1–D5 {title}; líneas punteadas = piloto (music21 art)")
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(ncol=5, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "base_rate_strata.png", dpi=150)
    plt.close(fig)


def fig_null(br):
    items = [("todo", br["strata"]["all"]["all"])]
    items += [(p, br["strata"]["period"][p]) for p in sl.PERIODS if p in br["strata"]["period"]]
    colls = sorted(br["strata"]["collection"].items(), key=lambda kv: -kv[1]["windows"])
    items += [(k, v) for k, v in colls if v["perm_works"] >= 5][:14]
    items = [(k, v) for k, v in items if v["null"]["D4"]["mean"] is not None]
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(items))
    obs = [v["null"]["D4"]["obs"] for _, v in items]
    mean = [v["null"]["D4"]["mean"] for _, v in items]
    lo = [v["null"]["D4"]["ci95"][0] for _, v in items]
    hi = [v["null"]["D4"]["ci95"][1] for _, v in items]
    ax.errorbar(x, mean, yerr=[np.array(mean) - np.array(lo), np.array(hi) - np.array(mean)],
                fmt="s", color="grey", capsize=3, label="nulo: media e IC95 (100 permutaciones)")
    ax.scatter(x, obs, color="#c44e52", zorder=3, label="observado")
    for xi, (k, v) in zip(x, items):
        ax.annotate(f"p={v['null']['D4']['p']:.2f}\n×{v['null']['D4']['ratio']:.2f}", (xi, max(obs[xi], hi[xi])),
                    textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{k}\n({v['perm_works']} obras)" for k, v in items], rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("ocurrencias D4 (obras con ≥150 notas)")
    ax.set_yscale("symlog", linthresh=10)
    ax.set_ylim(bottom=0)
    ax.set_title("D4 (altura generalizada ∧ ritmo) observado frente al nulo de barajado intra-voz")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "observed_vs_null.png", dpi=150)
    plt.close(fig)


def fig_pcross(un, pilot_un):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, rep in zip(axes, ("IV", "IVR")):
        c = un["curve"][rep]
        ax.plot([d["n"] for d in c], [d["p_cross"] for d in c], "o-", color="black", lw=2, label="corpus real (todo)")
        if pilot_un:
            pc = pilot_un["curve"][rep]
            ax.plot([d["n"] for d in pc], [d["p_cross"] for d in pc], "s--", color="grey", label="piloto (music21 art)")
        for j, p in enumerate(sl.PERIODS):
            cp = un["curve_by_period"].get(rep, {}).get(p)
            if not cp or not cp[0]["tokens"]:
                continue
            ax.plot([d["n"] for d in cp], [d["p_cross"] or 0 for d in cp], ".-", alpha=0.8,
                    label=f"{p} (n={un['works_by_period'].get(p, 0)})")
        ax.set_title({"IV": "solo intervalos", "IVR": "intervalos + clase rítmica"}[rep])
        ax.set_xlabel("n (notas)")
        ax.set_ylim(0, 1.02)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    axes[0].set_ylabel("P_cross(n): prob. de que un pasaje de n notas aparezca idéntico en otra obra")
    fig.tight_layout()
    fig.savefig(FIG / "p_cross.png", dpi=150)
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    br = json.loads((RES / "base_rate.json").read_text())
    un = json.loads((RES / "uniqueness.json").read_text())
    pilot_un_path = sl.ROOT / "scripts" / "pilot" / "uniq_art.json"
    pilot_un = json.loads(pilot_un_path.read_text()) if pilot_un_path.exists() else None
    fig_base_rate(br)
    fig_null(br)
    fig_pcross(un, pilot_un)
    print("figuras en", FIG)


if __name__ == "__main__":
    main()
