"""Fase 1b - Curva de unicidad por longitud.

Para n = 3..12 mide, en dos representaciones:
  IV   solo intervalos (transposicion-invariante)
  IVR  intervalos + clase ritmica (ratio de duracion cuantizado)

  - n-gramas distintos
  - fraccion de TIPOS que aparecen en una sola obra
  - P_cross(n): fraccion de VENTANAS cuyo n-grama aparece tambien en otra obra
    distinta.  Es la tasa base de "coincidencia de longitud n entre dos obras",
    el insumo directo del E-value.

Memoria: por n-grama guarda (primera obra, visto_en_otra) y el numero de tokens.
"""

import json
import sys
from collections import defaultdict

from music21 import chord, converter, corpus, note

NS = list(range(3, 13))


def voice_sequences(score):
    seqs = []
    parts = score.parts if score.parts else [score]
    for part in parts:
        try:
            flat = part.flatten().notesAndRests
        except Exception:
            continue
        cur = []
        for el in flat:
            if isinstance(el, note.Rest):
                if len(cur) >= 4:
                    seqs.append(cur)
                cur = []
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
            except Exception:
                continue
            if (tie is not None and tie.type in ("stop", "continue")
                    and cur and cur[-1][0] == midi):
                cur[-1] = (midi, cur[-1][1] + ql)
                continue
            cur.append((midi, ql))
        if len(cur) >= 4:
            seqs.append(cur)
    return seqs


def rclass(d_prev, d):
    """Clase ritmica del ratio d/d_prev: -2 mucho mas corta, -1 mas corta,
    0 igual, 1 mas larga, 2 mucho mas larga."""
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

    # tables[rep][n][gram] = [first_work, seen_other, tokens]
    tables = {"IV": {n: {} for n in NS}, "IVR": {n: {} for n in NS}}
    tokens = {"IV": defaultdict(int), "IVR": defaultdict(int)}
    nworks = 0

    for i, p in enumerate(paths):
        try:
            s = converter.parse(p)
            scores = list(s.scores) if getattr(s, "scores", None) else [s]
        except Exception:
            continue
        for j, sc in enumerate(scores):
            try:
                seqs = voice_sequences(sc)
            except Exception:
                continue
            if not seqs:
                continue
            wid = nworks
            nworks += 1
            for seq in seqs:
                ivs = [seq[k + 1][0] - seq[k][0] for k in range(len(seq) - 1)]
                rcs = [rclass(seq[k][1], seq[k + 1][1]) for k in range(len(seq) - 1)]
                L = len(ivs)
                for n in NS:
                    m = n - 1  # n notas = n-1 intervalos
                    if L < m:
                        continue
                    tab_iv = tables["IV"][n]
                    tab_ivr = tables["IVR"][n]
                    for k in range(L - m + 1):
                        g = tuple(ivs[k:k + m])
                        e = tab_iv.get(g)
                        if e is None:
                            tab_iv[g] = [wid, False, 1]
                        else:
                            e[2] += 1
                            if e[0] != wid:
                                e[1] = True
                        tokens["IV"][n] += 1
                        g2 = (g, tuple(rcs[k:k + m]))
                        e = tab_ivr.get(g2)
                        if e is None:
                            tab_ivr[g2] = [wid, False, 1]
                        else:
                            e[2] += 1
                            if e[0] != wid:
                                e[1] = True
                        tokens["IVR"][n] += 1
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(paths)} obras={nworks}", flush=True)

    print(f"\n[{target}] obras: {nworks}\n")
    out = {"target": target, "works": nworks, "curve": {}}
    for rep in ("IV", "IVR"):
        print(f"representacion {rep}")
        print(f"{'n':>3}{'ventanas':>10}{'tipos':>10}{'tipos unicos':>14}"
              f"{'% tipos 1 obra':>16}{'P_cross':>10}")
        out["curve"][rep] = []
        for n in NS:
            tab = tables[rep][n]
            tok = tokens[rep][n]
            ntypes = len(tab)
            uniq_types = sum(1 for e in tab.values() if not e[1])
            shared_tokens = sum(e[2] for e in tab.values() if e[1])
            pct_uniq = 100 * uniq_types / ntypes if ntypes else 0
            p_cross = shared_tokens / tok if tok else 0
            print(f"{n:>3}{tok:>10,}{ntypes:>10,}{uniq_types:>14,}"
                  f"{pct_uniq:>15.1f}%{p_cross:>10.4f}")
            out["curve"][rep].append({"n": n, "tokens": tok, "types": ntypes,
                                      "unique_types": uniq_types,
                                      "p_cross": p_cross})
        print()

    # el motivo de la Quinta extendido: cuantas notas del incipit real
    # (G G G Eb | F F F D) hacen falta para que sea unico en el corpus
    fifth = [0, 0, -4, 2, 0, 0, -3]   # intervalos del incipit (8 notas)
    print("incipit de la Quinta (8 notas, 7 intervalos): obras que lo contienen")
    for n in NS:
        m = n - 1
        if m > len(fifth):
            break
        g = tuple(fifth[:m])
        e = tables["IV"][n].get(g)
        if e is None:
            print(f"  n={n}: 0 obras")
        else:
            print(f"  n={n}: tokens={e[2]}, en {'varias obras' if e[1] else '1 obra'}")

    with open(f"/home/claude/uniq_{target}.json", "w") as f:
        json.dump(out, f)
    print(f"\nguardado en uniq_{target}.json")


if __name__ == "__main__":
    main()
