"""Fase 1 — tasa base del motivo de la Quinta sobre la caché, estratificada.

Definiciones D1–D5, clase rítmica y modelo nulo idénticos al piloto
(scripts/pilot/base_rate2.py); ver seqlib.py.  Diferencias documentadas en
docs/DECISIONES.md: unidad = obra completa (D-15), colapso de voces dobladas (D-13),
generador aleatorio sembrado por obra (D-20), obra objetivo excluida (D-21).

Estratos: collection, period, composer (>= 5 obras).  Salida: results/base_rate.json.

Uso: .venv/bin/python scripts/base_rate.py [--rest-break 0] [--n-perm 100] [--include-target]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402

SEED = 20260903
N_PERM = 100
MIN_WINDOWS_FOR_PERM = 150
OUT = sl.ROOT / "results" / "base_rate.json"


def d2_mask(iv: np.ndarray) -> np.ndarray:
    """(0,0,-4) o (0,0,-3) en ventanas de 3 intervalos consecutivos."""
    return (iv[:-2] == 0) & (iv[1:-1] == 0) & ((iv[2:] == -4) | (iv[2:] == -3))


def d3_mask(d: np.ndarray) -> np.ndarray:
    """Tres duraciones iguales (> 0) y cuarta >= 2x (rhythm_ok vectorizado)."""
    d1, d2, d3, d4 = d[:-3], d[1:-2], d[2:-1], d[3:]
    return ((d1 > 0) & (d2 > 0) & (d3 > 0) & (np.abs(d1 - d2) <= sl.TOL) & (np.abs(d2 - d3) <= sl.TOL)
            & (d4 >= 2 * d3 - sl.TOL))


def weak_mask(off: np.ndarray) -> np.ndarray:
    r = np.round(off)
    return (np.abs(off - r) > sl.TOL) | ((r.astype(np.int64) % 2) == 1)


def analyse_work(data, rest_break, n_perm, rng_seed):
    """Recuentos observados, n-gramas y recuentos nulos de una obra (equivale a process())."""
    seqs = sl.sequences(data, rest_break)
    counts = Counter()
    ngrams = Counter()
    windows = notes = 0
    null = {k: np.zeros(n_perm, dtype=np.int64) for k in ("D2", "D3", "D4")}
    total_notes = sum(len(s) for s in seqs)
    do_perm = total_notes >= MIN_WINDOWS_FOR_PERM
    rng = np.random.default_rng(rng_seed)
    for seq in seqs:
        n = len(seq)
        notes += n
        arr = np.array(seq, dtype=np.float64)
        midi = arr[:, 0]
        durs = arr[:, 1]
        offs = arr[:, 2]
        ivs = np.diff(midi).astype(np.int64)
        m2 = d2_mask(ivs)
        m3 = d3_mask(durs)
        m1 = (ivs[:-2] == 0) & (ivs[1:-1] == 0) & (ivs[2:] == -4)
        m4 = m2 & m3
        m5 = m4 & weak_mask(offs[:-3])
        windows += n - 3
        counts["D1"] += int(m1.sum())
        counts["D2"] += int(m2.sum())
        counts["D3"] += int(m3.sum())
        counts["D4"] += int(m4.sum())
        counts["D5"] += int(m5.sum())
        # 3-gramas de intervalo (para el ranking global)
        tri = ivs[:-2] * 1_000_000 + ivs[1:-1] * 1000 + ivs[2:]   # codificación entera
        ngrams.update(tri.tolist())
        if do_perm and n >= 4:
            # barajado independiente de intervalos y duraciones intra-voz (nulo del piloto)
            pi = np.argsort(rng.random((n_perm, n - 1)), axis=1)
            pd_ = np.argsort(rng.random((n_perm, n)), axis=1)
            si = ivs[pi]
            sd = durs[pd_]
            c2 = (si[:, :-2] == 0) & (si[:, 1:-1] == 0) & ((si[:, 2:] == -4) | (si[:, 2:] == -3))
            e1, e2, e3, e4 = sd[:, :-3], sd[:, 1:-2], sd[:, 2:-1], sd[:, 3:]
            c3 = ((e1 > 0) & (e2 > 0) & (e3 > 0) & (np.abs(e1 - e2) <= sl.TOL)
                  & (np.abs(e2 - e3) <= sl.TOL) & (e4 >= 2 * e3 - sl.TOL))
            null["D2"] += c2.sum(axis=1)
            null["D3"] += c3.sum(axis=1)
            null["D4"] += (c2 & c3).sum(axis=1)
    return counts, windows, notes, ngrams, null, do_perm


class Stratum:
    def __init__(self):
        self.works = 0
        self.windows = 0
        self.notes = 0
        self.counts = Counter()
        self.prevalence = Counter()
        self.null = {k: np.zeros(N_PERM, dtype=np.int64) for k in ("D2", "D3", "D4")}
        self.obs_perm = Counter()
        self.perm_works = 0

    def add(self, counts, windows, notes, null, did):
        self.works += 1
        self.windows += windows
        self.notes += notes
        for k, v in counts.items():
            self.counts[k] += v
            if v:
                self.prevalence[k] += 1
        if did:
            self.perm_works += 1
            for k in self.null:
                self.null[k] += null[k]
                self.obs_perm[k] += counts.get(k, 0)

    def summary(self):
        w = self.windows
        out = {"works": self.works, "windows": w, "notes": self.notes,
               "counts": {d: int(self.counts[d]) for d in sl.DEFS},
               "rate_per_100k": {d: (1e5 * self.counts[d] / w if w else None) for d in sl.DEFS},
               "prevalence": {d: int(self.prevalence[d]) for d in sl.DEFS},
               "prevalence_pct": {d: (100 * self.prevalence[d] / self.works if self.works else None) for d in sl.DEFS},
               "null": {}, "perm_works": self.perm_works}
        for k in ("D2", "D3", "D4"):
            vals = np.sort(self.null[k])
            mean = float(vals.mean()) if self.perm_works else None
            obs = int(self.obs_perm[k])
            ge = int((self.null[k] >= obs).sum())
            out["null"][k] = {
                "obs": obs, "mean": mean,
                "ci95": [int(vals[2]), int(vals[97])] if self.perm_works else None,
                "ratio": (obs / mean if mean else None),
                "p": (ge + 1) / (N_PERM + 1) if self.perm_works else None,
            }
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rest-break", type=float, default=0.0)
    ap.add_argument("--include-target", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    works = sl.load_catalog(exclude_target=not args.include_target)
    composers = sl.composer_strata(works)
    print(f"obras en catálogo: {len(works)}; compositores con >=5 obras: {len(composers)}", flush=True)

    strata = {"all": defaultdict(Stratum), "collection": defaultdict(Stratum),
              "period": defaultdict(Stratum), "composer": defaultdict(Stratum),
              "collection_x_period": defaultdict(Stratum)}
    ngrams_all = Counter()
    ngrams_period = defaultdict(Counter)
    missing = []
    t0 = time.time()
    for i, (wid, w) in enumerate(sorted(works.items())):
        data = sl.load_work(wid)
        if data is None:
            missing.append(wid)
            continue
        seed = SEED + zlib.crc32(wid.encode()) % 1_000_000
        counts, windows, notes, ngrams, null, did = analyse_work(data, args.rest_break, N_PERM, seed)
        del data
        if windows == 0:
            continue
        strata["all"]["all"].add(counts, windows, notes, null, did)
        strata["collection"][w["collection"]].add(counts, windows, notes, null, did)
        strata["period"][w["period"]].add(counts, windows, notes, null, did)
        strata["collection_x_period"][f"{w['collection']}|{w['period']}"].add(counts, windows, notes, null, did)
        if w["composer_id"] in composers:
            strata["composer"][w["composer_id"]].add(counts, windows, notes, null, did)
        ngrams_all.update(ngrams)
        ngrams_period[w["period"]].update(ngrams)
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(works)}  {(time.time()-t0)/60:.1f} min  ventanas={strata['all']['all'].windows:,}", flush=True)

    def tri_tuple(code):
        # deshacer codificación a*1e6 + b*1e3 + c con negativos
        c = ((code + 500) % 1000) - 500
        rest = (code - c) // 1000
        b = ((rest + 500) % 1000) - 500
        a = (rest - b) // 1000
        return (int(a), int(b), int(c))

    ranked = ngrams_all.most_common()
    total_ng = sum(ngrams_all.values())
    ranks = {}
    for tgt in sl.TARGETS:
        code = tgt[0] * 1_000_000 + tgt[1] * 1000 + tgt[2]
        rank = next((k + 1 for k, (g, _) in enumerate(ranked) if g == code), None)
        ranks[str(tgt)] = {"rank": rank, "count": ngrams_all.get(code, 0),
                           "pct": 100 * ngrams_all.get(code, 0) / total_ng if total_ng else None}

    out = {
        "seed": SEED, "n_perm": N_PERM, "min_windows_for_perm": MIN_WINDOWS_FOR_PERM,
        "rest_break": args.rest_break, "include_target": args.include_target,
        "works_in_catalog": len(works), "works_missing_cache": missing,
        "n_distinct_ngrams": len(ranked), "target_ngrams": ranks,
        "top_ngrams": [[list(tri_tuple(g)), c] for g, c in ranked[:300]],
        "rank_curve": [c for _, c in ranked[:5000]],
        "strata": {name: {k: s.summary() for k, s in sorted(d.items())} for name, d in strata.items()},
        "period_top_ngrams": {p: [[list(tri_tuple(g)), c] for g, c in cnt.most_common(30)]
                              for p, cnt in ngrams_period.items()},
    }
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    a = strata["all"]["all"].summary()
    print(f"\nobras {a['works']}  ventanas {a['windows']:,}  notas {a['notes']:,}")
    for d in sl.DEFS:
        print(f"  {d}: {a['counts'][d]:>8,}  {a['rate_per_100k'][d]:8.2f}/100k  obras>=1 {a['prevalence'][d]:5d} ({a['prevalence_pct'][d]:.1f}%)")
    for k in ("D2", "D3", "D4"):
        n = a["null"][k]
        print(f"  nulo {k}: obs {n['obs']:,} media {n['mean']:.1f} IC95 {n['ci95']} ratio {n['ratio']:.2f} p={n['p']:.3f}")
    print(f"guardado en {args.out}  ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    sys.exit(main())
