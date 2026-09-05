"""Extracción de secuencias melódicas a corpus/cache/<work_id>.npz (tarea 4).

Reglas heredadas del piloto (scripts/pilot/base_rate2.py::voice_sequences) más D-13/D-19:
  * una secuencia por parte (part.flatten().notesAndRests), todas las partes;
  * acorde -> nota superior (from_chord=1);
  * ligaduras (tie stop/continue, misma altura) fundidas sumando duraciones;
  * los silencios se guardan como `gap_before` (negras de silencio inmediatamente antes
    del evento en esa parte); el corte por silencio (--rest-break, por defecto 0 = cualquier
    silencio corta) lo aplica el análisis sobre `gap_before`, sin volver a parsear;
  * voces dobladas colapsadas (D-13): tokens (offset, intervalo, rclass) coincidentes en
    > 95 % de la más corta -> se descarta la posterior en orden de partitura;
  * streaming: una obra en memoria a la vez; paralelo por obra (multiprocessing).

Formato npz (arrays alineados, un elemento por nota):
  midi(int16) quarter_length(float32) offset(float32) voice_id(int16) movement_idx(int16)
  from_chord(int8) gap_before(float32)   + meta (json): work_id, unidades, rest_break, versión.

Uso:
  .venv/bin/python scripts/extract.py [--workers 8] [--rest-break 0] [--only COLL]
                                      [--include-duplicates] [--force] [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import traceback
import warnings
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
CACHE = ROOT / "corpus" / "cache"
WORKS = ROOT / "corpus" / "works.csv"
LOG = ROOT / "results" / "extract_log.csv"

TOL = 1e-6
COLLAPSE_THRESHOLD = 0.95
EXTRACT_VERSION = "1.0 (2026-09-05)"
LOG_COLS = ["work_id", "unit_id", "collection", "format", "status", "error", "n_parts_raw",
            "n_parts_kept", "collapse_ratio", "n_events", "n_rests", "seconds"]


# ----------------------------------------------------------------------------
# clase rítmica (idéntica a scripts/pilot/uniqueness.py::rclass)
# ----------------------------------------------------------------------------
def rclass(d_prev, d):
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


# ----------------------------------------------------------------------------
# lectores: cada uno devuelve lista de partes; parte = lista de eventos
# evento = (midi, ql, offset, from_chord, gap_before)
# ----------------------------------------------------------------------------
def _m21_part_events(part):
    """Reproduce voice_sequences() del piloto, guardando el silencio previo en vez de cortar."""
    from music21 import chord, note
    events = []
    gap = 0.0
    n_rests = 0
    for el in part.flatten().notesAndRests:
        if isinstance(el, note.Rest):
            try:
                gap += float(el.duration.quarterLength)
            except Exception:
                pass
            n_rests += 1
            continue
        if isinstance(el, chord.Chord):
            if not el.pitches:
                continue
            midi = max(p.midi for p in el.pitches)
            tie = el.tie
            from_chord = 1
        elif isinstance(el, note.Note):
            midi = el.pitch.midi
            tie = el.tie
            from_chord = 0
        else:
            continue
        try:
            ql = float(el.duration.quarterLength)
            off = float(el.offset)
        except Exception:
            continue
        if (tie is not None and tie.type in ("stop", "continue") and gap == 0.0
                and events and events[-1][0] == midi):
            m, d, o, fc, g = events[-1]
            events[-1] = (m, d + ql, o, fc, g)
            continue
        events.append((midi, ql, off, from_chord, gap))
        gap = 0.0
    return events, n_rests


def read_music21(path: Path, fmt: str):
    warnings.filterwarnings("ignore")
    from music21 import converter
    kw = {"forceSource": True}
    if fmt.startswith("musedata"):
        kw["format"] = "musedata"
    try:
        s = converter.parse(str(path), **kw)
    except Exception as e:
        if fmt != "kern":
            raise
        # music21 falla con algunos registros de referencia (!!!commission ...): reintentar
        # sin las líneas '!!!' (solo metadatos, no afectan a las notas)
        txt = "\n".join(l for l in Path(path).read_text(errors="replace").splitlines()
                         if not l.startswith("!!!"))
        s = converter.parse(txt, format="humdrum", forceSource=True)
    scores = list(s.scores) if getattr(s, "scores", None) else [s]
    parts, n_rests = [], 0
    for sc in scores:
        plist = list(sc.parts) if getattr(sc, "parts", None) else [sc]
        for part in plist:
            try:
                ev, nr = _m21_part_events(part)
            except Exception:
                continue
            n_rests += nr
            if ev:
                parts.append(ev)
    return parts, n_rests


def read_dcml_tsv(path: Path):
    """Lector de notes.tsv (ms3) emulando part.flatten() de music21 (D-19)."""
    import pandas as pd
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    onset_col = "quarterbeats_all_endings" if "quarterbeats_all_endings" in df.columns else "quarterbeats"

    def frac(x):
        if x in ("", "NA", "nan"):
            return None
        if "/" in x:
            a, b = x.split("/")
            return float(a) / float(b)
        return float(x)

    rows = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        on = frac(d.get(onset_col, ""))
        if on is None:
            on = frac(d.get("quarterbeats", ""))
        if on is None:
            continue
        dur = frac(d.get("duration_qb", "0")) or 0.0
        try:
            midi = int(float(d["midi"]))
        except Exception:
            continue
        staff = int(float(d.get("staff", "1") or 1))
        voice = int(float(d.get("voice", "1") or 1))
        mc = int(float(d.get("mc", "0") or 0))
        tied = d.get("tied", "")
        tied = int(float(tied)) if tied not in ("", "NA", "nan") else None
        rows.append((staff, voice, on, midi, dur, mc, tied))

    parts, n_rests = [], 0
    by_staff = defaultdict(list)
    for row in rows:
        by_staff[row[0]].append(row)
    for staff in sorted(by_staff):
        # 1) por voz: acordes -> nota superior; ligaduras; silencios sintéticos
        voices = defaultdict(list)
        for (_, voice, on, midi, dur, mc, tied) in by_staff[staff]:
            voices[voice].append((on, midi, dur, mc, tied))
        merged = []  # (offset, voice, midi, dur, from_chord) y silencios (offset, voice, None, dur)
        for voice in sorted(voices):
            ev = sorted(voices[voice], key=lambda x: (x[0], -x[1]))
            # agrupar por onset -> acorde
            chords = []
            for on, midi, dur, mc, tied in ev:
                if chords and abs(chords[-1][0] - on) < TOL:
                    c = chords[-1]
                    if midi > c[1]:
                        chords[-1] = (on, midi, dur, mc, tied, 1)
                    else:
                        chords[-1] = (c[0], c[1], c[2], c[3], c[4], 1)
                else:
                    chords.append((on, midi, dur, mc, tied, 0))
            seq = []
            for on, midi, dur, mc, tied, fc in chords:
                if seq and tied in (0, -1) and seq[-1][1] == midi and abs(seq[-1][0] + seq[-1][2] - on) < 1e-3:
                    o, m, d, mcp, fcp = seq[-1]
                    seq[-1] = (o, m, d + dur, mc, fcp)
                    continue
                seq.append((on, midi, dur, mc, fc))
            prev_end, prev_mc = None, None
            for on, midi, dur, mc, fc in seq:
                if prev_end is not None and on - prev_end > 1e-3:
                    if voice == 1 or mc == prev_mc:
                        merged.append((prev_end, voice, None, on - prev_end, 0))
                        n_rests += 1
                merged.append((on, voice, midi, dur, fc))
                prev_end, prev_mc = max(prev_end or 0.0, on + dur), mc
        # 2) aplanar por (offset, voz) como music21
        merged.sort(key=lambda x: (x[0], x[1]))
        events, gap = [], 0.0
        for off, voice, midi, dur, fc in merged:
            if midi is None:
                gap += dur
                continue
            events.append((midi, dur, off, fc, gap))
            gap = 0.0
        if events:
            parts.append(events)
    return parts, n_rests


def resolve_path(p: str) -> Path:
    if p.startswith("m21corpus:"):
        from music21 import corpus
        base = Path(corpus.__file__).parent if hasattr(corpus, "__file__") else None
        import music21
        return Path(music21.__file__).parent / "corpus" / p.split(":", 1)[1]
    return RAW / p


# ----------------------------------------------------------------------------
# colapso de voces dobladas (D-13)
# ----------------------------------------------------------------------------
def tokens(events):
    toks = set()
    for i in range(len(events) - 1):
        m0, d0, o0 = events[i][0], events[i][1], events[i][2]
        m1, d1 = events[i + 1][0], events[i + 1][1]
        toks.add((round(o0, 3), m1 - m0, rclass(d0, d1)))
    return toks


def collapse_parts(parts):
    kept, kept_toks = [], []
    for ev in parts:
        t = tokens(ev)
        dup = False
        if len(t) >= 4:
            for kt in kept_toks:
                if len(kt) >= 4:
                    inter = len(t & kt)
                    if inter / min(len(t), len(kt)) > COLLAPSE_THRESHOLD:
                        dup = True
                        break
        if not dup:
            kept.append(ev)
            kept_toks.append(t)
    return kept


# ----------------------------------------------------------------------------
def extract_work(job):
    work_id, units, rest_break, force = job
    out = CACHE / f"{work_id}.npz"
    logs = []
    if out.exists() and not force:
        for u in units:
            logs.append(dict(work_id=work_id, unit_id=u["unit_id"], collection=u["collection"],
                             format=u["format"], status="cached"))
        return logs
    arrays = defaultdict(list)
    meta_units = []
    t_work = time.time()
    voice_base = 0
    for mi, u in enumerate(units):
        t0 = time.time()
        rec = dict(work_id=work_id, unit_id=u["unit_id"], collection=u["collection"], format=u["format"])
        try:
            p = resolve_path(u["path"])
            if u["format"] == "dcml_tsv":
                parts, n_rests = read_dcml_tsv(p)
            else:
                parts, n_rests = read_music21(p, u["format"])
            kept = collapse_parts(parts)
            n_ev = 0
            for vi, ev in enumerate(kept):
                for midi, ql, off, fc, gap in ev:
                    arrays["midi"].append(midi)
                    arrays["quarter_length"].append(ql)
                    arrays["offset"].append(off)
                    arrays["voice_id"].append(voice_base + vi)
                    arrays["movement_idx"].append(mi)
                    arrays["from_chord"].append(fc)
                    arrays["gap_before"].append(gap)
                    n_ev += 1
            voice_base += len(kept)
            rec.update(status="ok", error="", n_parts_raw=len(parts), n_parts_kept=len(kept),
                       collapse_ratio=round(1 - len(kept) / len(parts), 3) if parts else "",
                       n_events=n_ev, n_rests=n_rests, seconds=round(time.time() - t0, 1))
            meta_units.append({"movement_idx": mi, "unit_id": u["unit_id"], "movement": u["movement"],
                               "n_parts_raw": len(parts), "n_parts_kept": len(kept), "n_events": n_ev})
        except Exception as e:
            rec.update(status="fail", error=f"{type(e).__name__}: {str(e)[:200]}".replace("\n", " "),
                       seconds=round(time.time() - t0, 1))
        logs.append(rec)
    if arrays["midi"]:
        CACHE.mkdir(parents=True, exist_ok=True)
        meta = {"work_id": work_id, "units": meta_units, "rest_break_default": rest_break,
                "extract_version": EXTRACT_VERSION, "seconds": round(time.time() - t_work, 1)}
        np.savez_compressed(out,
                            midi=np.array(arrays["midi"], dtype=np.int16),
                            quarter_length=np.array(arrays["quarter_length"], dtype=np.float32),
                            offset=np.array(arrays["offset"], dtype=np.float32),
                            voice_id=np.array(arrays["voice_id"], dtype=np.int16),
                            movement_idx=np.array(arrays["movement_idx"], dtype=np.int16),
                            from_chord=np.array(arrays["from_chord"], dtype=np.int8),
                            gap_before=np.array(arrays["gap_before"], dtype=np.float32),
                            meta=np.array(json.dumps(meta)))
    return logs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, os.cpu_count() - 2))
    ap.add_argument("--rest-break", type=float, default=0.0)
    ap.add_argument("--only", default=None, help="prefijo de collection (p. ej. kern/bach-370)")
    ap.add_argument("--include-duplicates", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--log", default=str(LOG))
    ap.add_argument("--retry-failed", action="store_true", help="reprocesa solo obras con unidades fallidas")
    args = ap.parse_args()
    failed_works = set()
    if args.retry_failed and Path(args.log).exists():
        with open(args.log, encoding="utf-8") as fh:
            failed_works = {r["work_id"] for r in csv.DictReader(fh) if r["status"] == "fail"}

    with open(WORKS, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    by_work = defaultdict(list)
    for r in rows:
        if args.only and not r["collection"].startswith(args.only):
            continue
        if r["is_primary"] != "1" and not args.include_duplicates:
            continue
        by_work[r["work_id"]].append(r)
    if args.retry_failed:
        by_work = {w: us for w, us in by_work.items() if w in failed_works}
    jobs = [(w, us, args.rest_break, args.force or args.retry_failed) for w, us in by_work.items()]
    if args.limit:
        jobs = jobs[: args.limit]
    # obras grandes primero para equilibrar
    jobs.sort(key=lambda j: -len(j[1]))
    print(f"obras: {len(jobs)}  unidades: {sum(len(j[1]) for j in jobs)}  workers: {args.workers}", flush=True)

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if log_path.exists() and not args.force:
        with open(log_path, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                existing[r["unit_id"]] = r
    t0 = time.time()
    done = 0
    n_fail = 0
    with Pool(args.workers) as pool:
        for logs in pool.imap_unordered(extract_work, jobs, chunksize=1):
            for rec in logs:
                if rec["status"] != "cached" or rec["unit_id"] not in existing:
                    existing[rec["unit_id"]] = {c: rec.get(c, "") for c in LOG_COLS}
                if rec["status"] == "fail":
                    n_fail += 1
            done += 1
            if done % 50 == 0 or done == len(jobs):
                el = time.time() - t0
                print(f"  {done}/{len(jobs)} obras  {el/60:.1f} min  fallos={n_fail}", flush=True)
                with open(log_path, "w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=LOG_COLS)
                    w.writeheader()
                    for k in sorted(existing):
                        w.writerow(existing[k])
    with open(log_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_COLS)
        w.writeheader()
        for k in sorted(existing):
            w.writerow(existing[k])
    print(f"listo en {(time.time()-t0)/60:.1f} min; fallos: {n_fail}; log: {log_path}")


if __name__ == "__main__":
    sys.exit(main())
