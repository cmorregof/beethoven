"""Test de regresión (D-18): la nueva canalización (extract.py -> caché -> recuento) debe
reproducir los números del piloto para `bach`.

Referencia del piloto (scripts/pilot/resultados_art.txt, colección `bach` del corpus
interno de music21, 433 ficheros): 101.162 ventanas, D2 = 148,28/100k, D4 = 7,91/100k.

Se comprueban dos colecciones:
  * m21_bach   — los mismos 433 ficheros del piloto (reproducción exacta esperada)
  * kern/bach-370-chorales — los 370 corales de craigsapp (conjunto distinto: 370 vs ~400
    corales + otras obras; se informa la desviación y se explica)
Sale con código 1 si m21_bach se desvía más del 2 % en D2 o D4.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402

PILOT = {"windows": 101162, "works": 433, "D2_rate": 148.28, "D4_rate": 7.91,
         "counts": {"D1": 42, "D2": 150, "D3": 6667, "D4": 8, "D5": 4}}
TOLERANCE = 0.02


def count_collection(collection: str, rest_break=0.0):
    works = sl.load_catalog(in_analysis_only=False, primary_only=True)
    wids = [w for w, r in works.items() if r["collection"] == collection]
    tot = Counter()
    prevalence = Counter()
    windows = notes = 0
    nworks = 0
    missing = 0
    for wid in wids:
        data = sl.load_work(wid)
        if data is None:
            missing += 1
            continue
        seqs = sl.sequences(data, rest_break)
        c = Counter()
        w = 0
        for seq in seqs:
            n = len(seq)
            notes += n
            ivs = [seq[i + 1][0] - seq[i][0] for i in range(n - 1)]
            durs = [e[1] for e in seq]
            for i in range(n - 3):
                iv = (ivs[i], ivs[i + 1], ivs[i + 2])
                r = sl.rhythm_ok(durs[i], durs[i + 1], durs[i + 2], durs[i + 3])
                w += 1
                if iv == (0, 0, -4):
                    c["D1"] += 1
                d2 = iv in sl.TARGETS
                if d2:
                    c["D2"] += 1
                if r:
                    c["D3"] += 1
                if d2 and r:
                    c["D4"] += 1
                    if sl.weak_position(seq[i][2]):
                        c["D5"] += 1
        if w == 0:
            continue
        nworks += 1
        windows += w
        for k, v in c.items():
            tot[k] += v
            prevalence[k] += 1
    return dict(collection=collection, works=nworks, missing=missing, windows=windows, notes=notes,
                counts=dict(tot), prevalence=dict(prevalence),
                rates={d: (1e5 * tot[d] / windows if windows else 0) for d in sl.DEFS})


def main():
    ok = True
    lines = ["# Test de regresión (D-18)", "",
             f"Referencia piloto `bach` (music21): ventanas {PILOT['windows']:,}, obras {PILOT['works']}, "
             f"D2 {PILOT['D2_rate']}/100k, D4 {PILOT['D4_rate']}/100k, recuentos {PILOT['counts']}", ""]
    for coll, strict in (("m21_bach", True), ("kern/bach-370-chorales", False)):
        r = count_collection(coll)
        lines.append(f"## {coll}")
        lines.append(f"obras {r['works']} (sin caché: {r['missing']}), ventanas {r['windows']:,}, notas {r['notes']:,}")
        lines.append("")
        lines.append("| def | recuento | por 100k | piloto por 100k | desviación |")
        lines.append("|---|---|---|---|---|")
        for d in sl.DEFS:
            rate = r["rates"][d]
            pilot_rate = 1e5 * PILOT["counts"][d] / PILOT["windows"]
            dev = (rate - pilot_rate) / pilot_rate if pilot_rate else float("nan")
            flag = ""
            if d in ("D2", "D4"):
                if abs(dev) > TOLERANCE:
                    flag = " **FUERA DE TOLERANCIA**" if strict else " (fuera de tolerancia: conjunto distinto)"
                    if strict:
                        ok = False
                else:
                    flag = " OK"
            lines.append(f"| {d} | {r['counts'].get(d, 0)} | {rate:.2f} | {pilot_rate:.2f} | {100*dev:+.1f}%{flag} |")
        lines.append("")
    lines.append("Notas: (1) el piloto contaba 433 «obras» en `bach` porque incluía 20 ficheros `.rntxt` "
                 "(análisis en números romanos) que music21 parsea como acordes; la nueva canalización los "
                 "excluye (413 ficheros), de ahí las ~1.900 ventanas de menos y la desviación de +1–2 %. "
                 "(2) `bach-370-chorales` es un conjunto distinto (370 corales Riemenschneider frente a "
                 "~390 corales + obras instrumentales del corpus music21), así que sus tasas no tienen por qué "
                 "coincidir; se listan como referencia.")
    lines.append("")
    verdict = "PASA" if ok else "FALLA"
    lines.append(f"**Resultado: {verdict}** (criterio: `m21_bach` D2 y D4 dentro de ±2 % del piloto).")
    out = sl.ROOT / "results" / "regression_test.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
