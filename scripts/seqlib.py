"""Utilidades compartidas por los análisis de Fase 1: lectura de la caché, catálogo,
segmentación por silencios y definiciones D1–D5 / rclass del piloto (sin cambios).

Todos los análisis leen SOLO corpus/cache/*.npz y corpus/works.csv.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "corpus" / "cache"
WORKS = ROOT / "corpus" / "works.csv"

TOL = 1e-6
TARGETS = ((0, 0, -4), (0, 0, -3))          # D2: alturas generalizadas
DEFS = ["D1", "D2", "D3", "D4", "D5"]
PERIODS = ["<1750", "1750–1800", "1800–1830", "1830–1900", ">1900", "unknown"]
MIN_WORKS_PER_COMPOSER = 5


# ---------------------------------------------------------------- definiciones del piloto
def rhythm_ok(d1, d2, d3, d4):
    """D3: tres duraciones iguales seguidas de una >= 2x (base_rate2.py)."""
    if d1 <= 0 or d2 <= 0 or d3 <= 0:
        return False
    if abs(d1 - d2) > TOL or abs(d2 - d3) > TOL:
        return False
    return d4 >= 2 * d3 - TOL


def weak_position(offset):
    """D5: ataque en posición métrica débil (base_rate2.py)."""
    return abs(offset - round(offset)) > TOL or (round(offset) % 2 == 1)


def rclass(d_prev, d):
    """Clase rítmica del ratio d/d_prev (uniqueness.py)."""
    if d_prev <= 0 or d <= 0:
        return 0
    r = d / d_prev
    if r < 0.4:
        return -2
    if r < 0.9:
        return -1
    if r <= 1.1:
        return 0
    if r <= 2.5:
        return 1
    return 2


# ---------------------------------------------------------------- catálogo
def load_catalog(in_analysis_only=True, primary_only=True, exclude_target=False):
    """Devuelve dict work_id -> {collection, composer_id, composer, period, ...} (una entrada por obra)."""
    works = {}
    with open(WORKS, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if in_analysis_only and r["in_analysis"] != "1":
                continue
            if primary_only and r["is_primary"] != "1":
                continue
            if exclude_target and r["is_target"] == "1":
                continue
            w = works.setdefault(r["work_id"], dict(r))
            w.setdefault("units", []).append(r["unit_id"])
    return works


def collection_group(collection: str) -> str:
    """Estrato 'collection' para las tablas: repos kern/dcml individuales, resto tal cual."""
    return collection


# ---------------------------------------------------------------- caché -> secuencias
def load_work(work_id: str):
    p = CACHE / f"{work_id}.npz"
    if not p.exists():
        return None
    z = np.load(p, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    out = {k: z[k] for k in ("midi", "quarter_length", "offset", "voice_id", "movement_idx",
                             "from_chord", "gap_before")}
    out["bar_remaining"] = z["bar_remaining"] if "bar_remaining" in z.files else np.full(len(out["midi"]), -1.0, np.float32)
    out["meta"] = meta
    return out


def sequences(data, rest_break: float = 0.0, min_len: int = 4):
    """Lista de secuencias [(midi, ql, offset), ...] por voz, cortadas donde
    gap_before > rest_break (rest_break=0 -> cualquier silencio corta, como el piloto).
    Cada secuencia pertenece a un (movement_idx, voice_id) y tiene >= min_len eventos."""
    midi = data["midi"]
    ql = data["quarter_length"]
    off = data["offset"]
    key = data["movement_idx"].astype(np.int64) * 100000 + data["voice_id"].astype(np.int64)
    gap = data["gap_before"]
    seqs = []
    n = len(midi)
    if n == 0:
        return seqs
    start = 0
    for i in range(1, n + 1):
        cut = i == n or key[i] != key[i - 1] or gap[i] > rest_break + TOL
        if cut:
            if i - start >= min_len:
                seqs.append(list(zip(midi[start:i].tolist(), ql[start:i].tolist(), off[start:i].tolist())))
            start = i
    return seqs


def sequences_ex(data, rest_break: float = 0.0, min_len: int = 4):
    """Como sequences(), pero devuelve (movement_idx, voice_id, is_bass, arr[n,4]) con columnas
    midi, ql, offset, bar_remaining. is_bass: la voz de mediana MIDI más baja de su movimiento
    (solo si el movimiento tiene >= 2 voces)."""
    midi, ql, off, br = data["midi"], data["quarter_length"], data["offset"], data["bar_remaining"]
    mv, vc, gap = data["movement_idx"], data["voice_id"], data["gap_before"]
    n = len(midi)
    if n == 0:
        return []
    # voz más grave por movimiento
    bass = {}
    for m in np.unique(mv):
        sel = mv == m
        voices = np.unique(vc[sel])
        if len(voices) < 2:
            continue
        med = {v: float(np.median(midi[sel & (vc == v)])) for v in voices}
        bass[int(m)] = min(med, key=med.get)
    key = mv.astype(np.int64) * 100000 + vc.astype(np.int64)
    out = []
    start = 0
    for i in range(1, n + 1):
        if i == n or key[i] != key[i - 1] or gap[i] > rest_break + TOL:
            if i - start >= min_len:
                m, v = int(mv[start]), int(vc[start])
                arr = np.stack([midi[start:i].astype(np.float64), ql[start:i].astype(np.float64),
                                off[start:i].astype(np.float64), br[start:i].astype(np.float64)], axis=1)
                out.append((m, v, bass.get(m) == v, arr))
            start = i
    return out


def by_stratum(works: dict, key: str):
    """Agrupa work_ids por valor de la columna `key` del catálogo."""
    out = defaultdict(list)
    for wid, w in works.items():
        out[w[key]].append(wid)
    return out


def composer_strata(works: dict, min_works=MIN_WORKS_PER_COMPOSER):
    g = by_stratum(works, "composer_id")
    return {c: ws for c, ws in g.items() if len(ws) >= min_works}
