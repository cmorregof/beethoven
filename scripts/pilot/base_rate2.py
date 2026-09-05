"""Fase 1 - tasa base del motivo de la Quinta. Version streaming.

Procesa obra a obra, acumula contadores y ejecuta las permutaciones en linea,
descartando las secuencias despues. Memoria acotada.
"""

import json
import random
import sys
from collections import Counter, defaultdict

from music21 import chord, converter, corpus, note

TOL = 1e-6
N_PERM = 100
MIN_WINDOWS_FOR_PERM = 150
DEFS = ["D1", "D2", "D3", "D4", "D5"]
TARGETS = ((0, 0, -4), (0, 0, -3))


def voice_sequences(score):
    seqs = []
    parts = score.parts if score.parts else [score]
    for part in parts:
        try:
            flat = part.flatten().notesAndRests
        except Exception:
            continue
        current = []
        for el in flat:
            if isinstance(el, note.Rest):
                if len(current) >= 4:
                    seqs.append(current)
                current = []
                continue
            if isinstance(el, chord.Chord):
                if not el.pitches:
                    continue
                midi = max(p.midi for p in el.pitches)
                tie = el.tie
            elif isinstance(el, note.Note):
                midi = el.pitch.midi
                tie = el.tie
            else:
                continue
            try:
                ql = float(el.duration.quarterLength)
                off = float(el.offset)
            except Exception:
                continue
            if (tie is not None and tie.type in ("stop", "continue")
                    and current and current[-1][0] == midi):
                m, d, o = current[-1]
                current[-1] = (m, d + ql, o)
                continue
            current.append((midi, ql, off))
        if len(current) >= 4:
            seqs.append(current)
    return seqs


def rhythm_ok(d1, d2, d3, d4):
    if d1 <= 0 or d2 <= 0 or d3 <= 0:
        return False
    if abs(d1 - d2) > TOL or abs(d2 - d3) > TOL:
        return False
    return d4 >= 2 * d3 - TOL


def weak_position(offset):
    return abs(offset - round(offset)) > TOL or (round(offset) % 2 == 1)


def process(seqs, ngrams, ngram_rhy, rng):
    """Cuenta patrones observados y devuelve tambien los recuentos nulos."""
    counts = Counter()
    windows = 0
    notes = 0
    null = {k: [0] * N_PERM for k in ("D2", "D3", "D4")}
    do_perm = sum(len(s) for s in seqs) >= MIN_WINDOWS_FOR_PERM

    for seq in seqs:
        notes += len(seq)
        n = len(seq)
        ivs = [seq[i + 1][0] - seq[i][0] for i in range(n - 1)]
        durs = [e[1] for e in seq]
        for i in range(n - 3):
            iv = (ivs[i], ivs[i + 1], ivs[i + 2])
            r = rhythm_ok(durs[i], durs[i + 1], durs[i + 2], durs[i + 3])
            windows += 1
            ngrams[iv] += 1
            ngram_rhy[(iv, r)] += 1
            if iv == (0, 0, -4):
                counts["D1"] += 1
            d2 = iv in TARGETS
            if d2:
                counts["D2"] += 1
            if r:
                counts["D3"] += 1
            if d2 and r:
                counts["D4"] += 1
                if weak_position(seq[i][2]):
                    counts["D5"] += 1

        if do_perm and n >= 4:
            for p in range(N_PERM):
                si = ivs[:]
                sd = durs[:]
                rng.shuffle(si)
                rng.shuffle(sd)
                c2 = c3 = c4 = 0
                for i in range(n - 3):
                    d2 = (si[i], si[i + 1], si[i + 2]) in TARGETS
                    r = rhythm_ok(sd[i], sd[i + 1], sd[i + 2], sd[i + 3])
                    if d2:
                        c2 += 1
                    if r:
                        c3 += 1
                    if d2 and r:
                        c4 += 1
                null["D2"][p] += c2
                null["D3"][p] += c3
                null["D4"][p] += c4

    return counts, windows, notes, null, do_perm


def collection_of(path):
    return str(path).split("corpus/")[-1].split("/")[0]


def main():
    target = sys.argv[1]
    art = {"bach", "beethoven", "mozart", "haydn", "schumann_robert",
           "schumann_clara", "schubert", "chopin", "corelli", "handel",
           "cpebach", "weber", "verdi", "beach", "monteverdi"}
    folk = {"essenFolksong", "ryansMammoth", "oneills1850", "airdsAirs",
            "nottingham-dataset", "miscFolk"}
    wanted = art if target == "art" else folk if target == "folk" else {target}
    paths = [p for p in corpus.getCorePaths() if collection_of(p) in wanted]
    print(f"[{target}] archivos: {len(paths)}", flush=True)

    rng = random.Random(20260903)
    tot = Counter()
    prevalence = Counter()
    ngrams = Counter()
    ngram_rhy = Counter()
    null_tot = {k: [0] * N_PERM for k in ("D2", "D3", "D4")}
    obs_perm = Counter()
    windows = notes = 0
    nworks = perm_works = 0
    failed = 0
    by_col = defaultdict(lambda: {"windows": 0, "counts": Counter(), "works": 0})

    for i, p in enumerate(paths):
        col = collection_of(p)
        try:
            s = converter.parse(p)
            scores = list(s.scores) if getattr(s, "scores", None) else [s]
        except Exception:
            failed += 1
            continue
        for sc in scores:
            try:
                seqs = voice_sequences(sc)
                if not seqs:
                    continue
                c, w, nt, null, did = process(seqs, ngrams, ngram_rhy, rng)
            except Exception:
                failed += 1
                continue
            if w == 0:
                continue
            nworks += 1
            windows += w
            notes += nt
            for k, v in c.items():
                tot[k] += v
                prevalence[k] += 1
            b = by_col[col]
            b["windows"] += w
            b["works"] += 1
            for k, v in c.items():
                b["counts"][k] += v
            if did:
                perm_works += 1
                for k in null_tot:
                    obs_perm[k] += c.get(k, 0)
                    for j in range(N_PERM):
                        null_tot[k][j] += null[k][j]
            del seqs
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(paths)}  obras={nworks}  ventanas={windows:,}", flush=True)

    print(f"\n[{target}] obras: {nworks}   fallos: {failed}")
    print(f"ventanas de 4 notas: {windows:,}")
    print(f"notas:               {notes:,}\n")
    print(f"{'def':<5}{'ocurrencias':>13}{'por 100k vent.':>16}{'obras >=1':>12}{'% obras':>10}")
    for d in DEFS:
        rate = 1e5 * tot[d] / windows if windows else 0
        pct = 100 * prevalence[d] / nworks if nworks else 0
        print(f"{d:<5}{tot[d]:>13,}{rate:>16.2f}{prevalence[d]:>12}{pct:>9.1f}%")

    ranked = ngrams.most_common()
    total_ng = sum(ngrams.values())
    print(f"\n3-gramas de intervalo distintos: {len(ranked):,}")
    for tgt in TARGETS:
        rank = next((k + 1 for k, (g, _) in enumerate(ranked) if g == tgt), None)
        cnt = ngrams.get(tgt, 0)
        print(f"  {tgt}: rango {rank} de {len(ranked):,}  n={cnt:,}  "
              f"({100*cnt/total_ng:.4f}%)")
    print("  top-10:")
    for g, c in ranked[:10]:
        print(f"    {str(g):<16}{c:>9,}  ({100*c/total_ng:.2f}%)")

    print(f"\n{'coleccion':<20}{'obras':>7}{'ventanas':>12}{'D2/100k':>10}{'D4/100k':>10}")
    for col, b in sorted(by_col.items(), key=lambda kv: -kv[1]["windows"]):
        w = b["windows"]
        print(f"{col:<20}{b['works']:>7}{w:>12,}"
              f"{1e5*b['counts']['D2']/w:>10.2f}{1e5*b['counts']['D4']/w:>10.2f}")

    print(f"\nmodelo nulo ({N_PERM} permutaciones intra-voz, {perm_works} obras "
          f"con >={MIN_WINDOWS_FOR_PERM} ventanas)")
    for k in ("D2", "D3", "D4"):
        vals = sorted(null_tot[k])
        mean = sum(vals) / len(vals)
        lo, hi = vals[2], vals[97]
        ge = sum(1 for v in null_tot[k] if v >= obs_perm[k])
        pv = (ge + 1) / (N_PERM + 1)
        ratio = obs_perm[k] / mean if mean else float("nan")
        print(f"  {k}: obs {obs_perm[k]:>8,}   nulo {mean:>10.1f} "
              f"[IC95 {lo:,}-{hi:,}]   ratio {ratio:>5.2f}x   p={pv:.4f}")

    out = {
        "target": target, "works": nworks, "windows": windows, "notes": notes,
        "counts": {d: tot[d] for d in DEFS},
        "prevalence": {d: prevalence[d] for d in DEFS},
        "by_collection": {c: {"works": b["works"], "windows": b["windows"],
                              "counts": dict(b["counts"])} for c, b in by_col.items()},
        "top_ngrams": [[list(g), c] for g, c in ranked[:300]],
        "n_distinct_ngrams": len(ranked),
        "rank_curve": [c for _, c in ranked[:5000]],
        "null": {k: null_tot[k] for k in null_tot},
        "obs_perm": dict(obs_perm),
    }
    with open(f"/home/claude/br_{target}.json", "w") as f:
        json.dump(out, f)
    print(f"\nguardado en br_{target}.json")


if __name__ == "__main__":
    main()
