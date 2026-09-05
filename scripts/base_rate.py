"""Fase 1 — tasa base del motivo de la Quinta sobre la caché, estratificada.

Definiciones D1–D5, clase rítmica y modelo nulo idénticos al piloto
(scripts/pilot/base_rate2.py); ver seqlib.py.  Diferencias documentadas en
docs/DECISIONES.md: unidad = obra completa (D-15), colapso de voces dobladas (D-13),
generador aleatorio sembrado por obra (D-20), obras objetivo excluidas (D-21, D-35),
1000 permutaciones para la tabla por estrato (D-34), desgloses de D4 por rol de voz y
posición cadencial (D-32).

Estratos: collection, period, composer (>= 5 obras).  Salida: results/base_rate.json.

Uso: .venv/bin/python scripts/base_rate.py [--rest-break 0] [--n-perm 1000] [--include-target]
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
N_PERM = 1000            # D-34: tabla por estrato (period, all); el resto usa las primeras 100
N_PERM_SMALL = 100
PERM_CHUNK = 200
MIN_WINDOWS_FOR_PERM = 150
CADENTIAL_QL = 1.0       # D-32: nota larga en la última negra del compás
OUT = sl.ROOT / "results" / "base_rate.json"
CLASSES = ["bass_cad", "bass_other", "other_cad", "other_other"]


def d2_mask(iv: np.ndarray) -> np.ndarray:
    return (iv[:, :-2] == 0) & (iv[:, 1:-1] == 0) & ((iv[:, 2:] == -4) | (iv[:, 2:] == -3))


def d3_mask(d: np.ndarray) -> np.ndarray:
    e1, e2, e3, e4 = d[:, :-3], d[:, 1:-2], d[:, 2:-1], d[:, 3:]
    return ((e1 > 0) & (e2 > 0) & (e3 > 0) & (np.abs(e1 - e2) <= sl.TOL) & (np.abs(e2 - e3) <= sl.TOL)
            & (e4 >= 2 * e3 - sl.TOL))


def weak_mask(off: np.ndarray) -> np.ndarray:
    r = np.round(off)
    return (np.abs(off - r) > sl.TOL) | ((r.astype(np.int64) % 2) == 1)


def analyse_work(data, rest_break, n_perm, rng_seed):
    """Recuentos observados, n-gramas y recuentos nulos de una obra (equivale a process()).
    Además: D4 y su nulo por clase (rol de voz × posición cadencial), D-32."""
    seqs = sl.sequences_ex(data, rest_break)
    counts = Counter()
    ngrams = Counter()
    windows = notes = 0
    null = {k: np.zeros(n_perm, dtype=np.int64) for k in ("D2", "D3", "D4")}
    cls_obs = Counter()          # clase -> D4 observado
    cls_windows = Counter()      # clase -> ventanas
    cls_null = {c: np.zeros(n_perm, dtype=np.int64) for c in CLASSES}
    total_notes = sum(len(s[3]) for s in seqs)
    do_perm = total_notes >= MIN_WINDOWS_FOR_PERM
    rng = np.random.default_rng(rng_seed)
    for (_, _, is_bass, arr) in seqs:
        n = len(arr)
        notes += n
        midi, durs, offs, brem = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]
        ivs = np.diff(midi).astype(np.int64)
        m2 = d2_mask(ivs[None, :])[0]
        m3 = d3_mask(durs[None, :])[0]
        m1 = (ivs[:-2] == 0) & (ivs[1:-1] == 0) & (ivs[2:] == -4)
        m4 = m2 & m3
        m5 = m4 & weak_mask(offs[:-3])
        windows += n - 3
        counts["D1"] += int(m1.sum())
        counts["D2"] += int(m2.sum())
        counts["D3"] += int(m3.sum())
        counts["D4"] += int(m4.sum())
        counts["D5"] += int(m5.sum())
        # clase de cada ventana: nota larga (4.ª) en la última negra del compás o antes de silencio/fin
        last_rem = brem[3:]
        cad = ((last_rem >= 0) & (last_rem <= CADENTIAL_QL + sl.TOL))
        cad[-1] = True                      # última ventana: la 4.ª nota precede a silencio o fin de voz
        role = "bass" if is_bass else "other"
        cls = np.where(cad, f"{role}_cad", f"{role}_other")
        for c in CLASSES:
            sel = cls == c
            if sel.any():
                cls_windows[c] += int(sel.sum())
                cls_obs[c] += int(m4[sel].sum())
        tri = ivs[:-2] * 1_000_000 + ivs[1:-1] * 1000 + ivs[2:]
        ngrams.update(tri.tolist())
        if do_perm and n >= 4:
            for p0 in range(0, n_perm, PERM_CHUNK):
                k = min(PERM_CHUNK, n_perm - p0)
                pi = np.argsort(rng.random((k, n - 1)), axis=1)
                pd_ = np.argsort(rng.random((k, n)), axis=1)
                c2 = d2_mask(ivs[pi])
                c3 = d3_mask(durs[pd_])
                c4 = c2 & c3
                null["D2"][p0:p0 + k] += c2.sum(axis=1)
                null["D3"][p0:p0 + k] += c3.sum(axis=1)
                null["D4"][p0:p0 + k] += c4.sum(axis=1)
                for c in CLASSES:          # la clase queda ligada a la posición original (D-32)
                    sel = cls == c
                    if sel.any():
                        cls_null[c][p0:p0 + k] += c4[:, sel].sum(axis=1)
    return counts, windows, notes, ngrams, null, do_perm, cls_obs, cls_windows, cls_null


class Stratum:
    def __init__(self, n_perm=N_PERM):
        self.n_perm = n_perm
        self.works = 0
        self.windows = 0
        self.notes = 0
        self.counts = Counter()
        self.prevalence = Counter()
        self.null = {k: np.zeros(n_perm, dtype=np.int64) for k in ("D2", "D3", "D4")}
        self.obs_perm = Counter()
        self.perm_works = 0
        self.cls_obs = Counter()
        self.cls_windows = Counter()
        self.cls_obs_perm = Counter()
        self.cls_null = {c: np.zeros(n_perm, dtype=np.int64) for c in CLASSES}

    def add(self, counts, windows, notes, null, did, cls_obs, cls_windows, cls_null):
        self.works += 1
        self.windows += windows
        self.notes += notes
        for k, v in counts.items():
            self.counts[k] += v
            if v:
                self.prevalence[k] += 1
        for c in CLASSES:
            self.cls_obs[c] += cls_obs.get(c, 0)
            self.cls_windows[c] += cls_windows.get(c, 0)
        if did:
            self.perm_works += 1
            for k in self.null:
                self.null[k] += null[k][: self.n_perm]
                self.obs_perm[k] += counts.get(k, 0)
            for c in CLASSES:
                self.cls_null[c] += cls_null[c][: self.n_perm]
                self.cls_obs_perm[c] += cls_obs.get(c, 0)

    @staticmethod
    def _null_stats(vals: np.ndarray, obs: int, n_perm: int):
        v = np.sort(vals)
        mean = float(v.mean())
        lo, hi = int(v[int(0.025 * n_perm)]), int(v[int(np.ceil(0.975 * n_perm)) - 1])
        ge = int((vals >= obs).sum())
        return {"obs": int(obs), "mean": mean, "ci95": [lo, hi], "ratio": (obs / mean if mean else None),
                "p": (ge + 1) / (n_perm + 1), "n_perm": n_perm}

    def summary(self):
        w = self.windows
        out = {"works": self.works, "windows": w, "notes": self.notes,
               "counts": {d: int(self.counts[d]) for d in sl.DEFS},
               "rate_per_100k": {d: (1e5 * self.counts[d] / w if w else None) for d in sl.DEFS},
               "prevalence": {d: int(self.prevalence[d]) for d in sl.DEFS},
               "prevalence_pct": {d: (100 * self.prevalence[d] / self.works if self.works else None) for d in sl.DEFS},
               "null": {}, "perm_works": self.perm_works, "n_perm": self.n_perm, "d4_by_class": {}}
        for k in ("D2", "D3", "D4"):
            out["null"][k] = (self._null_stats(self.null[k], self.obs_perm[k], self.n_perm)
                              if self.perm_works else None)
        for c in CLASSES:
            cw = self.cls_windows[c]
            out["d4_by_class"][c] = {
                "windows": int(cw), "obs": int(self.cls_obs[c]),
                "rate_per_100k": (1e5 * self.cls_obs[c] / cw if cw else None),
                "null": (self._null_stats(self.cls_null[c], self.cls_obs_perm[c], self.n_perm)
                         if self.perm_works and cw else None)}
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rest-break", type=float, default=0.0)
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    ap.add_argument("--include-target", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    n_perm = args.n_perm
    n_small = min(N_PERM_SMALL, n_perm)

    works = sl.load_catalog(exclude_target=not args.include_target)
    composers = sl.composer_strata(works)
    targets = [w for w, r in sl.load_catalog(exclude_target=False).items() if r["is_target"] == "1"]
    print(f"obras en catálogo: {len(works)}; compositores con >=5 obras: {len(composers)}; "
          f"obras objetivo excluidas: {targets if not args.include_target else 'ninguna'}", flush=True)

    strata = {"all": defaultdict(lambda: Stratum(n_perm)), "period": defaultdict(lambda: Stratum(n_perm)),
              "collection": defaultdict(lambda: Stratum(n_small)), "composer": defaultdict(lambda: Stratum(n_small)),
              "collection_x_period": defaultdict(lambda: Stratum(n_small))}
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
        res = analyse_work(data, args.rest_break, n_perm, seed)
        del data
        counts, windows, notes, ngrams, null, did, cls_obs, cls_windows, cls_null = res
        if windows == 0:
            continue
        payload = (counts, windows, notes, null, did, cls_obs, cls_windows, cls_null)
        strata["all"]["all"].add(*payload)
        strata["collection"][w["collection"]].add(*payload)
        strata["period"][w["period"]].add(*payload)
        strata["collection_x_period"][f"{w['collection']}|{w['period']}"].add(*payload)
        if w["composer_id"] in composers:
            strata["composer"][w["composer_id"]].add(*payload)
        ngrams_all.update(ngrams)
        ngrams_period[w["period"]].update(ngrams)
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(works)}  {(time.time()-t0)/60:.1f} min  ventanas={strata['all']['all'].windows:,}", flush=True)

    def tri_tuple(code):
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
        "seed": SEED, "n_perm": n_perm, "n_perm_small": n_small, "min_windows_for_perm": MIN_WINDOWS_FOR_PERM,
        "rest_break": args.rest_break, "include_target": args.include_target, "targets_excluded": targets,
        "cadential_ql": CADENTIAL_QL,
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
        print(f"  nulo {k}: obs {n['obs']:,} media {n['mean']:.1f} IC95 {n['ci95']} ratio {n['ratio']:.2f} p={n['p']:.4f}")
    for c in CLASSES:
        x = a["d4_by_class"][c]
        nn = x["null"]
        print(f"  D4 {c:12s}: ventanas {x['windows']:>9,} obs {x['obs']:5d} ({x['rate_per_100k']:.2f}/100k)"
              + (f" nulo {nn['mean']:.1f} ratio {nn['ratio']:.2f} p={nn['p']:.4f}" if nn else ""))
    print(f"guardado en {args.out}  ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    sys.exit(main())
