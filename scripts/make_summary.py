"""Genera results/summary.md (tarea 6) a partir de base_rate.json, uniqueness.json,
works.csv, extract_log.csv y regression_test.md."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402

RES = sl.ROOT / "results"
PILOT_RATES = {"D1": 77.71, "D2": 275.78, "D3": 6367.10, "D4": 16.53, "D5": 13.56}
PILOT_PREV = {"D1": 16.8, "D2": 31.4, "D3": 99.5, "D4": 3.8, "D5": 3.0}
PILOT_NULL_D4 = {"obs": 49, "mean": 51.5, "ratio": 0.95, "p": 0.69}
PILOT_BY_COLL = {"monteverdi": 52.04, "haydn": 74.09, "schumann_robert": 20.84, "beethoven": 8.69,
                 "bach": 7.91, "mozart": 6.05, "oneills1850": 7.15}
PILOT_PCROSS = {"IV": {4: 0.9825, 6: 0.7907, 8: 0.4854, 12: 0.2066},
                "IVR": {4: 0.8719, 6: 0.4646, 8: 0.2630, 12: 0.1715}}


def f(x, nd=2):
    return "—" if x is None else f"{x:,.{nd}f}"


def rate_row(name, s):
    r = s["rate_per_100k"]
    return (f"| {name} | {s['works']:,} | {s['windows']:,} | {f(r['D1'])} | {f(r['D2'])} | {f(r['D3'], 0)} | "
            f"{f(r['D4'])} | {f(r['D5'])} | {f(s['prevalence_pct']['D4'], 1)} % |")


def null_row(name, s):
    n = s["null"]["D4"]
    if not n or n["mean"] is None:
        return f"| {name} | {s['perm_works']} | — | — | — | — | — | — |"
    return (f"| {name} | {s['perm_works']} | {n['obs']:,} | {f(n['mean'], 1)} | {n['ci95'][0]:,}–{n['ci95'][1]:,} | "
            f"{f(n['ratio'])} | {f(n['p'], 3)} | {n.get('n_perm', '')} |")


CLASSES = ["bass_cad", "bass_other", "other_cad", "other_other"]
CLASS_LABEL = {"bass_cad": "bajo, cadencial", "bass_other": "bajo, otra", "other_cad": "otras voces, cadencial",
               "other_other": "otras voces, otra"}


def class_rows(name, s):
    rows = []
    for c in CLASSES:
        x = s["d4_by_class"][c]
        n = x["null"]
        rows.append(f"| {name} | {CLASS_LABEL[c]} | {x['windows']:,} | {x['obs']:,} | {f(x['rate_per_100k'])} | "
                    + (f"{f(n['mean'], 1)} | {f(n['ratio'])} | {f(n['p'], 3)} |" if n else "— | — | — |"))
    return rows


def main():
    br = json.loads((RES / "base_rate.json").read_text())
    un = json.loads((RES / "uniqueness.json").read_text())
    with open(sl.WORKS, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    prim = [r for r in rows if r["is_primary"] == "1" and r["in_analysis"] == "1"]
    works_by = defaultdict(set)
    units_by = Counter()
    for r in prim:
        works_by[(r["collection"].split("/")[0], r["period"])].add(r["work_id"])
        units_by[(r["collection"].split("/")[0], r["period"])] += 1
    colls = sorted({k[0] for k in works_by})
    with open(RES / "extract_log.csv", encoding="utf-8") as fh:
        log = list(csv.DictReader(fh))
    n_fail = sum(1 for r in log if r["status"] == "fail")
    A = br["strata"]["all"]["all"]
    P = br["strata"]["period"]

    L = []
    L.append("# Fase 1 sobre el corpus real — resumen\n")
    L.append(f"Generado por `scripts/make_summary.py` el 2026-09-05. Semilla {br['seed']}, {br['n_perm']} permutaciones "
             f"para `todo` y `period` ({br.get('n_perm_small', 100)} para el resto), `rest_break = {br['rest_break']}`, "
             f"obras objetivo excluidas: {', '.join(br.get('targets_excluded', []))}. Entorno en `results/env.txt`.\n")

    # 1. tamaño
    L.append("## 1. Tamaño del corpus por estrato\n")
    L.append("Unidades primarias en análisis (fichero/movimiento; entre paréntesis, obras `work_id`).\n")
    L.append("| colección | " + " | ".join(sl.PERIODS) + " | total |")
    L.append("|---|" + "---|" * (len(sl.PERIODS) + 1))
    for c in colls:
        cells = []
        tot_u = tot_w = 0
        for p in sl.PERIODS:
            u, w = units_by.get((c, p), 0), len(works_by.get((c, p), ()))
            tot_u += u
            tot_w += w
            cells.append(f"{u} ({w})" if u else "·")
        L.append(f"| {c} | " + " | ".join(cells) + f" | {tot_u} ({tot_w}) |")
    tot = []
    for p in sl.PERIODS:
        u = sum(units_by.get((c, p), 0) for c in colls)
        w = sum(len(works_by.get((c, p), ())) for c in colls)
        tot.append(f"**{u} ({w})**")
    L.append("| **total** | " + " | ".join(tot) + f" | **{len(prim)} ({len({r['work_id'] for r in prim})})** |")
    L.append(f"\nVentanas de 4 notas analizadas: **{A['windows']:,}** en {A['works']:,} obras ({A['notes']:,} notas); "
             f"piloto: 302.414 ventanas en 601 obras. Unidades que no parsean: {n_fail} (`results/extract_log.csv`).\n")
    L.append("| periodo | obras | ventanas | % ventanas |\n|---|---|---|---|")
    for p in sl.PERIODS:
        if p in P:
            L.append(f"| {p} | {P[p]['works']:,} | {P[p]['windows']:,} | {100*P[p]['windows']/A['windows']:.1f} % |")

    # 2. D1-D5 por periodo
    L.append("\n## 2. Tasa base anidada D1–D5 por periodo (ocurrencias por 100k ventanas)\n")
    L.append("| estrato | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |\n|---|---|---|---|---|---|---|---|---|")
    L.append(rate_row("**todo**", A))
    for p in sl.PERIODS:
        if p in P:
            L.append(rate_row(p, P[p]))
    L.append(f"| piloto (music21 art) | 601 | 302,414 | {PILOT_RATES['D1']} | {PILOT_RATES['D2']} | {PILOT_RATES['D3']:.0f} | "
             f"{PILOT_RATES['D4']} | {PILOT_RATES['D5']} | {PILOT_PREV['D4']} % |")
    d4_1750 = {p: P[p]["rate_per_100k"]["D4"] for p in ("1750–1800", "1800–1830") if p in P}
    w1 = sum(P[p]["windows"] for p in d4_1750)
    c1 = sum(P[p]["counts"]["D4"] for p in d4_1750)
    pooled = 1e5 * c1 / w1 if w1 else None
    L.append(f"\n**Estrato 1750–1830 (unión de los dos bins):** D4 = {c1} en {w1:,} ventanas → **{f(pooled)}/100k**, "
             f"frente a **16,53/100k** del piloto (todo el corpus art) y 8,69 (Beethoven), 6,05 (Mozart), 74,1 (Haydn, n=9) "
             f"por colección en el piloto. " + (
                 "La tasa del estrato clásico es **inferior** a la global del piloto. " if pooled is not None and pooled < 0.8 * PILOT_RATES["D4"] else
                 "La tasa del estrato clásico es **superior** a la global del piloto. " if pooled is not None and pooled > 1.25 * PILOT_RATES["D4"] else
                 "La tasa del estrato clásico **coincide en orden de magnitud** con la del piloto. ")
             + "Compárese sobre todo con las colecciones del piloto del mismo periodo (Beethoven, Mozart, Haydn).\n")

    # 3. por colección
    L.append("## 3. Tasa base por colección (≥ 10.000 ventanas)\n")
    L.append("| colección | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |\n|---|---|---|---|---|---|---|---|---|")
    C = sorted(br["strata"]["collection"].items(), key=lambda kv: -kv[1]["windows"])
    for k, s in C:
        if s["windows"] >= 10000:
            L.append(rate_row(k, s))
    L.append("\nPiloto (D4/100k): " + ", ".join(f"{k} {v}" for k, v in PILOT_BY_COLL.items()) + ".\n")

    # 4. por compositor
    L.append("## 4. Tasa base por compositor (≥ 5 obras, ordenado por ventanas)\n")
    L.append("| compositor | obras | ventanas | D1 | D2 | D3 | D4 | D5 | obras con D4 |\n|---|---|---|---|---|---|---|---|---|")
    for k, s in sorted(br["strata"]["composer"].items(), key=lambda kv: -kv[1]["windows"])[:25]:
        L.append(rate_row(k, s))

    # 5. nulo
    L.append("\n## 5. Observado frente al modelo nulo (D4; barajado intra-voz, obras con ≥ 150 notas)\n")
    L.append("| estrato | obras perm. | D4 obs | D4 nulo (media) | IC95 | ratio | p | perms |\n|---|---|---|---|---|---|---|---|")
    L.append(null_row("**todo**", A))
    for p in sl.PERIODS:
        if p in P:
            L.append(null_row(p, P[p]))
    for k, s in C[:12]:
        if s["perm_works"] >= 5:
            L.append(null_row(k, s))
    L.append(f"| piloto (art) | 519 | {PILOT_NULL_D4['obs']} | {PILOT_NULL_D4['mean']} | 36–64 | {PILOT_NULL_D4['ratio']} | {PILOT_NULL_D4['p']} | 100 |")
    # 5b. desgloses D4 (D-32)
    L.append("\n### 5b. D4 por rol de voz y posición cadencial (D-32)\n")
    L.append("Rol: voz de mediana MIDI más baja de cada movimiento = «bajo». Cadencial: la nota larga empieza en la última "
             "negra del compás o precede a silencio/fin de voz. El nulo conserva la clase de cada posición.\n")
    L.append("| estrato | clase | ventanas | D4 obs | D4/100k | nulo (media) | ratio | p |\n|---|---|---|---|---|---|---|---|")
    L += class_rows("**todo**", A)
    for p in sl.PERIODS:
        if p in P:
            L += class_rows(p, P[p])
    tot_obs = A["counts"]["D4"]
    parts = {c: A["d4_by_class"][c] for c in CLASSES}
    excess = {c: (parts[c]["obs"] - parts[c]["null"]["mean"]) if parts[c]["null"] else 0 for c in CLASSES}
    tot_excess = sum(excess.values())
    L.append("\nReparto del exceso observado − nulo (todo): " + ", ".join(
        f"{CLASS_LABEL[c]} {excess[c]:+.0f} ({100*excess[c]/tot_excess:.0f} %)" for c in CLASSES) +
        f". Ventanas por clase: " + ", ".join(f"{CLASS_LABEL[c]} {100*parts[c]['windows']/A['windows']:.1f} %" for c in CLASSES) + ".\n")
    nd = A["null"]
    L.append(f"\nD2: obs {nd['D2']['obs']:,} vs nulo {f(nd['D2']['mean'], 1)} (ratio {f(nd['D2']['ratio'])}, p={f(nd['D2']['p'], 3)}); "
             f"D3: obs {nd['D3']['obs']:,} vs {f(nd['D3']['mean'], 1)} (ratio {f(nd['D3']['ratio'])}, p={f(nd['D3']['p'], 3)}); "
             f"D4: ratio {f(nd['D4']['ratio'])}, p={f(nd['D4']['p'], 3)}. Piloto: D2 0,88×, D3 1,14× (p=0,01), D4 0,95× (p=0,69).\n")

    # 6. n-gramas
    tg = br["target_ngrams"]
    L.append("## 6. Ranking del 3-grama de intervalos\n")
    L.append(f"3-gramas distintos: {br['n_distinct_ngrams']:,} (piloto 9.512). "
             + "; ".join(f"`{k}`: rango {v['rank']}, n={v['count']:,} ({f(v['pct'], 4)} %)" for k, v in tg.items())
             + ". Piloto: (0,0,−4) rango 194, 0,078 %; (0,0,−3) rango 83, 0,198 %.\n")
    L.append("Top-10: " + ", ".join(f"`{tuple(g)}` {c:,}" for g, c in br["top_ngrams"][:10]) + ".\n")

    # 7. unicidad
    L.append("## 7. Curva de unicidad P_cross(n)\n")
    L.append(f"{un['works']:,} obras. P_cross(n) = probabilidad de que una ventana de n notas aparezca idéntica en otra obra.\n")
    L.append("| n | IV tokens | IV tipos | IV P_cross | IV piloto | IV P_pair | IVR tokens | IVR tipos | IVR P_cross | IVR piloto | IVR P_pair |\n|---|---|---|---|---|---|---|---|---|---|---|")
    civ = {d["n"]: d for d in un["curve"]["IV"]}
    civr = {d["n"]: d for d in un["curve"]["IVR"]}
    for n in un["ns"]:
        a, b = civ[n], civr[n]
        L.append(f"| {n} | {a['tokens']:,} | {a['types']:,} | {f(a['p_cross'], 4)} | {PILOT_PCROSS['IV'].get(n, '')} | {f(a.get('p_pair'), 5)} | "
                 f"{b['tokens']:,} | {b['types']:,} | {f(b['p_cross'], 4)} | {PILOT_PCROSS['IVR'].get(n, '')} | {f(b.get('p_pair'), 5)} |")
    L.append("\n`P_pair(n)` (D-33) = probabilidad de que una ventana de A aparezca en una obra B concreta del mismo estrato, "
             "promediada sobre pares; no depende del número de obras.\n")
    L.append("Aviso (D-33): `P_pair` pondera por ventanas, así que en los estratos orquestales (1750–1830) lo dominan "
             "n-gramas formularios de acompañamiento (notas repetidas, trémolos, escalas) que aparecen en casi todas las "
             "sinfonías; el diagnóstico por pares no encontró duplicados (contención máxima 5 % entre obras distintas). "
             "Para el E-value convendrá una versión ponderada por tipos o que excluya los n-gramas de nota repetida.\n")
    L.append("P_cross(n) y P_pair(n) por periodo (IVR = intervalos + ritmo), dentro de cada periodo:\n")
    L.append("| periodo | obras | P_cross n=4 | n=6 | n=8 | n=12 | P_pair n=4 | n=6 | n=8 | n=12 |\n|---|---|---|---|---|---|---|---|---|---|")
    for p in sl.PERIODS:
        cp = un["curve_by_period"].get("IVR", {}).get(p)
        if not cp or not cp[0]["tokens"]:
            continue
        d = {x["n"]: x for x in cp}
        L.append(f"| {p} | {un['works_by_period'].get(p, 0)} | " + " | ".join(f(d[n]["p_cross"], 3) for n in (4, 6, 8, 12))
                 + " | " + " | ".join(f(d[n].get("p_pair"), 5) for n in (4, 6, 8, 12)) + " |")

    # 8. fechas y anomalías
    all_works = {}
    for r in rows:
        all_works.setdefault(r["work_id"], r)
    ys = Counter(r["year_source"] for r in all_works.values())
    unk = sum(1 for r in prim if r["period"] == "unknown")
    L.append("\n## 8. Obras sin fecha\n")
    ps = Counter(r["period_source"] for r in all_works.values())
    L.append(f"Origen de la fecha por obra: " + ", ".join(f"{k} {v}" for k, v in ys.most_common()) + ". "
             f"Asignación de periodo: " + ", ".join(f"{k} {v}" for k, v in ps.most_common()) + " (D-30: rangos por punto medio). "
             f"Unidades en `unknown`: {unk} de {len(prim)} ({100*unk/len(prim):.0f} %), casi todas Lieder cuyo compositor cruza un bin. "
             f"`corpus/manual_dates.csv` ingerido ({sum(1 for _ in open(sl.ROOT/'corpus'/'manual_dates.csv'))-1} obras); "
             f"detalle en `results/missing_dates.md`.\n")
    L.append("## 9. Anomalías y avisos\n")
    n_np = sum(1 for r in rows if r["is_primary"] != "1")
    n_seq = len({r["work_id"] for r in rows if "seq:" in r["duplicate_group"] and r["is_primary"] != "1"})
    L.append(f"- **Duplicados entre colecciones**: {n_np:,} unidades no primarias por clave de catálogo o por hash de secuencia "
             f"({n_seq} obras por hash, D-29: ediciones MuseData, kern vs MuseData, OpenScore vs kern/DCML); prioridad "
             "DCML > MuseData > kern > S3 > OpenScore. Lista en `results/seq_duplicates.md`.")
    L.append("- **Movimientos partidos**: el finale de la Novena está en 8 secciones MuseData (un solo `work_id`); WTC = pareja preludio+fuga; "
             "en OpenScore un fichero puede contener todos los movimientos (Beethoven op. 18) o uno (Dvořák).")
    L.append("- **OMR/transcripción**: OpenScore es transcripción humana desde IMSLP (sin OMR), pero 7 cuartetos no importan en music21 y 39 carpetas "
             "carecen de partitura. MuseData: 20 movimientos con datos corruptos. Instrumentos transpositores en altura escrita (sin efecto, D-14).")
    L.append("- **Voces dobladas**: colapsadas en el 20 % de las unidades (orquesta y continuo); ver `results/extract_summary.md`.")
    L.append("- **Unidad de obra**: prevalencia «obras con D4» no es comparable con el piloto (allí obra = fichero, aquí obra completa).")
    L.append("- **Test de regresión**: `results/regression_test.md` (m21_bach reproduce el piloto: D2 +1,2 %, D4 +1,9 %).")
    L.append("\nFiguras: `results/fig/base_rate_strata.png`, `results/fig/observed_vs_null.png`, `results/fig/p_cross.png`.")
    (RES / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
