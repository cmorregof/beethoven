"""Fase 1b — curva de unicidad P_cross(n) sobre la caché, por representación y estrato.

Representaciones (idénticas al piloto scripts/pilot/uniqueness.py):
  IV   solo intervalos (transposición-invariante)
  IVR  intervalos + clase rítmica rclass (ratio de duración cuantizado)
Para n = 3..12:
  tokens (ventanas), tipos distintos, tipos en una sola obra, y
  P_cross(n) = fracción de ventanas cuyo n-grama aparece también en OTRA obra (work_id).

Implementación: cada n-grama se codifica como hash de 64 bits (numpy); por (rep, n) se ordena
la tabla (hash, obra) y se cuentan obras distintas por hash.  Memoria acotada (D-22).

Estratos: global y por `period` (P_cross dentro del periodo).  Salida: results/uniqueness.json.

Uso: .venv/bin/python scripts/uniqueness.py [--rest-break 0]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402

NS = list(range(3, 13))
OUT = sl.ROOT / "results" / "uniqueness.json"
P1 = np.uint64(0x9E3779B97F4A7C15)
P2 = np.uint64(0xC2B2AE3D27D4EB4F)


def rclass_vec(d_prev: np.ndarray, d: np.ndarray) -> np.ndarray:
    """rclass vectorizado, mismos umbrales que el piloto."""
    out = np.zeros(len(d), dtype=np.int64)
    ok = (d_prev > 0) & (d > 0)
    r = np.where(ok, d / np.where(d_prev > 0, d_prev, 1.0), 1.0)
    out[ok & (r < 0.4)] = -2
    out[ok & (r >= 0.4) & (r < 0.9)] = -1
    out[ok & (r > 1.1) & (r <= 2.5)] = 1
    out[ok & (r > 2.5)] = 2
    return out


def rolling_hashes(sym: np.ndarray, m: int) -> np.ndarray:
    """Hash de 64 bits de todas las ventanas de longitud m de la secuencia de símbolos."""
    L = len(sym)
    if L < m:
        return np.empty(0, dtype=np.uint64)
    s = sym.astype(np.uint64)
    h = np.zeros(L - m + 1, dtype=np.uint64)
    with np.errstate(over="ignore"):
        for k in range(m):
            h = (h * P1) ^ ((s[k:L - m + 1 + k] + np.uint64(1_000_003)) * P2)
            h ^= h >> np.uint64(29)
    return h


def work_windows(data, rest_break):
    """Para una obra: dict rep -> dict n -> array de hashes de sus ventanas."""
    seqs = sl.sequences(data, rest_break)
    out = {"IV": defaultdict(list), "IVR": defaultdict(list)}
    for seq in seqs:
        arr = np.array(seq, dtype=np.float64)
        ivs = np.diff(arr[:, 0]).astype(np.int64) + 200          # símbolos >= 0
        rcs = rclass_vec(arr[:-1, 1], arr[1:, 1]) + 2
        ivr = ivs * 8 + rcs                                        # símbolo conjunto
        for n in NS:
            m = n - 1
            if len(ivs) < m:
                continue
            out["IV"][n].append(rolling_hashes(ivs, m))
            out["IVR"][n].append(rolling_hashes(ivr, m))
    return {rep: {n: (np.concatenate(v) if v else np.empty(0, dtype=np.uint64)) for n, v in d.items()}
            for rep, d in out.items()}


def curve(hashes: np.ndarray, work_idx: np.ndarray) -> dict:
    """tokens, tipos, tipos únicos y P_cross de una tabla (hash, obra)."""
    tok = len(hashes)
    if tok == 0:
        return {"tokens": 0, "types": 0, "unique_types": 0, "p_cross": None}
    order = np.lexsort((work_idx, hashes))
    h, w = hashes[order], work_idx[order]
    new_h = np.r_[True, h[1:] != h[:-1]]
    type_id = np.cumsum(new_h) - 1
    ntypes = int(type_id[-1] + 1)
    new_pair = new_h | np.r_[True, w[1:] != w[:-1]]
    works_per_type = np.bincount(type_id[new_pair], minlength=ntypes)
    shared = works_per_type >= 2
    tokens_per_type = np.bincount(type_id, minlength=ntypes)
    return {"tokens": int(tok), "types": ntypes, "unique_types": int((~shared).sum()),
            "p_cross": float(tokens_per_type[shared].sum() / tok)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rest-break", type=float, default=0.0)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    works = sl.load_catalog(exclude_target=True)
    wids = sorted(works)
    print(f"obras: {len(wids)}", flush=True)
    # tablas por (rep, n): listas de arrays de hashes y de índices de obra
    tables = {rep: {n: ([], []) for n in NS} for rep in ("IV", "IVR")}
    period_of = {}
    t0 = time.time()
    nworks = 0
    for i, wid in enumerate(wids):
        data = sl.load_work(wid)
        if data is None:
            continue
        ww = work_windows(data, args.rest_break)
        del data
        if not ww["IV"]:
            continue
        period_of[nworks] = works[wid]["period"]
        for rep in ("IV", "IVR"):
            for n in NS:
                h = ww[rep].get(n)
                if h is None or len(h) == 0:
                    continue
                tables[rep][n][0].append(h)
                tables[rep][n][1].append(np.full(len(h), nworks, dtype=np.int32))
        nworks += 1
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(wids)}  {(time.time()-t0)/60:.1f} min", flush=True)

    per = np.array([period_of[k] for k in range(nworks)])
    out = {"works": nworks, "rest_break": args.rest_break, "ns": NS, "curve": {}, "curve_by_period": {}}
    for rep in ("IV", "IVR"):
        out["curve"][rep] = []
        for n in NS:
            hs, ws = tables[rep][n]
            H = np.concatenate(hs) if hs else np.empty(0, dtype=np.uint64)
            W = np.concatenate(ws) if ws else np.empty(0, dtype=np.int32)
            c = curve(H, W)
            c["n"] = n
            out["curve"][rep].append(c)
            for p in sl.PERIODS:
                sel = np.isin(W, np.where(per == p)[0])
                cp = curve(H[sel], W[sel])
                cp["n"] = n
                out["curve_by_period"].setdefault(rep, {}).setdefault(p, []).append(cp)
            print(f"{rep} n={n:2d} tokens={c['tokens']:,} tipos={c['types']:,} P_cross={c['p_cross']:.4f}", flush=True)
            tables[rep][n] = ([], [])
    out["works_by_period"] = {p: int((per == p).sum()) for p in sl.PERIODS}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"guardado en {args.out} ({(time.time()-t0)/60:.1f} min)")


if __name__ == "__main__":
    sys.exit(main())
