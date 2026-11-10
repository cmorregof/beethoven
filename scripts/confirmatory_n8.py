"""Test confirmatorio D-41 (n = 8) con el nulo de fragmentos de igual longitud propuesto en D-43.

ESTE SCRIPT NO SE EJECUTA SOBRE LOS OBJETIVOS SIN DESBLOQUEO EXPLÍCITO DEL USUARIO.
Por defecto la guardia del preregistro (`preregistration_guard.py`) aborta ante Beethoven op. 67
o cualquier obra de Cherubini. La ejecución real exige a la vez:
  --run-confirmatory, --d43-commit <hash del commit que registra D-43> y la variable de entorno
  D41_CONFIRMATORY_UNLOCK=user-approved.
Sin las tres, cualquier identificador objetivo aborta con PreregistrationViolation (código 3).

Diseño (D-41, `decisions/D-41_preregistro.md`; D-43, `paper/D-43_borrador.md`):
  instancia   = tipo de ventana de 8 notas (7-grama de símbolos intervalo + clase rítmica, D-39),
                misma simbolización que `thresholds_n8.windows_with_movement` (rest_break 0).
  estadístico = K(X, B) = número de tipos de X presentes en B con DF ≤ t_DF, con la regla de
                exclusión de D-37 por par: para A, sin el compositor de A ni el de B; para cada
                réplica A′, sin el compositor de A′ ni el de B (S_B se precalcula por compositor).
  longitud    = L(A) = ventanas de 8 notas de A tras colapso de dobladas sobre el fragmento (D-13).
  nulo        = R = 1000 fragmentos A′ (D-43 b) de la piscina de ese fragmento (paper/D-43_null_pool.csv,
                columna `fragments`): barra de inicio uniforme sobre todas las barras de la piscina,
                compases completos y todas las partes hasta L(A′) ∈ [0,95·L(A), 1,05·L(A)] (si no,
                se resortea; se informa la tasa de rechazo); colapso de dobladas por fragmento;
                B′ = B. Generador default_rng([20260903, k]), k = 1 para A1 y 2 para A2.
                Alternativa declarada: emparejar por duración en negras (--measure quarters).
  p           = fracción de réplicas con K(A′) ≥ K(A) (D-41); se informa también (1 + #)/(1 + R).
  Bonferroni  sobre el número de fragmentos.
  secundario  = exclusión común para A y A′ ({compositor de B} ∪ compositores de la piscina), D-43 (e).
  confirmación= algún fragmento con p corregido ≤ 0,05 y, en ese mismo fragmento, al menos un tipo
                compartido con DF ≤ t_DF y ritmo no uniforme (D-38).
  ranking por E (menor primero) solo informativo.
t_DF y t_E se leen de results/thresholds_n8.json; no se recalculan.

Las funciones de cálculo son puras (ventanas y funciones DF/E inyectadas) y se prueban con datos
sintéticos en tests/test_confirmatory_n8.py. La carga de datos reales importa seqlib/kn_background
desde $BEETHOVEN_ROOT/scripts (por defecto, la raíz del repo de este script).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import preregistration_guard as guard  # noqa: E402

N, LAM, STRATUM = 8, 0.45, "1750-1830"
M_ORD = N - 1
SEED = 20260903
N_NULL = 1000
ALPHA = 0.05
UNLOCK_ENV = "D41_CONFIRMATORY_UNLOCK"
UNLOCK_VALUE = "user-approved"
TARGET_B = "musedata_beethoven-bhl-orch-sym5"
HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")


class ConfirmatoryLocked(SystemExit):
    """El desbloqueo está incompleto: no se corre nada."""

    def __init__(self, msg: str):
        super().__init__(4)
        self.msg = msg

    def __str__(self) -> str:
        return self.msg


# ----------------------------------------------------------------------------
# estructura de ventanas
# ----------------------------------------------------------------------------
@dataclass
class WorkWindows:
    """Ventanas de 8 notas de una obra, en orden temporal (movimiento, ataque, voz)."""
    work_id: str
    composer: str
    hashes: np.ndarray                    # uint64 [n]
    syms: np.ndarray                      # int64 [n, M_ORD]
    mov: np.ndarray                       # int [n]
    onset: np.ndarray                     # float [n]
    voice: np.ndarray                     # int [n]
    n_bars: int | None = None             # compases con algún ataque (None si no hay bar_remaining)
    meta: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.hashes)


def symbols_from_arr(arr: np.ndarray) -> np.ndarray:
    """Símbolos (intervalo + 200)·8 + (rclass + 2) de una secuencia [n, ≥3] (midi, ql, offset).
    Idéntico a kn_background.symbols_of; aquí sin dependencias para los tests."""
    midi, ql = arr[:, 0], arr[:, 1]
    ivs = np.diff(midi).astype(np.int64)
    dp, d = ql[:-1], ql[1:]
    rc = np.zeros(len(d), dtype=np.int64)
    ok = (dp > 0) & (d > 0)
    r = np.where(ok, d / np.where(dp > 0, dp, 1.0), 1.0)
    rc[ok & (r < 0.4)] = -2
    rc[ok & (r >= 0.4) & (r < 0.9)] = -1
    rc[ok & (r > 1.1) & (r <= 2.5)] = 1
    rc[ok & (r > 2.5)] = 2
    return (ivs + 200) * 8 + (rc + 2)


_P1 = np.uint64(0x9E3779B97F4A7C15)   # mismas constantes que uniqueness.py
_P2 = np.uint64(0xC2B2AE3D27D4EB4F)


def rolling_hashes_local(sym: np.ndarray, m: int) -> np.ndarray:
    """Hash de respaldo para tests (en datos reales se usa kn_background.order_hashes)."""
    L = len(sym)
    if L < m:
        return np.empty(0, dtype=np.uint64)
    s = np.asarray(sym).astype(np.uint64)
    h = np.zeros(L - m + 1, dtype=np.uint64)
    with np.errstate(over="ignore"):
        for k in range(m):
            h = (h * _P1) ^ ((s[k:L - m + 1 + k] + np.uint64(1_000_003)) * _P2)
            h ^= h >> np.uint64(29)
    return h


def count_bars(seqs: Iterable[tuple]) -> int | None:
    """Compases con algún ataque: fin de compás = offset + bar_remaining, distintos por movimiento."""
    ends: set[tuple[int, float]] = set()
    any_br = False
    for mv, _v, arr in seqs:
        if arr.shape[1] < 4:
            continue
        br = arr[:, 3]
        ok = br >= 0
        if ok.any():
            any_br = True
            for e in np.round(arr[ok, 2] + br[ok], 3):
                ends.add((int(mv), float(e)))
    return len(ends) if any_br else None


def windows_from_sequences(seqs: Sequence[tuple], work_id: str, composer: str,
                           symbols_fn: Callable = symbols_from_arr,
                           hash_fn: Callable = rolling_hashes_local, m: int = M_ORD) -> WorkWindows:
    """seqs = [(movimiento, voz, arr[n, ≥3] con columnas midi, ql, offset[, bar_remaining])]."""
    H, S, MV, ON, VC = [], [], [], [], []
    for mv, v, arr in seqs:
        sym = np.asarray(symbols_fn(arr[:, :3]), dtype=np.int64)
        if len(sym) < m:
            continue
        h = np.asarray(hash_fn(sym, m), dtype=np.uint64)
        nw = len(sym) - m + 1
        idx = np.arange(nw)[:, None] + np.arange(m)[None, :]
        H.append(h); S.append(sym[idx])
        MV.append(np.full(nw, int(mv))); VC.append(np.full(nw, int(v)))
        ON.append(np.asarray(arr[:nw, 2], dtype=np.float64))
    if not H:
        e = np.empty(0)
        return WorkWindows(work_id, composer, e.astype(np.uint64), np.empty((0, m), np.int64),
                           e.astype(int), e, e.astype(int), count_bars(seqs))
    h, s, mv, on, vc = (np.concatenate(x) for x in (H, S, MV, ON, VC))
    order = np.lexsort((vc, on, mv))
    return WorkWindows(work_id, composer, h[order], s[order], mv[order], on[order], vc[order], count_bars(seqs))


# ----------------------------------------------------------------------------
# estadístico
# ----------------------------------------------------------------------------
def uniform_rhythm(sym: np.ndarray) -> bool:
    """Ritmo uniforme = todas las clases rítmicas 0 (D-38, como thresholds_n8)."""
    rcs = np.asarray(sym) % 8 - 2
    return bool(np.all(rcs == 0))


def type_index(ww: WorkWindows) -> dict[int, int]:
    """hash -> índice de la primera ventana con ese tipo."""
    u, first = np.unique(ww.hashes, return_index=True)
    return {int(h): int(i) for h, i in zip(u, first)}


def pass_set(ww_B: WorkWindows, df_fn: Callable[[np.ndarray], float], t_df: float):
    """DF de cada tipo de B y conjunto S_B de tipos con DF ≤ t_df.
    Devuelve (dict hash -> DF, np.ndarray uint64 ordenado de S_B)."""
    dfs = {}
    for h, i in type_index(ww_B).items():
        dfs[h] = float(df_fn(ww_B.syms[i]))
    S = np.array(sorted(h for h, d in dfs.items() if d <= t_df), dtype=np.uint64)
    return dfs, S


def count_statistic(hashes_A: np.ndarray, S_B: np.ndarray) -> int:
    """Número de tipos distintos de A presentes en S_B."""
    if len(hashes_A) == 0 or len(S_B) == 0:
        return 0
    return int(np.isin(np.unique(np.asarray(hashes_A, dtype=np.uint64)), S_B, assume_unique=True).sum())


def shared_passing(ww_A: WorkWindows, ww_B: WorkWindows, dfs_B: Mapping[int, float], t_df: float):
    """Tipos de A presentes en B: lista de dicts (hash, sym, DF, pasa, ritmo uniforme)."""
    ia, ib = type_index(ww_A), type_index(ww_B)
    out = []
    for h in sorted(set(ia) & set(ib)):
        sym = ww_A.syms[ia[h]]
        d = dfs_B[h]
        out.append(dict(hash=h, sym=sym, DF=d, pass_DF=d <= t_df, uniform_rhythm=uniform_rhythm(sym)))
    return out


# ----------------------------------------------------------------------------
# fragmentos y emparejamiento de longitud
# ----------------------------------------------------------------------------
def length_in_windows(ww: WorkWindows, length: float, unit: str) -> int:
    """Longitud expresada en número total de ventanas de 8 notas (todas las voces).
    unit = "windows": tal cual; unit = "bars": length × (ventanas por compás de ww)."""
    if unit == "windows":
        return int(round(length))
    if unit == "bars":
        if not ww.n_bars:
            raise ValueError(f"{ww.work_id}: sin recuento de compases (bar_remaining)")
        return max(1, int(round(length * len(ww) / ww.n_bars)))
    raise ValueError(f"unidad de longitud desconocida: {unit!r}")


def fragment_starts(ww: WorkWindows, L: int) -> np.ndarray:
    """Inicios válidos de un fragmento contiguo de L ventanas dentro de un mismo movimiento."""
    n = len(ww)
    if L <= 0 or n < L:
        return np.empty(0, dtype=np.int64)
    s = np.arange(n - L + 1)
    return s[ww.mov[s] == ww.mov[s + L - 1]]


def sample_fragments(ww: WorkWindows, L: int, k: int, rng: np.random.Generator) -> list[np.ndarray]:
    """k fragmentos contiguos de L ventanas de ww (inicio uniforme entre los válidos)."""
    st = fragment_starts(ww, L)
    if len(st) == 0:
        return []
    pick = rng.choice(st, size=k, replace=True)
    return [ww.hashes[s:s + L] for s in pick]


def sample_null_fragments(pool: Sequence[WorkWindows], L, k: int, rng: np.random.Generator):
    """k fragmentos de la piscina: uniforme sobre todos los (obra, inicio) válidos.
    L = número de ventanas (int) o función obra -> número de ventanas (emparejamiento por compases)."""
    Lf = L if callable(L) else (lambda _w: L)
    lens = [Lf(w) for w in pool]
    starts = [(i, fragment_starts(w, lens[i])) for i, w in enumerate(pool)]
    starts = [(i, s) for i, s in starts if len(s)]
    if not starts:
        return [], []
    sizes = np.array([len(s) for _, s in starts])
    flat = rng.integers(0, sizes.sum(), size=k)
    cum = np.cumsum(sizes)
    out, src = [], []
    for f in flat:
        j = int(np.searchsorted(cum, f, side="right"))
        i, s = starts[j]
        off = int(f - (cum[j - 1] if j else 0))
        st = int(s[off])
        out.append(pool[i].hashes[st:st + lens[i]]); src.append(pool[i].work_id)
    return out, src


# ----------------------------------------------------------------------------
# p-valor, Bonferroni, regla de decisión
# ----------------------------------------------------------------------------
def p_value(obs: float, null: Sequence[float]) -> float:
    """Fracción de nulos con recuento ≥ observado (D-41)."""
    null = np.asarray(null)
    if len(null) == 0:
        raise ValueError("nulo vacío")
    return float((null >= obs).mean())


def bonferroni(ps: Sequence[float], m: int | None = None) -> list[float]:
    m = len(ps) if m is None else m
    return [min(1.0, float(p) * m) for p in ps]


def confirmation_rule(cases: Sequence[Mapping], alpha: float = ALPHA) -> dict:
    """cases: dicts con 'work_A', 'p_corrected' y 'n_pass_nonuniform' (tipos compartidos con
    DF ≤ t_DF y ritmo no uniforme en esa obra). Confirmación: alguna obra con p corregido ≤ alpha
    y n_pass_nonuniform ≥ 1 en esa misma obra."""
    sig = [c["work_A"] for c in cases if c["p_corrected"] <= alpha]
    conf = [c["work_A"] for c in cases if c["p_corrected"] <= alpha and c["n_pass_nonuniform"] >= 1]
    return {"confirmed": bool(conf), "significant_works": sig, "confirming_works": conf,
            "refuted_strong_sense": not sig, "alpha": alpha}


def rank_by_E(shared: Sequence[Mapping], e_fn: Callable[[np.ndarray], float] | None):
    """Tipos compartidos que pasan DF, ordenados por E (menor primero). Solo informativo."""
    rows = [dict(r) for r in shared if r["pass_DF"]]
    if e_fn is None:
        return rows
    for r in rows:
        r["E"] = float(e_fn(r["sym"]))
    return sorted(rows, key=lambda r: r["E"])


# ----------------------------------------------------------------------------
# D-43 (b): fragmentos A′ por compases completos, ±5 % en ventanas, colapso por fragmento
# ----------------------------------------------------------------------------
TOL = 1e-6
COLLAPSE_THRESHOLD = 0.95          # D-13 (scripts/extract.py)
LEN_TOL = 0.05                     # D-43 (b): L(A′) ∈ [0,95·L(A), 1,05·L(A)]
MAX_DRAWS = 200_000


@dataclass
class Notes:
    """Notas de una obra (o fragmento) tal como las guarda la caché: una fila por nota."""
    work_id: str
    composer: str
    midi: np.ndarray
    ql: np.ndarray
    offset: np.ndarray
    voice: np.ndarray
    mov: np.ndarray
    gap: np.ndarray
    br: np.ndarray                 # bar_remaining (−1 si no hay)

    @classmethod
    def from_cache(cls, d: Mapping, work_id: str, composer: str) -> "Notes":
        return cls(work_id, composer, np.asarray(d["midi"], float), np.asarray(d["quarter_length"], float),
                   np.asarray(d["offset"], float), np.asarray(d["voice_id"], int), np.asarray(d["movement_idx"], int),
                   np.asarray(d["gap_before"], float), np.asarray(d["bar_remaining"], float))

    def take(self, mask: np.ndarray) -> "Notes":
        return Notes(self.work_id, self.composer, *(getattr(self, k)[mask] for k in
                                                    ("midi", "ql", "offset", "voice", "mov", "gap", "br")))

    def __len__(self) -> int:
        return len(self.midi)


def _rclass(dp: float, d: float) -> int:
    if dp <= 0 or d <= 0:
        return 0
    r = d / dp
    return -2 if r < 0.4 else -1 if r < 0.9 else 0 if r <= 1.1 else 1 if r <= 2.5 else 2


def voice_tokens(nt: Notes, v: int) -> set:
    """Tokens D-13 de una voz (extract.tokens): (offset redondeado, intervalo, rclass)."""
    sel = np.nonzero(nt.voice == v)[0]
    m, d, o = nt.midi[sel], nt.ql[sel], nt.offset[sel]
    return {(round(float(o[i]), 3), float(m[i + 1] - m[i]), _rclass(float(d[i]), float(d[i + 1])))
            for i in range(len(sel) - 1)}


def collapse_voices(nt: Notes, threshold: float = COLLAPSE_THRESHOLD) -> Notes:
    """Colapso de voces dobladas (regla D-13 de extract.collapse_parts) aplicado a un fragmento:
    en orden de voz, se descarta una voz si > threshold de sus tokens (≥ 4) coinciden con una
    voz ya conservada (fracción sobre la más corta)."""
    kept, kept_toks = [], []
    for v in sorted(np.unique(nt.voice).tolist()):
        t = voice_tokens(nt, v)
        dup = False
        if len(t) >= 4:
            for kt in kept_toks:
                if len(kt) >= 4 and len(t & kt) / min(len(t), len(kt)) > threshold:
                    dup = True
                    break
        if not dup:
            kept.append(v); kept_toks.append(t)
    return nt.take(np.isin(nt.voice, kept))


def note_windows(nt: Notes, symbols_fn: Callable = symbols_from_arr, hash_fn: Callable = rolling_hashes_local,
                 m: int = M_ORD) -> np.ndarray:
    """Hashes de las ventanas de 8 notas: segmentos por (movimiento, voz) cortados por cualquier
    silencio (rest_break = 0) y en el borde del fragmento; las notas fuera del fragmento no existen,
    así que las ventanas que cruzan el borde no cuentan."""
    if len(nt) == 0:
        return np.empty(0, dtype=np.uint64)
    order = np.lexsort((nt.offset, nt.voice, nt.mov))
    midi, ql, off, v, mv, gap = (x[order] for x in (nt.midi, nt.ql, nt.offset, nt.voice, nt.mov, nt.gap))
    key = mv.astype(np.int64) * 100000 + v
    cut = np.r_[True, (key[1:] != key[:-1]) | (gap[1:] > TOL)]
    starts = np.nonzero(cut)[0].tolist() + [len(midi)]
    out = []
    for a, b in zip(starts[:-1], starts[1:]):
        if b - a >= m + 1:
            arr = np.stack([midi[a:b], ql[a:b], off[a:b]], axis=1)
            out.append(np.asarray(hash_fn(np.asarray(symbols_fn(arr), dtype=np.int64), m), dtype=np.uint64))
    return np.concatenate(out) if out else np.empty(0, dtype=np.uint64)


def fragment_hashes(nt: Notes, collapse: bool = True, **kw) -> np.ndarray:
    return note_windows(collapse_voices(nt) if collapse else nt, **kw)


def bar_table(nt: Notes) -> list[tuple[int, float, float]]:
    """Compases (movimiento, inicio, fin) reconstruidos con offset + bar_remaining (D-43 b)."""
    out = []
    for mv in np.unique(nt.mov).tolist():
        sel = (nt.mov == mv) & (nt.br >= 0)
        if not sel.any():
            continue
        ends = np.unique(np.round(nt.offset[sel] + nt.br[sel], 3))
        first = float(np.min(nt.offset[nt.mov == mv]))
        starts = np.r_[min(first, ends[0]), ends[:-1]]
        out += [(int(mv), float(s), float(e)) for s, e in zip(starts, ends) if e > s]
    return out


def span(nt: Notes, mv: int, t0: float, t1: float) -> Notes:
    """Notas con ataque en [t0, t1) del movimiento mv, todas las partes."""
    return nt.take((nt.mov == mv) & (nt.offset >= t0 - TOL) & (nt.offset < t1 - TOL))


def quarters(nt: Notes) -> float:
    if len(nt) == 0:
        return 0.0
    return float(np.max(nt.offset + nt.ql) - np.min(nt.offset))


def draw_bar_fragment(pool: Sequence[Notes], bars: Sequence[list], target: float, rng: np.random.Generator,
                      measure: str = "windows", tol: float = LEN_TOL, collapse: bool = True,
                      max_draws: int = MAX_DRAWS, **kw):
    """Un fragmento A′ (D-43 b): barra de inicio uniforme entre todas las barras de la piscina, se añaden
    compases completos hasta que la medida ∈ [(1−tol)·target, (1+tol)·target]; si el primer compás que
    supera (1−tol)·target pasa de (1+tol)·target, o el movimiento se acaba, se descarta y se resortea.
    measure = "windows" (principal) o "quarters" (alternativa declarada: duración en negras).
    Devuelve (hashes, work_id, intentos)."""
    sizes = np.array([len(b) for b in bars])
    if sizes.sum() == 0:
        raise ValueError("piscina sin compases")
    cum = np.cumsum(sizes)
    lo, hi = (1 - tol) * target, (1 + tol) * target
    for tries in range(1, max_draws + 1):
        f = int(rng.integers(0, cum[-1]))
        i = int(np.searchsorted(cum, f, side="right"))
        b0 = f - (int(cum[i - 1]) if i else 0)
        bl = bars[i]
        mv, t0, _ = bl[b0]
        for j in range(b0, len(bl)):
            if bl[j][0] != mv:
                break
            nt = span(pool[i], mv, t0, bl[j][2])
            if collapse:
                nt = collapse_voices(nt)
            h = note_windows(nt, **kw)
            val = len(h) if measure == "windows" else quarters(nt)
            if val >= lo:
                if val <= hi:
                    return h, pool[i].work_id, tries
                break
    raise RuntimeError(f"sin fragmento admisible tras {max_draws} sorteos")


# ----------------------------------------------------------------------------
# piscina del nulo (paper/D-43_null_pool.csv)
# ----------------------------------------------------------------------------
def read_null_pool(path: Path, catalog: Mapping[str, Mapping] | None = None) -> dict[str, list[dict]]:
    """Lee el CSV de la piscina (cabecera work_id, composer_id, …, instrumentation, fragments, rule).
    Devuelve {etiqueta de fragmento: filas}; la columna `fragments` separa por ';'. La guardia se aplica
    a cada fila y, si se da el catálogo, a la fila del catálogo (is_target)."""
    import csv
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "work_id" not in rows[0] or "fragments" not in rows[0]:
        raise ValueError(f"{path}: se esperaba un CSV con columnas work_id y fragments")
    out: dict[str, list[dict]] = {}
    for r in rows:
        guard.check_catalog_rows([r], context=f"piscina del nulo ({path.name})")
        if catalog is not None:
            if r["work_id"] not in catalog:
                raise ValueError(f"{r['work_id']} no está en el catálogo")
            guard.check_catalog_rows([catalog[r["work_id"]]], context=f"piscina del nulo ({path.name})")
        for lab in [x.strip() for x in r["fragments"].split(";") if x.strip()]:
            out.setdefault(lab, []).append(r)
    return out


# ----------------------------------------------------------------------------
# un caso y el conjunto
# ----------------------------------------------------------------------------
def p_plus1(obs: float, null: Sequence[float]) -> float:
    """(1 + #{nulos ≥ observado}) / (1 + R), informado junto al p de D-41."""
    null = np.asarray(null)
    return float((1 + (null >= obs).sum()) / (1 + len(null)))


def pass_sets_by_composer(B: WorkWindows, df_fn: Callable, composers: Iterable[str], t_df: float):
    """S_B[c] = {q ∈ tipos(B) : DF₋{c, cB}(q) ≤ t_DF} para cada compositor c (regla D-37 por par).
    df_fn(sym, c) = DF de q en el estrato sin c ni el compositor de B."""
    dfs, S = {}, {}
    for c in sorted(set(composers)):
        dfs[c], S[c] = pass_set(B, lambda s, c=c: df_fn(s, c), t_df)
    return dfs, S


def run_case(label: str, A: Notes, B: WorkWindows, pool: Sequence[Notes], df_fn: Callable, t_df: float,
             rng: np.random.Generator, n_null: int = N_NULL, measure: str = "windows",
             df_common_fn: Callable | None = None, e_fn=None, collapse: bool = True,
             kw_win: Mapping | None = None) -> dict:
    """Un fragmento A frente a B (D-43 b).
    Principal: K(A) con S_B[compositor de A]; cada réplica A′ con S_B[compositor de A′] (D-37 por par).
    Secundario (si df_common_fn): un único S_B con exclusión común, igual para A y A′."""
    kw_win = dict(kw_win or {})
    pool_ids = {w.work_id for w in pool}
    if A.work_id in pool_ids or B.work_id in pool_ids:
        raise ValueError("A o B dentro de la piscina del nulo")
    if any(w.composer in (A.composer, B.composer) for w in pool):
        raise ValueError("la piscina del nulo contiene obras del compositor de A o de B")
    hA = fragment_hashes(A, collapse=collapse, **kw_win)
    LA = len(hA)
    target = LA if measure == "windows" else quarters(A)
    dfs, S = pass_sets_by_composer(B, df_fn, [A.composer] + [w.composer for w in pool], t_df)
    bars = [bar_table(w) for w in pool]
    reps, tries = [], 0
    for _ in range(n_null):
        h, src, t = draw_bar_fragment(pool, bars, target, rng, measure=measure, collapse=collapse, **kw_win)
        reps.append((h, src, next(w.composer for w in pool if w.work_id == src)))
        tries += t
    obs = count_statistic(hA, S[A.composer])
    null = [count_statistic(h, S[c]) for h, _, c in reps]
    # tipos compartidos con su símbolo (para el ritmo y el ranking por E): se reconstruyen de B
    iB = type_index(B)
    shared = []
    for h in sorted(set(np.unique(hA).tolist()) & set(iB)):
        sym = B.syms[iB[h]]
        d = dfs[A.composer][h]
        shared.append(dict(hash=h, sym=sym, DF=d, pass_DF=d <= t_df, uniform_rhythm=uniform_rhythm(sym)))
    passing = [r for r in shared if r["pass_DF"]]
    comp_counts: dict[str, int] = {}
    for _, src, c in reps:
        comp_counts[c] = comp_counts.get(c, 0) + 1
    res = {"label": label, "work_A": A.work_id, "work_B": B.work_id, "L_A_windows": LA,
           "measure": measure, "target": target, "statistic": obs, "n_null": len(null),
           "null_mean": float(np.mean(null)), "null_max": int(np.max(null)),
           "p": p_value(obs, null), "p_plus1": p_plus1(obs, null),
           "draws": tries, "rejection_rate": 1 - len(reps) / tries,
           "replicate_composers": comp_counts, "exclusion": "D-37 por réplica (compositor de A′ y de B)",
           "n_shared": len(shared), "n_pass": len(passing),
           "n_pass_nonuniform": sum(not r["uniform_rhythm"] for r in passing),
           "ranking_E": [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in r.items()}
                         for r in rank_by_E(shared, e_fn)][:50]}
    if df_common_fn is not None:
        _dc, Sc = pass_set(B, df_common_fn, t_df)
        oc = count_statistic(hA, Sc)
        nc = [count_statistic(h, Sc) for h, _, _ in reps]
        res["secondary_common_exclusion"] = {"label": "secundario: exclusión común para A y A′ (D-43 e)",
                                             "statistic": oc, "null_mean": float(np.mean(nc)),
                                             "p": p_value(oc, nc), "p_plus1": p_plus1(oc, nc)}
    return res


def run_confirmatory(cases: Sequence[tuple], B: WorkWindows, df_fn, t_df, seed=SEED, **kw) -> dict:
    """cases = [(etiqueta, k, A: Notes, piscina: [Notes])]; generador default_rng([seed, k]) por fragmento
    (D-43 b: k = 1 para A1, k = 2 para A2), así que el resultado no depende del orden."""
    out = []
    for label, k, A, pool in cases:
        rng = np.random.default_rng([seed, int(k)])
        r = run_case(label, A, B, pool, df_fn, t_df, rng, **kw)
        r["rng"] = [seed, int(k)]
        out.append(r)
    for c, pc in zip(out, bonferroni([c["p"] for c in out])):
        c["p_corrected"] = pc
    for c, pc in zip(out, bonferroni([c["p_plus1"] for c in out])):
        c["p_plus1_corrected"] = pc
    return {"cases": out, "decision": confirmation_rule(out), "bonferroni_m": len(out), "seed": seed}


# ----------------------------------------------------------------------------
# bloqueo
# ----------------------------------------------------------------------------
def authorize(ids: Iterable[str], run_confirmatory: bool, d43_commit: str | None,
              env: Mapping[str, str], verify_commit: Callable[[str], bool] | None = None) -> bool:
    """True si la ejecución toca objetivos y está desbloqueada; False si no toca objetivos.
    Si toca objetivos sin el desbloqueo completo, aborta con PreregistrationViolation (guardia).
    El desbloqueo exige: run_confirmatory, d43_commit con forma de hash git (y existente si se da
    verify_commit) y env[UNLOCK_ENV] == UNLOCK_VALUE."""
    ids = [str(i) for i in ids]
    touches = any(guard.is_forbidden_id(i) for i in ids)
    if not touches:
        return False
    ok_hash = bool(d43_commit) and bool(HASH_RE.match(str(d43_commit).lower()))
    if ok_hash and verify_commit is not None:
        ok_hash = verify_commit(str(d43_commit))
    unlocked = bool(run_confirmatory) and ok_hash and env.get(UNLOCK_ENV) == UNLOCK_VALUE
    if not unlocked:
        missing = [n for n, ok in (("--run-confirmatory", run_confirmatory), ("--d43-commit válido", ok_hash),
                                   (f"{UNLOCK_ENV}={UNLOCK_VALUE}", env.get(UNLOCK_ENV) == UNLOCK_VALUE)) if not ok]
        guard.check_ids(ids, context=f"confirmatory_n8 (desbloqueo incompleto: falta {', '.join(missing)})")
        raise ConfirmatoryLocked("desbloqueo incompleto")   # inalcanzable: check_ids ya abortó
    return True


def git_commit_exists(root: Path) -> Callable[[str], bool]:
    def f(h: str) -> bool:
        r = subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{h}^{{commit}}"],
                           capture_output=True)
        return r.returncode == 0
    return f


# ----------------------------------------------------------------------------
# carga de datos reales (solo en main)
# ----------------------------------------------------------------------------
def beethoven_root() -> Path:
    return Path(os.environ.get("BEETHOVEN_ROOT", str(_HERE.parent))).resolve()


def load_pipeline():
    """Importa seqlib y kn_background desde $BEETHOVEN_ROOT/scripts y comprueba su origen."""
    sd = beethoven_root() / "scripts"
    sys.path.insert(0, str(sd))
    import seqlib as sl
    import kn_background as kb
    for mod in (sl, kb):
        if Path(mod.__file__).resolve().parent != sd:
            raise RuntimeError(f"{mod.__name__} importado desde {mod.__file__}, se esperaba {sd}")
    return sl, kb


def load_work_any(sl, wid: str, extra_cache: Path | None, allow: frozenset = frozenset()):
    """sl.load_work con respaldo en una caché local (obras no primarias extraídas aparte).
    `allow` = identificadores objetivo ya autorizados por authorize() (solo en la ejecución desbloqueada)."""
    if wid not in allow:
        guard.check_ids([wid], context="load_work_any")
    d = sl.load_work(wid)
    if d is None and extra_cache is not None and (extra_cache / f"{wid}.npz").exists():
        old = sl.CACHE
        try:
            sl.CACHE = extra_cache
            d = sl.load_work(wid)
        finally:
            sl.CACHE = old
    return d


def real_windows(sl, kb, wid: str, composer: str, extra_cache: Path | None = None,
                 allow: frozenset = frozenset()) -> WorkWindows:
    """Ventanas de 8 notas como thresholds_n8.windows_with_movement (sequences_ex, rest_break 0)."""
    d = load_work_any(sl, wid, extra_cache, allow)
    if d is None:
        raise FileNotFoundError(f"sin caché para {wid}")
    seqs = [(mv, v, arr) for mv, v, _b, arr in sl.sequences_ex(d, 0.0)]
    return windows_from_sequences(seqs, wid, composer, symbols_fn=lambda a: kb.symbols_of(a)[0],
                                  hash_fn=kb.order_hashes)


def read_thresholds(root: Path) -> tuple[float, float]:
    t = json.loads((root / "results" / "thresholds_n8.json").read_text(encoding="utf-8"))
    return float(t["DF"]["threshold"]), float(t["E"]["threshold"])


def parse_A(specs: Sequence[str]) -> list[tuple[str, int, str]]:
    """--A A1=<work_id> A2=<work_id>  ->  [(etiqueta, k, work_id)], k = número de la etiqueta (A1 → 1)."""
    out = []
    for s in specs:
        if "=" not in s:
            raise SystemExit(f"--A espera ETIQUETA=work_id, no {s!r}")
        lab, wid = s.split("=", 1)
        m = re.fullmatch(r"A(\d+)", lab.strip())
        if not m:
            raise SystemExit(f"etiqueta de fragmento no válida: {lab!r} (A1, A2, …)")
        out.append((lab.strip(), int(m.group(1)), wid.strip()))
    return out


def main(argv=None, env=None):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--A", nargs="+", required=True, help="fragmentos A como A1=<work_id> A2=<work_id> (D-43 a)")
    ap.add_argument("--B", default=TARGET_B)
    ap.add_argument("--null-pool", type=Path, required=True,
                    help="CSV de la piscina (paper/D-43_null_pool.csv; columna fragments separa por fragmento)")
    ap.add_argument("--measure", choices=("windows", "quarters"), default="windows",
                    help="emparejamiento de longitud: ventanas (principal) o duración en negras (sensibilidad)")
    ap.add_argument("--no-fragment-collapse", action="store_true", help="sin colapso de dobladas por fragmento")
    ap.add_argument("--n-null", type=int, default=N_NULL)
    ap.add_argument("--run-confirmatory", action="store_true")
    ap.add_argument("--d43-commit", default=None)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    root = beethoven_root()
    As = parse_A(args.A)
    ids = [w for _, _, w in As] + [args.B]
    unlocked = authorize(ids, args.run_confirmatory, args.d43_commit, env, verify_commit=git_commit_exists(root))
    # -------- a partir de aquí: o no hay objetivos, o el usuario desbloqueó explícitamente --------
    sl, kb = load_pipeline()
    cat = sl.load_catalog(in_analysis_only=False, primary_only=False, exclude_target=False)
    pools = read_null_pool(args.null_pool, catalog=cat)
    for lab, _, _ in As:
        if lab not in pools:
            raise SystemExit(f"la piscina no tiene filas para el fragmento {lab}")
    t_df, t_e = read_thresholds(root)
    M = kb.Models(STRATUM, N, LAM)
    cB = cat[args.B]["composer_id"]
    wB = M.widx.get(args.B, -1)          # op. 67 no está en las tablas (is_target): el término de compositor usa todo Beethoven
    df_fn = lambda s, c: M.df(s, c, cB)  # D-37 por par: sin el compositor de A (o de A′) ni el de B
    pool_comps = sorted({r["composer_id"] for rows in pools.values() for r in rows})
    Mc = kb.Models(STRATUM, N, LAM, tables=M.T)
    common = set().union(*(M.comp_works.get(c, set()) for c in pool_comps + [cB]))
    Mc.excl_of = lambda _cA, _cB: common  # secundario D-43 (e): exclusión común {B} ∪ compositores de la piscina
    df_common = lambda s: Mc.df(s, cB, cB)
    allow = frozenset(ids) if unlocked else frozenset()
    B = real_windows(sl, kb, args.B, cB, allow=allow)
    e_fn = lambda s: len(B) * M.p_hier(s, As and cat[As[0][2]]["composer_id"], cB, wB)
    kw_win = dict(symbols_fn=lambda a: kb.symbols_of(a)[0], hash_fn=kb.order_hashes)

    def notes(wid):
        d = load_work_any(sl, wid, None, allow)
        if d is None:
            raise FileNotFoundError(f"sin caché para {wid}")
        return Notes.from_cache(d, wid, cat[wid]["composer_id"])

    cases = []
    for lab, k, wid in As:
        pool = [notes(r["work_id"]) for r in pools[lab]]
        cases.append((lab, k, notes(wid), pool))
    out = run_confirmatory(cases, B, df_fn, t_df, n_null=args.n_null, measure=args.measure,
                           df_common_fn=df_common, e_fn=e_fn, collapse=not args.no_fragment_collapse,
                           kw_win=kw_win)
    out.update(t_DF=t_df, t_E=t_e, n=N, lam=LAM, stratum=STRATUM, d43_commit=args.d43_commit,
               unlocked=unlocked, null_pool={lab: [r["work_id"] for r in pools[lab]] for lab, _, _ in As})
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "confirmatory_n8.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str),
                                                       encoding="utf-8")
    print(json.dumps(out["decision"], indent=1, ensure_ascii=False))
    return out


if __name__ == "__main__":
    main()
