"""Modelo de fondo por tipo de n-grama IVR (D-37), insumo del E-value de Fase 2.

Para cada estrato (los cinco bins de periodo más la unión 1750–1830) y n = 4..12:
    p_q = (count_q + 1) / (N + V + 1)            (Laplace: +1 por tipo, un cajón «no visto»)
donde count_q = ventanas del estrato con el n-grama q, N = ventanas totales del estrato,
V = tipos distintos observados.  Tipos no vistos: p_unseen = 1 / (N + V + 1).

Se guarda results/background/<estrato>_n<n>.parquet con una fila por (hash, composer_id):
    hash (uint64), composer (int16, código de results/background/meta.json), count (int32)
y results/background/meta.json con N, V, ventanas y tipos exclusivos por compositor.
Guardar por compositor permite recalcular el fondo excluyendo compositores (regla D-37:
para un par (A, B) el fondo se estima sin los compositores de A ni de B) sin volver a la caché.

Uso:
  .venv/bin/python scripts/background.py build        # tablas + background_summary.md
  .venv/bin/python scripts/background.py calibrate    # 200 ventanas, fig/background_calibration.png
API:
  bg = Background.load("1750-1830", 8); bg.p(hashes, exclude=("beethoven_l", "cherubini_l"))
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402
import uniqueness as un  # noqa: E402

NS = list(range(4, 13))
STRATA = {"lt1750": ["<1750"], "1750-1800": ["1750–1800"], "1800-1830": ["1800–1830"],
          "1830-1900": ["1830–1900"], "gt1900": [">1900"], "1750-1830": ["1750–1800", "1800–1830"]}
OUT = sl.ROOT / "results" / "background"
FIG = sl.ROOT / "results" / "fig"
SEED = 20260903
N_CAL = 200
N_CAL_N = 8
CAL_STRATUM = "1750-1830"


# ----------------------------------------------------------------------------
class Background:
    """Tabla de fondo de un (estrato, n) con exclusión opcional de compositores.
    Con exclusión: N' = N − ventanas de los excluidos; V' = V − tipos exclusivos de cada excluido
    (aproximación: los tipos compartidos solo entre dos excluidos no se descuentan)."""

    def __init__(self, stratum: str, n: int, hashes, composer, count, meta):
        self.stratum, self.n = stratum, n
        order = np.argsort(hashes, kind="stable")
        self.hashes, self.composer, self.count = hashes[order], composer[order], count[order]
        self.meta = meta
        self.codes = {name: code for code, name in enumerate(meta["composers"])}
        self.starts = np.r_[0, np.nonzero(self.hashes[1:] != self.hashes[:-1])[0] + 1]
        self.uh = self.hashes[self.starts]
        self.uc = np.add.reduceat(self.count, self.starts)
        self.N, self.V = meta["N"], meta["V"]

    @classmethod
    def load(cls, stratum: str, n: int):
        t = pq.read_table(OUT / f"{stratum}_n{n}.parquet")
        allmeta = json.loads((OUT / "meta.json").read_text())
        meta = dict(allmeta["tables"][f"{stratum}_n{n}"])
        meta["composers"] = allmeta["composers"]
        return cls(stratum, n, t["hash"].to_numpy(), t["composer"].to_numpy(), t["count"].to_numpy(), meta)

    def totals(self, exclude=()):
        """(N', V') del estrato sin los compositores excluidos."""
        N, V = self.N, self.V
        for c in set(exclude):
            N -= self.meta["tokens_by_composer"].get(c, 0)
            V -= self.meta["exclusive_types_by_composer"].get(c, 0)
        return N, V

    def counts(self, query: np.ndarray, exclude=()):
        """count_q para cada hash consultado, sin los compositores excluidos."""
        query = np.asarray(query, dtype=np.uint64)
        idx = np.searchsorted(self.uh, query)
        idx[idx >= len(self.uh)] = 0
        found = self.uh[idx] == query
        out = np.where(found, self.uc[idx], 0).astype(np.int64)
        if exclude:
            codes = {self.codes[c] for c in exclude if c in self.codes}
            for k in np.nonzero(found)[0]:
                a = self.starts[idx[k]]
                b = self.starts[idx[k] + 1] if idx[k] + 1 < len(self.starts) else len(self.hashes)
                sel = np.isin(self.composer[a:b], list(codes))
                out[k] -= int(self.count[a:b][sel].sum())
        return out

    def alpha_value(self, alpha):
        """alpha numérico, o 'gt': pseudocuenta tal que la masa de tipos no vistos iguale la
        estimación de Good–Turing N1/N (N1 = tipos vistos una sola vez)."""
        if alpha == "gt":
            n1 = self.meta.get("N1")
            if n1 is None:
                n1 = int((self.uc == 1).sum())
            return n1 / (self.V + 1) * (self.N / max(self.N - n1, 1))
        return float(alpha)

    def p(self, query: np.ndarray, exclude=(), alpha=1.0):
        """p_q = (count_q + alpha) / (N + alpha·(V + 1)), sin los compositores excluidos.
        alpha=1: Laplace add-one (D-37). alpha='gt': pseudocuenta Good–Turing."""
        a = self.alpha_value(alpha)
        N, V = self.totals(exclude)
        return (self.counts(query, exclude) + a) / (N + a * (V + 1))


# ----------------------------------------------------------------------------
def build(rest_break=0.0):
    works = sl.load_catalog(exclude_target=True)
    composers = sorted({r["composer_id"] for r in works.values()})
    code = {c: i for i, c in enumerate(composers)}
    # acumular hashes y códigos por (estrato, n)
    acc = {(s, n): ([], []) for s in STRATA for n in NS}
    works_by_stratum = {s: 0 for s in STRATA}
    t0 = time.time()
    n_used = 0
    for i, (wid, r) in enumerate(sorted(works.items())):
        strata = [s for s, ps in STRATA.items() if r["period"] in ps]
        if not strata:
            continue
        d = sl.load_work(wid)
        if d is None:
            continue
        ww = un.work_windows(d, rest_break)["IVR"]
        del d
        n_used += 1
        for s in strata:
            works_by_stratum[s] += 1
        for n in NS:
            h = ww.get(n)
            if h is None or len(h) == 0:
                continue
            cc = np.full(len(h), code[r["composer_id"]], dtype=np.int16)
            for s in strata:
                acc[(s, n)][0].append(h)
                acc[(s, n)][1].append(cc)
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(works)} {(time.time()-t0)/60:.1f} min", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"seed": SEED, "rest_break": rest_break, "composers": composers, "ns": NS,
            "strata": {s: ps for s, ps in STRATA.items()}, "works_used": n_used,
            "works_by_stratum": works_by_stratum, "tables": {}}
    for (s, n), (hs, cs) in acc.items():
        if not hs:
            continue
        H = np.concatenate(hs)
        C = np.concatenate(cs)
        key = np.stack([H, C.astype(np.uint64)], axis=1)
        order = np.lexsort((C, H))
        H, C = H[order], C[order]
        new = np.r_[True, (H[1:] != H[:-1]) | (C[1:] != C[:-1])]
        starts = np.nonzero(new)[0]
        cnt = np.diff(np.r_[starts, len(H)]).astype(np.int32)
        uh, uc = H[starts], C[starts]
        tbl = pa.table({"hash": pa.array(uh, pa.uint64()), "composer": pa.array(uc, pa.int16()),
                        "count": pa.array(cnt, pa.int32())})
        pq.write_table(tbl, OUT / f"{s}_n{n}.parquet", compression="zstd")
        # tipos exclusivos por compositor (para el ajuste de V al excluir)
        new_h = np.r_[True, uh[1:] != uh[:-1]]
        type_id = np.cumsum(new_h) - 1
        comps_per_type = np.bincount(type_id)
        exclusive = uc[np.isin(type_id, np.nonzero(comps_per_type == 1)[0])]
        excl_by_comp = np.bincount(exclusive, minlength=len(composers))
        tok_by_comp = np.bincount(C, minlength=len(composers))
        N, V = int(len(H)), int(new_h.sum())
        meta["tables"][f"{s}_n{n}"] = {
            "N": N, "V": V, "N1": int((np.bincount(type_id, weights=cnt) == 1).sum()),
            "p_unseen": 1.0 / (N + V + 1), "rows": int(len(uh)),
            "tokens_by_composer": {composers[k]: int(v) for k, v in enumerate(tok_by_comp) if v},
            "exclusive_types_by_composer": {composers[k]: int(v) for k, v in enumerate(excl_by_comp) if v},
        }
        print(f"{s:10s} n={n:2d} N={N:,} V={V:,} filas={len(uh):,}", flush=True)
        acc[(s, n)] = ([], [])
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"tablas en {OUT} ({(time.time()-t0)/60:.1f} min)")


# ----------------------------------------------------------------------------
def summary():
    meta = json.loads((OUT / "meta.json").read_text())
    L = ["# Modelo de fondo por tipo (D-37)", "",
         f"Estratos: {', '.join(STRATA)}. n = {NS[0]}..{NS[-1]}. p_q = (count_q + 1)/(N + V + 1) sobre n-gramas IVR "
         f"(intervalos + clase rítmica) de las obras primarias del estrato, sin obras objetivo. "
         f"Obras usadas: {meta['works_used']}.", "",
         "## Distribución de log10(p_q) sobre tipos observados", "",
         "| estrato | n | N (ventanas) | V (tipos) | log10 p_unseen | p1 | p10 | p50 | p90 | p99 | máx |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    top = None
    for s in STRATA:
        for n in NS:
            k = f"{s}_n{n}"
            if k not in meta["tables"]:
                continue
            bg = Background.load(s, n)
            # count por tipo
            order = np.argsort(bg.hashes, kind="stable")
            h, c = bg.hashes[order], bg.count[order]
            starts = np.r_[0, np.nonzero(h[1:] != h[:-1])[0] + 1]
            uc = np.add.reduceat(c, starts)
            N, V = bg.meta["N"], bg.meta["V"]
            lp = np.log10((uc + 1) / (N + V + 1))
            pc = np.percentile(lp, [1, 10, 50, 90, 99])
            L.append(f"| {s} | {n} | {N:,} | {V:,} | {np.log10(1/(N+V+1)):.2f} | " +
                     " | ".join(f"{x:.2f}" for x in pc) + f" | {lp.max():.2f} |")
            if s == CAL_STRATUM and n == N_CAL_N:
                uh = h[starts]
                idx = np.argsort(-uc)[:20]
                top = [(int(uh[i]), int(uc[i]), float((uc[i] + 1) / (N + V + 1))) for i in idx]
    # decodificar los 20 tipos más frecuentes de n=8 en 1750-1830 buscando sus símbolos en la caché
    if top:
        L += ["", f"## Los 20 tipos más frecuentes de n = {N_CAL_N} en {CAL_STRATUM}", "",
              "| # | count | p_q | intervalos | clase rítmica |", "|---|---|---|---|---|"]
        want = {h: (c, p) for h, c, p in top}
        sym = find_symbols(set(want), CAL_STRATUM, N_CAL_N)
        for rank, (h, c, p) in enumerate(top, 1):
            iv, rc = sym.get(h, ("?", "?"))
            L.append(f"| {rank} | {c:,} | {p:.2e} | `{iv}` | `{rc}` |")
        L += ["", "Clase rítmica: −2 mucho más corta, −1 más corta, 0 igual, 1 más larga, 2 mucho más larga "
              "(ratio de duración respecto a la nota anterior)."]
    (sl.ROOT / "results" / "background_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def find_symbols(hashes: set, stratum: str, n: int, rest_break=0.0):
    """Busca en la caché las secuencias de símbolos de los hashes pedidos (para el informe)."""
    works = sl.load_catalog(exclude_target=True)
    found = {}
    m = n - 1
    for wid, r in works.items():
        if r["period"] not in STRATA[stratum]:
            continue
        d = sl.load_work(wid)
        if d is None:
            continue
        for seq in sl.sequences(d, rest_break):
            arr = np.array(seq, dtype=np.float64)
            ivs = np.diff(arr[:, 0]).astype(np.int64)
            rcs = un.rclass_vec(arr[:-1, 1], arr[1:, 1])
            ivr = (ivs + 200) * 8 + (rcs + 2)
            if len(ivr) < m:
                continue
            hs = un.rolling_hashes(ivr, m)
            for k in np.nonzero(np.isin(hs, list(hashes - set(found))))[0]:
                found[int(hs[k])] = (",".join(str(x) for x in ivs[k:k + m]), ",".join(str(x) for x in rcs[k:k + m]))
        if len(found) == len(hashes):
            break
    return found


# ----------------------------------------------------------------------------
def calibrate(rest_break=0.0, alpha=1.0, suffix=""):
    """200 ventanas de 8 notas al azar de obras de 1750-1830: E predicho vs observado,
    leave-both-composers-out (D-37)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(SEED)
    works = sl.load_catalog(exclude_target=True)
    wids = sorted(w for w, r in works.items() if r["period"] in STRATA[CAL_STRATUM])
    # hashes por obra (n=8) y compositor
    per_work = {}
    comp = {}
    for wid in wids:
        d = sl.load_work(wid)
        if d is None:
            continue
        h = un.work_windows(d, rest_break)["IVR"].get(N_CAL_N)
        if h is None or len(h) == 0:
            continue
        per_work[wid] = h
        comp[wid] = works[wid]["composer_id"]
    wl = sorted(per_work)
    tokens = np.array([len(per_work[w]) for w in wl])
    # muestreo uniforme sobre ventanas
    cum = np.cumsum(tokens)
    picks = rng.integers(0, cum[-1], size=N_CAL)
    wi = np.searchsorted(cum, picks, side="right")
    queries = []
    for p, i in zip(picks, wi):
        off = p - (cum[i - 1] if i > 0 else 0)
        queries.append((wl[i], int(per_work[wl[i]][off])))
    bg = Background.load(CAL_STRATUM, N_CAL_N)
    # conjuntos únicos por obra para «aparece en B»
    tok_of = {w: int(len(per_work[w])) for w in wl}
    rows = []
    for qi, (wa, q) in enumerate(queries):
        ca = comp[wa]
        pred_occ = pred_pres = 0.0
        obs_occ = obs_pres = 0
        nB = 0
        # p_q por compositor de B: caché por cb
        p_by_cb = {}
        for wb in wl:
            cb = comp[wb]
            if cb == ca:
                continue
            if cb not in p_by_cb:
                p_by_cb[cb] = float(bg.p(np.array([q], dtype=np.uint64), exclude=(ca, cb), alpha=alpha)[0])
            pq_ = p_by_cb[cb]
            E = tok_of[wb] * pq_
            pred_occ += E
            pred_pres += 1 - np.exp(-E)
            occ = int((per_work[wb] == q).sum())
            obs_occ += occ
            obs_pres += 1 if occ else 0
            nB += 1
        rows.append(dict(query=qi, work=wa, composer=ca, hash=q, n_B=nB,
                         p_q_excl_A=float(bg.p(np.array([q], dtype=np.uint64), exclude=(ca,), alpha=alpha)[0]),
                         count_excl_A=int(bg.counts(np.array([q], dtype=np.uint64), exclude=(ca,))[0]),
                         pred_occurrences=pred_occ, obs_occurrences=obs_occ,
                         pred_works=pred_pres, obs_works=obs_pres))
        if (qi + 1) % 50 == 0:
            print(f"  {qi+1}/{N_CAL}", flush=True)
    import csv
    with open(sl.ROOT / "results" / f"background_calibration{suffix}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    po = np.array([r["pred_occurrences"] for r in rows])
    oo = np.array([r["obs_occurrences"] for r in rows])
    pw = np.array([r["pred_works"] for r in rows])
    ow = np.array([r["obs_works"] for r in rows])
    # curva de calibración por deciles de predicción
    def binned(pred, obs, k=10):
        order = np.argsort(pred)
        bins = np.array_split(order, k)
        return (np.array([pred[b].mean() for b in bins]), np.array([obs[b].mean() for b in bins]),
                np.array([obs[b].std(ddof=1) / np.sqrt(len(b)) for b in bins]))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    for ax, pred, obs, title in ((axes[0], po, oo, "ocurrencias en obras B (Σ_B windows_B·p_q)"),
                                 (axes[1], pw, ow, "obras B que contienen q (Σ_B 1−e^{−E_B})")):
        eps = 0.05
        ax.scatter(pred + eps, obs + eps, s=14, alpha=0.5, color="#4c72b0", label=f"{N_CAL} ventanas de {N_CAL_N} notas")
        bx, by, be = binned(pred, obs)
        ax.errorbar(bx + eps, by + eps, yerr=be, fmt="o-", color="#c44e52", capsize=3, label="media por decil de E predicho")
        lim = [eps, max(pred.max(), obs.max()) * 1.5 + eps]
        ax.plot(lim, lim, "k--", lw=1, label="diagonal")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("E predicho (+0,05)")
        ax.set_ylabel("observado (+0,05)")
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    a_val = bg.alpha_value(alpha)
    fig.suptitle(f"Calibración del fondo por tipo, estrato {CAL_STRATUM}, n={N_CAL_N}, leave-both-composers-out (D-37); "
                 f"pseudocuenta α={a_val:.3g}" + (" (Good–Turing)" if alpha == "gt" else " (Laplace)"))
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"background_calibration{suffix}.png", dpi=150)
    # resumen numérico
    def ratio(a, b):
        return float(a.sum() / b.sum()) if b.sum() else float("nan")
    zero_pred = (po < 0.5)
    single = np.array([r["count_excl_A"] == 0 for r in rows])
    txt = [f"pseudocuenta α = {a_val:.4g} ({'Good–Turing' if alpha == 'gt' else 'Laplace'}); N1/N (tipos únicos) = {int((bg.uc == 1).sum())/bg.N:.3f}",
           f"ventanas {N_CAL}, obras B por ventana ≈ {np.mean([r['n_B'] for r in rows]):.0f}; ventanas cuyo tipo no aparece fuera de su compositor: {single.sum()}",
           f"  de esas {single.sum()}: predicho {po[single].sum():.1f} ocurrencias, observado {oo[single].sum()} (por construcción 0)",
           f"ocurrencias: predicho total {po.sum():.1f}, observado {oo.sum()}, ratio obs/pred {ratio(oo, po):.2f}",
           f"obras con q: predicho total {pw.sum():.1f}, observado {ow.sum()}, ratio {ratio(ow, pw):.2f}",
           f"ventanas con E_occ < 0.5: {zero_pred.sum()} (observadas {oo[zero_pred].sum()} ocurrencias, predichas {po[zero_pred].sum():.1f})",
           f"correlación log(pred+0.05) vs log(obs+0.05): {np.corrcoef(np.log(po+0.05), np.log(oo+0.05))[0,1]:.3f}"]
    bx, by, be = binned(po, oo)
    txt.append("deciles (pred → obs): " + "; ".join(f"{x:.2f}→{y:.2f}" for x, y in zip(bx, by)))
    with open(sl.ROOT / "results" / "background_calibration.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## α = {a_val:.4g} ({'Good–Turing' if alpha == 'gt' else 'Laplace'}){suffix}\n\n" + "\n".join(f"- {t}" for t in txt) + "\n")
    print("\n".join(txt))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "summary", "calibrate", "all"])
    ap.add_argument("--rest-break", type=float, default=0.0)
    ap.add_argument("--alpha", default="1", help="pseudocuenta: número o 'gt'")
    args = ap.parse_args()
    alpha = "gt" if args.alpha == "gt" else float(args.alpha)
    suffix = "" if alpha == 1.0 else ("_gt" if alpha == "gt" else f"_a{alpha:g}")
    if args.cmd in ("build", "all"):
        build(args.rest_break)
    if args.cmd in ("summary", "all"):
        summary()
    if args.cmd in ("calibrate", "all"):
        calibrate(args.rest_break, alpha, suffix)


if __name__ == "__main__":
    main()
