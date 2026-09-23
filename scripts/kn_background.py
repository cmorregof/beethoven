"""Fondo Kneser-Ney interpolado, fondo jerárquico y frecuencia documental (D-38 → D-39/D-40).

Símbolos: s = (intervalo + 200)·8 + (rclass + 2), los mismos de uniqueness.py.  Una ventana de
n notas es un m-grama de símbolos con m = n − 1.  «Órdenes 1..n» del brief = órdenes de
símbolo 1..m.

Tablas (`build`): por estrato y orden j = 1..11, un parquet con una fila por (grama, obra):
gram (uint64), prefix (hash del (j−1)-grama inicial), suffix (hash del (j−1)-grama final),
work (int32, índice en meta.json), count (ventanas de esa obra).  El recuento documental
d(g) es el número de filas de g.  De ahí salen, para cualquier subconjunto de obras
(inclusión: modelo de compositor; exclusión: estrato sin A ni B):
  c_j(g), N1+(p •) seguidores distintos, N1+(• g) predecesores distintos, N1+(• p •).

p_KN(q) = Π_k p(s_k | s_1..s_{k−1}); cada condicional es un KN interpolado de orden k con
descuento absoluto D_j = n1/(n1 + 2·n2) (n1, n2 del estrato completo; aproximación),
recuentos crudos en el orden superior, de continuación en los inferiores y uniforme
1/(V1 + 1) al fondo.

DF_q = d(q)/N_obras para gramas vistos; para no vistos, back-off KN sobre recuentos documentales
(cada obra aporta cada grama una vez): min(1/(N_obras+1), p_KN^doc(q)·N_1^doc/N_obras).

Jerárquico (D-39): p = λ·p_KN[obras del compositor de B sin B](q) + (1−λ)·p_KN[estrato sin
los compositores de A y B](q); λ por interpolación borrada sobre el 20 % de obras de reserva.

Uso:  .venv/bin/python scripts/kn_background.py build | lambda | calibrate | all
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import OrderedDict, defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402
import uniqueness as un  # noqa: E402
import background as bgl  # noqa: E402  (Laplace: cota superior)

MAX_ORDER = 11                       # n = 12 notas
STRATA = bgl.STRATA
OUT = sl.ROOT / "results" / "background_kn"
RES = sl.ROOT / "results"
FIG = RES / "fig"
SEED = 20260903
CAL_STRATUM = "1750-1830"
CAL_N = 8
HOLDOUT_FRAC = 0.20
LAMBDA_GRID = np.round(np.arange(0.0, 1.0001, 0.05), 2)
ZERO = np.uint64(0)


def symbols_of(seq_arr: np.ndarray):
    """(símbolos, intervalos, rclass) de una secuencia [n,3] (midi, ql, offset)."""
    ivs = np.diff(seq_arr[:, 0]).astype(np.int64)
    rcs = un.rclass_vec(seq_arr[:-1, 1], seq_arr[1:, 1])
    return (ivs + 200) * 8 + (rcs + 2), ivs, rcs


def order_hashes(sym: np.ndarray, j: int) -> np.ndarray:
    return un.rolling_hashes(np.asarray(sym), j)


# ----------------------------------------------------------------------------
# construcción de tablas
# ----------------------------------------------------------------------------
def build(rest_break=0.0):
    works = sl.load_catalog(exclude_target=True)
    wl = sorted(works)
    widx = {w: i for i, w in enumerate(wl)}
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"seed": SEED, "rest_break": rest_break, "max_order": MAX_ORDER, "works": wl,
            "composer": {w: works[w]["composer_id"] for w in wl},
            "period": {w: works[w]["period"] for w in wl}, "strata": STRATA, "tables": {}}
    acc = {(s, j): [] for s in STRATA for j in range(1, MAX_ORDER + 1)}
    t0 = time.time()
    for i, wid in enumerate(wl):
        strata = [s for s, ps in STRATA.items() if works[wid]["period"] in ps]
        if not strata:
            continue
        d = sl.load_work(wid)
        if d is None:
            continue
        seqs = sl.sequences(d, rest_break)
        del d
        per_order = defaultdict(list)
        for seq in seqs:
            sym, _, _ = symbols_of(np.array(seq, dtype=np.float64))
            H = {}
            for j in range(1, MAX_ORDER + 1):
                if len(sym) < j:
                    break
                H[j] = order_hashes(sym, j)
                g = H[j]
                if j == 1:
                    pre = suf = np.zeros(len(g), dtype=np.uint64)
                else:
                    pre = H[j - 1][:len(g)]
                    suf = H[j - 1][1:len(g) + 1]
                per_order[j].append(np.stack([g, pre, suf], axis=1))
        for j, parts in per_order.items():
            A = np.concatenate(parts)
            ug, first, cnt = np.unique(A[:, 0], return_index=True, return_counts=True)
            rows = np.column_stack([ug, A[first, 1], A[first, 2]])
            for s in strata:
                acc[(s, j)].append((rows, np.full(len(ug), widx[wid], dtype=np.int32), cnt.astype(np.int32)))
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(wl)} {(time.time()-t0)/60:.1f} min", flush=True)
    for (s, j), parts in acc.items():
        if not parts:
            continue
        rows = np.concatenate([p[0] for p in parts])
        wk = np.concatenate([p[1] for p in parts])
        cnt = np.concatenate([p[2] for p in parts])
        order = np.lexsort((wk, rows[:, 0]))
        g = rows[order, 0]
        tbl = pa.table({"gram": pa.array(g, pa.uint64()), "prefix": pa.array(rows[order, 1], pa.uint64()),
                        "suffix": pa.array(rows[order, 2], pa.uint64()), "work": pa.array(wk[order], pa.int32()),
                        "count": pa.array(cnt[order], pa.int32())})
        pq.write_table(tbl, OUT / f"{s}_o{j}.parquet", compression="zstd")
        newg = np.r_[True, g[1:] != g[:-1]]
        gc = np.add.reduceat(cnt[order], np.nonzero(newg)[0])
        meta["tables"][f"{s}_o{j}"] = {"rows": int(len(g)), "N": int(cnt.sum()), "V": int(newg.sum()),
                                      "n1": int((gc == 1).sum()), "n2": int((gc == 2).sum()),
                                      "works": int(len(np.unique(wk)))}
        print(f"{s:10s} o={j:2d} filas={len(g):,} N={int(cnt.sum()):,} V={int(newg.sum()):,}", flush=True)
        acc[(s, j)] = []
    (OUT / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    print(f"tablas en {OUT} ({(time.time()-t0)/60:.1f} min)")


# ----------------------------------------------------------------------------
# recuentos agregados por grama con índices por prefijo y sufijo
# ----------------------------------------------------------------------------
class ArrayCounts:
    """Recuentos de un orden: gramas únicos ordenados, recuento, prefijo, sufijo, índices."""

    def __init__(self, ug, uc, upre, usuf, D):
        self.ug, self.uc, self.upre, self.usuf, self.D = ug, uc, upre, usuf, D
        self.by_pre = np.argsort(upre, kind="stable")
        self.pre_sorted = upre[self.by_pre]
        self.by_suf = np.argsort(usuf, kind="stable")
        self.suf_sorted = usuf[self.by_suf]
        self.N = int(uc.sum())
        self.V = int(len(ug))

    @classmethod
    def from_rows(cls, g, pre, suf, c, D):
        """g ordenado por grama (filas por (grama, obra)); agrega por grama."""
        if len(g) == 0:
            e = np.empty(0, dtype=np.uint64)
            return cls(e, np.empty(0, dtype=np.int64), e, e, D)
        starts = np.r_[0, np.nonzero(g[1:] != g[:-1])[0] + 1]
        return cls(g[starts], np.add.reduceat(c, starts).astype(np.int64), pre[starts], suf[starts], D)

    def count(self, g):
        k = np.searchsorted(self.ug, np.uint64(g))
        if k < len(self.ug) and self.ug[k] == np.uint64(g):
            return int(self.uc[k])
        return 0

    def idx_with_prefix(self, p):
        """Índices (en ug/uc) de los gramas con prefijo p."""
        a = np.searchsorted(self.pre_sorted, np.uint64(p), side="left")
        b = np.searchsorted(self.pre_sorted, np.uint64(p), side="right")
        return self.by_pre[a:b]

    def idx_with_suffix(self, s):
        a = np.searchsorted(self.suf_sorted, np.uint64(s), side="left")
        b = np.searchsorted(self.suf_sorted, np.uint64(s), side="right")
        return self.by_suf[a:b]

    def idx_with_suffixes(self, ss):
        """Índices de los gramas cuyo sufijo está en el array ss (vectorizado)."""
        ss = np.asarray(ss, dtype=np.uint64)
        if len(ss) == 0:
            return np.empty(0, dtype=np.int64)
        a = np.searchsorted(self.suf_sorted, ss, side="left")
        b = np.searchsorted(self.suf_sorted, ss, side="right")
        ln = b - a
        tot = int(ln.sum())
        if tot == 0:
            return np.empty(0, dtype=np.int64)
        starts = np.repeat(a - np.r_[0, np.cumsum(ln)[:-1]], ln)
        return self.by_suf[starts + np.arange(tot)]

    def grams_with_prefix(self, p):
        return self.ug[self.idx_with_prefix(p)]

    def grams_with_suffix(self, s):
        return self.ug[self.idx_with_suffix(s)]


class Sub:
    """Recuentos a restar de un orden: gramas ordenados (uint64) y recuento (int64)."""

    __slots__ = ("g", "c", "total")

    def __init__(self, g=None, c=None):
        self.g = np.empty(0, dtype=np.uint64) if g is None else np.asarray(g, dtype=np.uint64)
        self.c = np.empty(0, dtype=np.int64) if c is None else np.asarray(c, dtype=np.int64)
        self.total = int(self.c.sum())

    def __bool__(self):
        return len(self.g) > 0

    def lookup(self, gs):
        """Recuento a restar para cada grama de gs (0 si no está)."""
        gs = np.asarray(gs, dtype=np.uint64)
        if len(self.g) == 0 or len(gs) == 0:
            return np.zeros(len(gs), dtype=np.int64)
        k = np.minimum(np.searchsorted(self.g, gs), len(self.g) - 1)
        return np.where(self.g[k] == gs, self.c[k], 0)


class Counts:
    """Modelo de recuentos multi-orden con exclusión opcional de obras (por sustracción).
    base[j]: ArrayCounts del conjunto incluido; sub[j]: Sub (arrays) con lo que se resta.
    Todo vectorizado sobre NumPy: ningún dict de Python del tamaño del corpus."""

    CACHE_MAX = 200_000

    def __init__(self, base: dict[int, ArrayCounts], sub: dict[int, Sub] | None = None):
        self.base = base
        self.sub = sub or {j: Sub() for j in base}
        for j in base:
            self.sub.setdefault(j, Sub())
        self.N = {j: b.N - self.sub[j].total for j, b in base.items()}
        self.V = {}
        for j, b in base.items():
            s = self.sub[j]
            if s:
                k = np.searchsorted(b.ug, s.g)
                k = np.minimum(k, len(b.ug) - 1)
                bc = np.where(b.ug[k] == s.g, b.uc[k], 0)
                zeroed = int((s.c >= bc).sum())
            else:
                zeroed = 0
            self.V[j] = b.V - zeroed
        self._cache = OrderedDict()

    def _get(self, k):
        v = self._cache.get(k)
        if v is not None:
            self._cache.move_to_end(k)
        return v

    def _put(self, k, v):
        self._cache[k] = v
        if len(self._cache) > self.CACHE_MAX:
            self._cache.popitem(last=False)
        return v

    def D(self, j):
        return self.base[j].D

    def count(self, j, g):
        if j not in self.base:
            return 0
        b = self.base[j]
        c = b.count(g)
        if c and self.sub[j]:
            c -= int(self.sub[j].lookup(np.array([g], dtype=np.uint64))[0])
        return c

    def _counts_at(self, j, idx):
        """Recuentos netos de los gramas base[j].ug[idx]."""
        b = self.base[j]
        c = b.uc[idx]
        if self.sub[j] and len(idx):
            c = c - self.sub[j].lookup(b.ug[idx])
        return c

    def followers(self, j, p):
        """N1+(p •): j-gramas distintos con prefijo p y recuento > 0."""
        k = ("f", j, int(p))
        v = self._get(k)
        if v is None:
            if j not in self.base:
                v = 0
            else:
                idx = self.base[j].idx_with_prefix(p)
                v = int((self._counts_at(j, idx) > 0).sum()) if len(idx) else 0
            self._put(k, v)
        return v

    def cont(self, j, g):
        """N1+(• g): (j+1)-gramas distintos con sufijo g y recuento > 0."""
        k = ("c", j, int(g))
        v = self._get(k)
        if v is None:
            if j + 1 not in self.base:
                v = 0
            else:
                idx = self.base[j + 1].idx_with_suffix(g)
                v = int((self._counts_at(j + 1, idx) > 0).sum()) if len(idx) else 0
            self._put(k, v)
        return v

    def cont_sum(self, j, p):
        """N1+(• p •) = Σ_{g de orden j con prefijo p, c(g)>0} N1+(• g)."""
        k = ("s", j, int(p))
        v = self._get(k)
        if v is None:
            if j not in self.base or j + 1 not in self.base:
                v = 0
            else:
                b = self.base[j]
                idx = b.idx_with_prefix(p)
                if len(idx) == 0:
                    v = 0
                else:
                    gs = b.ug[idx][self._counts_at(j, idx) > 0]
                    idx2 = self.base[j + 1].idx_with_suffixes(gs)
                    v = int((self._counts_at(j + 1, idx2) > 0).sum()) if len(idx2) else 0
            self._put(k, v)
        return v


class Tables:
    """Tablas de un estrato en memoria: filas por (grama, obra) y agregados por orden."""

    def __init__(self, stratum: str):
        self.stratum = stratum
        self.meta = json.loads((OUT / "meta.json").read_text())
        self.works = self.meta["works"]
        self.composer = self.meta["composer"]
        self.rows, self.tok, self.doc = {}, {}, {}
        for j in range(1, MAX_ORDER + 1):
            p = OUT / f"{stratum}_o{j}.parquet"
            if not p.exists():
                continue
            t = pq.read_table(p)
            r = {"g": t["gram"].to_numpy(), "pre": t["prefix"].to_numpy(), "suf": t["suffix"].to_numpy(),
                 "w": t["work"].to_numpy(), "c": t["count"].to_numpy().astype(np.int64)}
            r["by_work"] = np.argsort(r["w"], kind="stable")
            r["work_sorted"] = r["w"][r["by_work"]]
            m = self.meta["tables"][f"{stratum}_o{j}"]
            D = m["n1"] / (m["n1"] + 2 * m["n2"]) if (m["n1"] + 2 * m["n2"]) else 0.5
            r["D"] = D
            self.rows[j] = r
            self.tok[j] = ArrayCounts.from_rows(r["g"], r["pre"], r["suf"], r["c"], D)
            self.doc[j] = ArrayCounts.from_rows(r["g"], r["pre"], r["suf"], np.ones(len(r["g"]), dtype=np.int64), D)

    def _rows_of(self, j, wset):
        r = self.rows[j]
        out = []
        for w in wset:
            a = np.searchsorted(r["work_sorted"], w, side="left")
            b = np.searchsorted(r["work_sorted"], w, side="right")
            if b > a:
                out.append(r["by_work"][a:b])
        return np.concatenate(out) if out else np.empty(0, dtype=np.int64)

    def subset_counts(self, wset: set[int], doc=False) -> Counts:
        """Modelo construido solo con las obras de wset (modelo de compositor)."""
        base = {}
        for j, r in self.rows.items():
            idx = self._rows_of(j, wset)
            if len(idx) == 0:
                continue
            idx = idx[np.argsort(r["g"][idx], kind="stable")]
            c = np.ones(len(idx), dtype=np.int64) if doc else r["c"][idx]
            base[j] = ArrayCounts.from_rows(r["g"][idx], r["pre"][idx], r["suf"][idx], c, r["D"])
        return Counts(base)

    def minus_counts(self, excl: set[int], doc=False) -> Counts:
        """Estrato completo menos las obras de excl (estrato sin A ni B)."""
        sub = {}
        for j, r in self.rows.items():
            idx = self._rows_of(j, excl)
            if len(idx) == 0:
                sub[j] = Sub()
                continue
            g = r["g"][idx]
            c = np.ones(len(idx), dtype=np.int64) if doc else r["c"][idx]
            order = np.argsort(g, kind="stable")
            g, c = g[order], c[order]
            starts = np.r_[0, np.nonzero(g[1:] != g[:-1])[0] + 1]
            sub[j] = Sub(g[starts], np.add.reduceat(c, starts))
        return Counts(self.doc if doc else self.tok, sub)


# ----------------------------------------------------------------------------
# Kneser-Ney interpolado
# ----------------------------------------------------------------------------
class KN:
    def __init__(self, cn: Counts):
        self.cn = cn
        self.V1 = max(cn.V.get(1, 0), 1)
        self.uniform = 1.0 / (self.V1 + 1)

    def _lower(self, j, suf, sufpre):
        """Nivel de continuación de orden j para el sufijo suf[j] con prefijo sufpre[j]."""
        if j == 0:
            return self.uniform
        cn = self.cn
        D = cn.D(j)
        g = suf[j]
        if j == 1:
            den = cn.V.get(2, 0)                       # N1+(• •) = bigramas distintos
            if den == 0:
                return self.uniform
            return max(cn.cont(1, g) - D, 0) / den + D * cn.V.get(1, 0) / den * self.uniform
        p = sufpre[j]
        den = cn.cont_sum(j, p)
        lower = self._lower(j - 1, suf, sufpre)
        if den == 0:
            return lower
        return max(cn.cont(j, g) - D, 0) / den + D * cn.followers(j, p) / den * lower

    def prob(self, sym, window=True) -> float:
        """p_KN(q) = Π_k p(s_k | s_1..s_{k−1}) de una ventana de símbolos.
        window=True: probabilidad por ventana de orden m (× N_1/N_m), porque la cadena telescopa a
        c_m(q)/N_1 (posiciones de símbolo) y el E-value multiplica por ventanas de orden m."""
        sym = np.asarray(sym)
        m = len(sym)
        H = {j: order_hashes(sym, j) for j in range(1, m + 1)}
        cn = self.cn
        lp = 0.0
        for k in range(1, m + 1):
            g = int(H[k][0])
            if k == 1:
                N = cn.N.get(1, 0)
                D = cn.D(1)
                p = (max(cn.count(1, g) - D, 0) / N + D * cn.V.get(1, 0) / N * self.uniform) if N else self.uniform
            else:
                suf = {i: int(H[i][k - i]) for i in range(1, k)}          # sufijo de orden i: s_{k-i+1..k}
                sufpre = {i: int(H[i - 1][k - i]) for i in range(2, k)}   # su prefijo (i-1)-grama
                ctx = int(H[k - 1][0])
                c_ctx = cn.count(k - 1, ctx)
                lower = self._lower(k - 1, suf, sufpre)
                if c_ctx == 0:
                    p = lower
                else:
                    D = cn.D(k)
                    p = max(cn.count(k, g) - D, 0) / c_ctx + D * cn.followers(k, ctx) / c_ctx * lower
            lp += np.log(max(p, 1e-300))
        p = float(np.exp(lp))
        if window and m in cn.N and cn.N[m] > 0:
            p *= cn.N[1] / cn.N[m]
        return p


# ----------------------------------------------------------------------------
# API de alto nivel
# ----------------------------------------------------------------------------
class Models:
    """Modelos de un estrato: Laplace (cota superior), KN estrato-sin-(A,B), jerárquico, DF."""

    def __init__(self, stratum: str, n: int, lam: float | None = None, tables: Tables | None = None):
        self.stratum, self.n, self.m = stratum, n, n - 1
        self.T = tables if tables is not None else Tables(stratum)   # Tables no depende de n: compartible
        self.lap = bgl.Background.load(stratum, n)
        self.lam = lam
        self._minus, self._subset = OrderedDict(), OrderedDict()
        self.MODEL_CACHE = 4                # modelos vivos a la vez por tipo (LRU)
        works = sl.load_catalog(exclude_target=True)
        self.widx = {w: i for i, w in enumerate(self.T.works)}
        self.comp_works = defaultdict(set)
        for w in self.T.works:
            if works.get(w, {}).get("period") in STRATA[stratum]:
                self.comp_works[self.T.composer[w]].add(self.widx[w])
        self.n_works = sum(len(v) for v in self.comp_works.values())

    def _lru(self, cache, key, make):
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        cache[key] = v = make()
        while len(cache) > self.MODEL_CACHE:
            cache.popitem(last=False)
        return v

    def minus(self, excl: set[int], doc=False) -> KN:
        key = (frozenset(excl), doc)
        return self._lru(self._minus, key, lambda: KN(self.T.minus_counts(excl, doc)))

    def subset(self, incl: set[int], doc=False) -> KN:
        key = (frozenset(incl), doc)
        return self._lru(self._subset, key, lambda: KN(self.T.subset_counts(incl, doc)))

    def excl_of(self, cA, cB):
        return self.comp_works.get(cA, set()) | self.comp_works.get(cB, set())

    def p_laplace(self, sym, cA, cB):
        h = np.array([order_hashes(sym, self.m)[0]], dtype=np.uint64)
        return float(self.lap.p(h, exclude=(cA, cB))[0])

    def p_kn(self, sym, cA, cB):
        return self.minus(self.excl_of(cA, cB)).prob(sym)

    def p_comp(self, sym, cB, wB: int):
        incl = self.comp_works.get(cB, set()) - {wB}
        return self.subset(incl).prob(sym) if incl else None

    def p_hier(self, sym, cA, cB, wB: int, lam=None):
        lam = self.lam if lam is None else lam
        ps = self.p_kn(sym, cA, cB)
        pc = self.p_comp(sym, cB, wB)
        if pc is None or lam is None:
            return ps
        return lam * pc + (1 - lam) * ps

    def df(self, sym, cA, cB):
        """DF_q = fracción de obras del estrato sin A ni B que contienen q (KN documental)."""
        excl = self.excl_of(cA, cB)
        kn = self.minus(excl, doc=True)
        nw = max(self.n_works - len(excl), 1)
        d = kn.cn.count(self.m, int(order_hashes(sym, self.m)[0]))
        if d > 0:
            return d / nw                           # empírica exacta para gramas vistos
        p_doc = kn.prob(sym, window=False)          # back-off KN documental ≈ d_m(q)/N_1^doc
        T1 = kn.cn.N.get(1, 0)
        return min(1.0 / (nw + 1), p_doc * T1 / nw) # un tipo nunca visto en nw obras: DF < 1/(nw+1)


# ----------------------------------------------------------------------------
def work_symbol_windows(wid: str, m: int, rest_break=0.0):
    d = sl.load_work(wid)
    if d is None:
        return []
    out = []
    for seq in sl.sequences(d, rest_break):
        sym, _, _ = symbols_of(np.array(seq, dtype=np.float64))
        for k in range(len(sym) - m + 1):
            out.append(sym[k:k + m])
    return out


def sample_windows(rng, per_work: dict, n_total: int):
    wl = sorted(per_work)
    tok = np.array([len(per_work[w]) for w in wl])
    cum = np.cumsum(tok)
    picks = rng.integers(0, cum[-1], size=n_total)
    wi = np.searchsorted(cum, picks, side="right")
    return [(wl[i], per_work[wl[i]][p - (cum[i - 1] if i > 0 else 0)]) for p, i in zip(picks, wi)]


def estimate_lambda(n=CAL_N, rest_break=0.0, per_work_windows=150):
    """Interpolación borrada (D-39): 20 % de obras de reserva; λ maximiza la log-verosimilitud de
    sus ventanas bajo λ·p_comp(obras de entrenamiento de cB) + (1−λ)·p_KN(entrenamiento sin cB)."""
    rng = np.random.default_rng(SEED)
    M = Models(CAL_STRATUM, n)
    all_w = sorted({w for ws in M.comp_works.values() for w in ws})
    rng.shuffle(all_w)
    hold = set(all_w[:int(round(HOLDOUT_FRAC * len(all_w)))])
    train = set(all_w) - hold
    ll = {float(lam): 0.0 for lam in LAMBDA_GRID}
    n_eval, used = 0, []
    t0 = time.time()
    for wB in sorted(hold):
        wid = M.T.works[wB]
        cB = M.T.composer[wid]
        comp_train = M.comp_works[cB] & train
        if not comp_train:
            continue
        wins = work_symbol_windows(wid, n - 1, rest_break)
        if not wins:
            continue
        sel = rng.choice(len(wins), size=min(per_work_windows, len(wins)), replace=False)
        kn_c = M.subset(comp_train)
        kn_s = M.minus(hold | M.comp_works[cB])
        for k in sel:
            pc, ps = kn_c.prob(wins[k]), kn_s.prob(wins[k])
            for lam in ll:
                ll[lam] += np.log(max(lam * pc + (1 - lam) * ps, 1e-300))
            n_eval += 1
        used.append(wid)
        print(f"  {wid[:42]:42s} {cB:13s} comp={len(comp_train):2d} obras, {len(sel)} ventanas  {(time.time()-t0)/60:.1f} min", flush=True)
    best = max(ll, key=ll.get)
    out = {"n": n, "stratum": CAL_STRATUM, "holdout_frac": HOLDOUT_FRAC, "holdout_works_used": used,
           "n_windows": n_eval, "lambda": best,
           "loglik_per_window": {str(k): v / max(n_eval, 1) for k, v in ll.items()}}
    (RES / f"kn_lambda_n{n}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"λ* = {best}; log-verosimilitud por ventana: " +
          ", ".join(f"λ={k:.2f}: {v/max(n_eval,1):.3f}" for k, v in sorted(ll.items()) if k in (0.0, 0.25, 0.5, 0.75, 1.0, best)))
    return best


def metrics(pred, obs, eps=0.05):
    x, y = np.log(pred + eps), np.log(obs + eps)
    return float(np.polyfit(x, y, 1)[0]), float(np.mean(np.abs(y - x))), float(np.mean(y - x))


def calibrate(n=CAL_N, rest_break=0.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lam_file = RES / f"kn_lambda_n{n}.json"
    lam = json.loads(lam_file.read_text())["lambda"] if lam_file.exists() else None
    M = Models(CAL_STRATUM, n, lam)
    rng = np.random.default_rng(SEED)
    m = n - 1
    works = sl.load_catalog(exclude_target=True)
    wl = sorted(w for w, r in works.items() if r["period"] in STRATA[CAL_STRATUM])
    per_work, hashes = {}, {}
    for wid in wl:
        wins = work_symbol_windows(wid, m, rest_break)
        if wins:
            per_work[wid] = wins
            hashes[wid] = np.array([order_hashes(s, m)[0] for s in wins], dtype=np.uint64)
    queries = sample_windows(rng, per_work, bgl.N_CAL)
    wlist = sorted(per_work)
    rows, pairs_all = [], []
    t0 = time.time()
    for qi, (wa, sym) in enumerate(queries):
        ca = M.T.composer[wa]
        q = np.uint64(order_hashes(sym, m)[0])
        rec = dict(query=qi, work=wa, composer=ca, n_B=0, obs_occ=0, obs_works=0,
                   pred_occ_lap=0.0, pred_occ_kn=0.0, pred_occ_hier=0.0,
                   pred_works_lap=0.0, pred_works_kn=0.0, pred_works_hier=0.0, pred_works_df=0.0)
        cache = {}
        for wb in wlist:
            cb = M.T.composer[wb]
            if cb == ca:
                continue
            if cb not in cache:
                cache[cb] = (M.p_laplace(sym, ca, cb), M.p_kn(sym, ca, cb), M.df(sym, ca, cb))
            pl, pk, dfq = cache[cb]
            ph = M.p_hier(sym, ca, cb, M.widx[wb]) if lam is not None else pk
            tb = len(per_work[wb])
            occ = int((hashes[wb] == q).sum())
            rec["n_B"] += 1
            rec["obs_occ"] += occ
            rec["obs_works"] += 1 if occ else 0
            for name, p in (("lap", pl), ("kn", pk), ("hier", ph)):
                E = tb * p
                rec[f"pred_occ_{name}"] += E
                rec[f"pred_works_{name}"] += 1 - np.exp(-E)
            rec["pred_works_df"] += dfq
            pairs_all.append((qi, wa, wb, dfq, 1 if occ else 0, 1 - np.exp(-tb * ph), 1 - np.exp(-tb * pk)))
        rows.append(rec)
        if (qi + 1) % 20 == 0:
            print(f"  {qi+1}/{len(queries)}  {(time.time()-t0)/60:.1f} min", flush=True)
    with open(RES / "kn_calibration.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(RES / "kn_calibration_pairs.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["query", "work_A", "work_B", "df_pred", "present", "p_present_hier", "p_present_kn"])
        w.writerows(pairs_all)

    obs = np.array([r["obs_occ"] for r in rows], dtype=float)
    obs_w = np.array([r["obs_works"] for r in rows], dtype=float)
    seen = obs > 0
    L = ["# Calibración de los tres fondos (D-40)", "",
         f"Estrato {CAL_STRATUM}, n = {n}, {len(rows)} ventanas muestreadas uniformemente sobre ventanas, "
         f"leave-both-composers-out; λ = {lam}. Métricas sobre log(x + 0,05): pendiente OLS de log(obs) sobre "
         "log(pred), sesgo absoluto medio |log obs − log pred| (MAE), sesgo medio (log obs − log pred). "
         "«vistas» = ventanas con ≥ 1 ocurrencia en otro compositor.", "",
         "| modelo | conjunto | n | pendiente | MAE log | sesgo log | obs/pred total |", "|---|---|---|---|---|---|---|"]
    summary = {}
    for name, label in (("lap", "Laplace (cota superior)"), ("kn", "Kneser-Ney"), ("hier", "jerárquico")):
        pred = np.array([r[f"pred_occ_{name}"] for r in rows])
        for subset, mask in (("todas", np.ones(len(rows), bool)), ("vistas", seen)):
            s, mae, b = metrics(pred[mask], obs[mask])
            summary[(name, subset)] = (s, mae, b)
            L.append(f"| {label} | {subset} | {int(mask.sum())} | {s:.3f} | {mae:.3f} | {b:+.3f} | "
                     f"{obs[mask].sum()/pred[mask].sum():.2f} |")
    L += ["", "## obs/pred por tramo de E predicho (KN), ocurrencias, ventanas vistas", "",
          "| tramo E (KN) | n | Laplace | KN | jerárquico |", "|---|---|---|---|---|"]
    pk = np.array([r["pred_occ_kn"] for r in rows])
    for lo, hi in ((0, 1), (1, 3), (3, 30), (30, 300), (300, 3000), (3000, 1e12)):
        sel = seen & (pk >= lo) & (pk < hi)
        if sel.sum():
            cells = [f"{obs[sel].sum()/np.array([r[f'pred_occ_{k}'] for r in rows])[sel].sum():.2f}" for k in ("lap", "kn", "hier")]
            L.append(f"| [{lo:g}, {hi:g}) | {int(sel.sum())} | " + " | ".join(cells) + " |")
    unseen = ~seen
    L.append("")
    L.append(f"Ventanas no vistas en otro compositor: {int(unseen.sum())} (observado 0); E predicho medio: " +
             ", ".join(f"{lab} {np.array([r[f'pred_occ_{k}'] for r in rows])[unseen].mean():.3f}"
                       for k, lab in (("lap", "Laplace"), ("kn", "KN"), ("hier", "jerárquico"))) + ".")
    # DF a nivel de obra
    P = np.array(pairs_all, dtype=object)
    dfp = P[:, 3].astype(float)
    pres = P[:, 4].astype(float)
    php = P[:, 5].astype(float)
    pkn = P[:, 6].astype(float)
    edges = [0, 1e-4, 1e-3, 1e-2, 0.05, 0.1, 0.2, 0.5, 1.01]
    L += ["", "## DF: presencia en B (pares ventana × obra B)", "",
          f"pares {len(dfp):,}; presencia observada {pres.mean():.4f}; DF media {dfp.mean():.4f}; "
          f"1−e^(−E) KN medio {pkn.mean():.4f}; jerárquico {php.mean():.4f}", "",
          "| bin DF predicho | pares | DF medio | presencia observada | 1−e^(−E) KN | 1−e^(−E) hier |", "|---|---|---|---|---|---|"]
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (dfp >= lo) & (dfp < hi)
        if sel.sum():
            L.append(f"| [{lo:g}, {hi:g}) | {int(sel.sum()):,} | {dfp[sel].mean():.4f} | {pres[sel].mean():.4f} | "
                     f"{pkn[sel].mean():.4f} | {php[sel].mean():.4f} |")
    pw_df = np.array([r["pred_works_df"] for r in rows])
    s_df, mae_df, b_df = metrics(pw_df, obs_w)
    L.append(f"\nA nivel de ventana (número de obras B que contienen q): DF pendiente {s_df:.3f}, MAE log {mae_df:.3f}, "
             f"sesgo {b_df:+.3f}; total predicho {pw_df.sum():.1f} vs observado {obs_w.sum():.0f}.")
    cands = {k[0]: v for k, v in summary.items() if k[1] == "todas" and 0.9 <= v[0] <= 1.1}
    choice = min(cands, key=lambda k: cands[k][1]) if cands else None
    fallback = min((k for k in summary if k[1] == "todas"), key=lambda k: summary[k][1])[0]
    L += ["", "## Regla de selección (D-40)", "",
          "Menor MAE en log entre los modelos con pendiente en [0,9, 1,1] sobre las 200 ventanas → "
          + (f"**{choice}**." if choice else f"ningún modelo cumple la pendiente; el de menor MAE es **{fallback}**.")]
    (RES / "kn_calibration.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    json.dump({"lambda": lam, "summary": {f"{k[0]}|{k[1]}": v for k, v in summary.items()}, "choice": choice,
               "fallback": fallback}, open(RES / "kn_calibration.json", "w"), indent=1)
    print("\n".join(L))
    # figura
    fig, axes = plt.subplots(1, 4, figsize=(21, 5.2))
    eps = 0.05
    for ax, (name, label) in zip(axes[:3], (("lap", "Laplace"), ("kn", "Kneser-Ney"), ("hier", f"jerárquico λ={lam}"))):
        pred = np.array([r[f"pred_occ_{name}"] for r in rows])
        ax.scatter(pred + eps, obs + eps, s=14, alpha=0.5, color="#4c72b0")
        order = np.argsort(pred)
        bins = np.array_split(order, 10)
        ax.plot([pred[b].mean() + eps for b in bins], [obs[b].mean() + eps for b in bins], "o-", color="#c44e52", label="media por decil")
        lim = [eps * 0.8, max(pred.max(), obs.max()) * 1.5]
        ax.plot(lim, lim, "k--", lw=1)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
        s, mae, b = summary[(name, "todas")]
        ax.set_title(f"{label}: pendiente {s:.2f}, MAE log {mae:.2f}", fontsize=10)
        ax.set_xlabel("E predicho (ocurrencias en B, +0,05)"); ax.set_ylabel("observado (+0,05)")
        ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax = axes[3]
    for arr, lab, st in ((dfp, "DF (KN documental)", "o-"), (pkn, "1−e^(−E) KN", "s--"), (php, "1−e^(−E) jerárquico", "^:")):
        xs, ys = [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            sel = (arr >= lo) & (arr < hi)
            if sel.sum() >= 20:
                xs.append(arr[sel].mean()); ys.append(max(pres[sel].mean(), 1e-5))
        ax.plot(xs, ys, st, label=lab)
    ax.plot([1e-5, 1], [1e-5, 1], "k--", lw=1)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("presencia predicha en B"); ax.set_ylabel("presencia observada (fracción de pares)")
    ax.set_title("presencia en B: fiabilidad por bins", fontsize=10); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.suptitle(f"Calibración de fondos, estrato {CAL_STRATUM}, n={n}, leave-both-composers-out")
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "background_calibration_models.png", dpi=150)
    print(f"figura en {FIG / 'background_calibration_models.png'}  ({(time.time()-t0)/60:.1f} min)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "lambda", "calibrate", "all"])
    ap.add_argument("--n", type=int, default=CAL_N)
    ap.add_argument("--rest-break", type=float, default=0.0)
    args = ap.parse_args()
    if args.cmd in ("build", "all"):
        build(args.rest_break)
    if args.cmd in ("lambda", "all"):
        estimate_lambda(args.n, args.rest_break)
    if args.cmd in ("calibrate", "all"):
        calibrate(args.n, args.rest_break)


if __name__ == "__main__":
    main()
