"""Sensibilidad a cita literal de los umbrales congelados n = 8 con los pares Le Cène → Dawson.

Pares (A = original, B = arreglo literal para teclado del Anne Dawson's Book):
  A = musedata_vivaldi-lecene-op3-rvX, B = musedata_vivaldi-dawson-op3-rvX, X ∈ {230, 265, 519, 567}.

LS-1 (principal). Instancia = tipo de ventana de 8 notas (7-grama IVR, rest_break 0, misma
simbolización que thresholds_n8.windows_with_movement) de A presente en B. Para cada instancia,
exactamente como scripts/thresholds_n8.py: DF = M.df(s, cA, cB), E = ventanas_B · M.p_hier(s, cA, cB,
M.widx[wB]) con M = Models("1750-1830", 8, 0.45). t_DF y t_E se leen de results/thresholds_n8.json.
Vivaldi no tiene obras en el estrato 1750-1830: comp_works["vivaldi_a"] está vacío, así que
excl_of(cA, cB) = ∅ (fondo = estrato completo) y p_comp devuelve None, con lo que p_hier = p_KN del
estrato (el término de compositor desaparece; ninguna fórmula cambia). El script lo comprueba y lo
anota en el JSON. Variante secundaria "noBeethoven": cA = "beethoven_l" en la ranura de exclusión
(DF y p_KN sin Beethoven, el fondo del caso objetivo menos Cherubini; véase caveats).

LS-2 (secundaria). Potencia del test de fragmentos: 200 fragmentos contiguos de A (todas las voces)
por par y longitud (10, 15, 20 compases convertidos a ventanas con las ventanas por compás de A);
estadístico = tipos del fragmento presentes en S_B = {tipos de B con DF ≤ t_DF}; nulo = 1000
fragmentos de la misma longitud en ventanas de obras de cuerda < 1750 de otros compositores
(POOL_PREFIXES), mismo B; p = fracción de nulos ≥ observado; potencia = fracción con p ≤ 0,025.

Guardia: aborta si cualquier obra tocada es objetivo o de Cherubini; los únicos A/B permitidos son
los 8 work_id de PAIRS. Le Cène op. 3 no es primaria (duplicado de Dawson en el catálogo) y no está
en la caché del repo: si falta, se extrae con scripts/extract.py (mismo código, sin cambios) a una
caché local de W (corpus/cache, ignorada por git).

Uso: BEETHOVEN_ROOT=<M> <M>/.venv/bin/python scripts/literal_sensitivity_n8.py --out-dir results
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import resource
import sys
import time
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import preregistration_guard as guard  # noqa: E402
import confirmatory_n8 as cf  # noqa: E402

N, LAM, STRATUM, M_ORD, SEED = cf.N, cf.LAM, cf.STRATUM, cf.M_ORD, cf.SEED
RVS = (230, 265, 519, 567)
PAIRS = [(f"L{x}", f"musedata_vivaldi-lecene-op3-rv{x}", f"musedata_vivaldi-dawson-op3-rv{x}") for x in RVS]
ALLOWED_AB = frozenset(w for _, a, b in PAIRS for w in (a, b))
VIVALDI = "vivaldi_a"
BEETHOVEN = "beethoven_l"
VARIANTS = {"default": None, "noBeethoven": BEETHOVEN}   # ranura cA de exclusión (None = compositor de A)
LENGTHS_BARS = (10, 15, 20)
N_OBS, N_NULL_LS2, ALPHA_LS2 = 200, 1000, 0.025
# Piscina del nulo de LS-2: conjuntos de cuerda (dos violines/ripieno + continuo) < 1750, sin Vivaldi.
POOL_PREFIXES = ("musedata_corelli-chry-concerto-", "musedata_corelli-chry-trio-", "dcml-corelli-op-",
                 "musedata_handel-brit-orch-op06-", "musedata_handel-haa-op6n")
CAVEATS = [
    "La sensibilidad de LS-1/LS-2 con Dawson/Le Cène es una cota superior para cita literal con cambio "
    "de dominio: arreglos literales para teclado de conciertos de cuerda del estrato <1750, frente a "
    "umbrales (t_DF, t_E) calibrados en cuartetos de cuerda 1750-1830.",
    "Vivaldi no tiene obras en el estrato 1750-1830: el término de compositor del fondo jerárquico es "
    "nulo (p_comp = None) y p_hier = p_KN del estrato; la exclusión por defecto no quita ninguna obra.",
    "La variante noBeethoven quita Beethoven del fondo pero no nombra a Cherubini (la API de Models solo tiene "
    "dos ranuras de exclusión, cA y cB, y cB debe ser el compositor de B). Cherubini no tiene obras en las tablas "
    "de fondo (su única obra es objetivo y está excluida), así que noBeethoven equivale al fondo del caso objetivo.",
    "Instancias = tipos compartidos, correlacionados dentro de cada par: los IC de Wilson tratan las "
    "instancias como independientes y son optimistas.",
    "Le Cène op. 3 (no primaria) se extrajo con scripts/extract.py sin cambios a una caché local no versionada.",
]


# ----------------------------------------------------------------------------
# funciones puras
# ----------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """IC de Wilson 95 % para k éxitos en n ensayos."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": int(k), "n": int(n), "rate": (k / n) if n else float("nan"), "wilson95": [lo, hi]}


def shared_instances(A: cf.WorkWindows, B: cf.WorkWindows) -> list[dict]:
    """Tipos de A presentes en B, con ocurrencias y movimientos de A (como thresholds_n8)."""
    hb: dict[int, int] = {}
    for h in B.hashes.tolist():
        hb[h] = hb.get(h, 0) + 1
    seen: dict[int, dict] = {}
    for i, h in enumerate(A.hashes.tolist()):
        if h in hb:
            r = seen.setdefault(h, {"hash": h, "sym": A.syms[i], "occ_A": 0, "mv_A": set(), "occ_B": hb[h]})
            r["occ_A"] += 1
            r["mv_A"].add(int(A.mov[i]) + 1)
    return list(seen.values())


def summarize(rows: Sequence[Mapping], t_df: float, t_e: float, by: str = "pair") -> dict:
    """Sensibilidad DF, E y combinada (DF y E) global y por grupo, con IC de Wilson."""
    def block(rs):
        n = len(rs)
        kd = sum(r["DF"] <= t_df for r in rs)
        ke = sum(r["E"] <= t_e for r in rs)
        kb_ = sum((r["DF"] <= t_df) and (r["E"] <= t_e) for r in rs)
        knu = sum((r["DF"] <= t_df) and not r["uniform_rhythm"] for r in rs)
        kbnu = sum((r["DF"] <= t_df) and (r["E"] <= t_e) and not r["uniform_rhythm"] for r in rs)
        return {"instances": n, "DF": rate(kd, n), "E": rate(ke, n), "combined": rate(kb_, n),
                "pass_DF_nonuniform": int(knu), "pass_both_nonuniform": int(kbnu),
                "min_DF": float(min((r["DF"] for r in rs), default=float("nan"))),
                "min_E": float(min((r["E"] for r in rs), default=float("nan")))}
    out = {"global": block(rows), "per_" + by: {}}
    for g in sorted({r[by] for r in rows}):
        out["per_" + by][g] = block([r for r in rows if r[by] == g])
    return out


def select_string_pool(rows: Iterable[Mapping], prefixes=POOL_PREFIXES) -> list[str]:
    """work_id de la piscina del nulo LS-2: < 1750, primarias, en análisis, sin Vivaldi, prefijos de cuerda."""
    ok = guard.filter_catalog_rows(list(rows))
    out = []
    for r in ok:
        if (r.get("period") == "<1750" and str(r.get("is_primary")) == "1" and str(r.get("in_analysis")) == "1"
                and r.get("composer_id") != VIVALDI and str(r.get("work_id", "")).startswith(tuple(prefixes))):
            out.append(r["work_id"])
    return sorted(set(out))


def check_touched(ab_ids: Iterable[str], pool_ids: Iterable[str], catalog_rows: Iterable[Mapping],
                  allowed_ab=ALLOWED_AB, context="literal_sensitivity_n8") -> None:
    """Guardia: A/B solo de la lista permitida; todo lo tocado sin objetivos ni Cherubini."""
    ab_ids, pool_ids = list(ab_ids), list(pool_ids)
    guard.check_ids(ab_ids + pool_ids, context=context)
    guard.check_catalog_rows(list(catalog_rows), context=context)
    bad = [w for w in ab_ids if w not in allowed_ab]
    if bad:
        raise guard.PreregistrationViolation(f"ABORTADO: A/B no permitido en {context}: {bad}")
    if set(pool_ids) & set(allowed_ab):
        raise guard.PreregistrationViolation(f"ABORTADO: A/B dentro de la piscina del nulo en {context}")


def ls2_power(obs_counts: Sequence[int], null_counts: Sequence[int], alpha: float = ALPHA_LS2) -> dict:
    null = np.asarray(null_counts)
    ps = np.array([cf.p_value(o, null) for o in obs_counts])
    k = int((ps <= alpha).sum())
    return {"power": rate(k, len(ps)), "obs_mean": float(np.mean(obs_counts)), "obs_median": float(np.median(obs_counts)),
            "null_mean": float(null.mean()), "null_q95": float(np.quantile(null, 0.95)), "null_max": int(null.max()),
            "p_median": float(np.median(ps))}


# ----------------------------------------------------------------------------
# datos reales
# ----------------------------------------------------------------------------
def ensure_extracted(root: Path, wids: Sequence[str], extra_cache: Path, catalog_csv: Path) -> list[dict]:
    """Extrae con scripts/extract.py (sin cambios) las obras sin caché en root ni en extra_cache."""
    todo = [w for w in wids if not (root / "corpus" / "cache" / f"{w}.npz").exists()
            and not (extra_cache / f"{w}.npz").exists()]
    if not todo:
        return []
    guard.check_ids(todo, context="ensure_extracted")
    import extract as ex
    if Path(ex.__file__).resolve().parent != root / "scripts":
        raise RuntimeError(f"extract importado desde {ex.__file__}")
    ex.CACHE = extra_cache
    with open(catalog_csv, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["work_id"] in set(todo)]
    guard.check_catalog_rows(rows, context="ensure_extracted")
    logs = []
    for w in todo:
        units = [r for r in rows if r["work_id"] == w]
        logs += ex.extract_work((w, units, 0.0, False))
    return logs


def smoke_p07(sl, kb, M, root: Path, n_rows: int = 20) -> dict:
    """Recalcula DF y E de las primeras filas de P07 y las compara con results/thresholds_n8_windows.csv."""
    with open(root / "results" / "thresholds_n8_windows.csv", encoding="utf-8") as fh:
        ref = [r for r in csv.DictReader(fh) if r["pair"] == "P07"][:n_rows]
    wa, wb = ref[0]["work_A"], ref[0]["work_B"]
    guard.check_ids([wa, wb], context="smoke_p07")
    ca, cb = M.T.composer[wa], M.T.composer[wb]
    A = cf.real_windows(sl, kb, wa, ca)
    B = cf.real_windows(sl, kb, wb, cb)
    ia = cf.type_index(A)
    res = []
    for r in ref:
        h = int(r["hash"])
        s = A.syms[ia[h]] if h in ia else None
        if s is None:
            res.append(dict(hash=h, ok=False, why="hash ausente")); continue
        df = M.df(s, ca, cb)
        E = len(B) * M.p_hier(s, ca, cb, M.widx[wb])
        okd = math.isclose(df, float(r["DF"]), rel_tol=1e-9, abs_tol=1e-15)
        oke = math.isclose(E, float(r["E"]), rel_tol=1e-9, abs_tol=1e-15)
        res.append(dict(hash=h, DF=df, DF_ref=float(r["DF"]), E=E, E_ref=float(r["E"]),
                        windows_B=len(B), windows_B_ref=int(r["windows_B"]),
                        ok=bool(okd and oke and len(B) == int(r["windows_B"]))))
    return {"pair": "P07", "rows_checked": len(res), "all_ok": all(x["ok"] for x in res), "rows": res}


def git_head(path: Path) -> str | None:
    import subprocess
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--extra-cache", type=Path, default=_HERE.parent / "corpus" / "cache",
                    help="caché local (no versionada) para obras no primarias extraídas aquí")
    ap.add_argument("--skip-ls2", action="store_true")
    ap.add_argument("--smoke-only", action="store_true")
    ap.add_argument("--spec-commit", default=None, help="commit de la torre que registra la especificación")
    args = ap.parse_args(argv)
    t0 = time.time()
    root = cf.beethoven_root()
    catalog_csv = root / "corpus" / "works.csv"
    with open(catalog_csv, encoding="utf-8") as fh:
        all_rows = list(csv.DictReader(fh))
    ab_ids = [w for _, a, b in PAIRS for w in (a, b)]
    pool_ids = select_string_pool(all_rows)
    touched_rows = [r for r in all_rows if r["work_id"] in set(ab_ids) | set(pool_ids)]
    check_touched(ab_ids, pool_ids, touched_rows)
    comp_of = {r["work_id"]: r["composer_id"] for r in touched_rows}
    t_df, t_e = cf.read_thresholds(root)

    sl, kb = cf.load_pipeline()
    args.extra_cache.mkdir(parents=True, exist_ok=True)
    extract_logs = ensure_extracted(root, [a for _, a, _ in PAIRS], args.extra_cache, catalog_csv)

    t_load = time.time()
    M = kb.Models(STRATUM, N, LAM)
    timing = {"load_models_s": round(time.time() - t_load, 1)}
    smoke = smoke_p07(sl, kb, M, root)
    out = {"n": N, "lambda": LAM, "stratum": STRATUM, "t_DF": t_df, "t_E": t_e,
           "thresholds_source": "results/thresholds_n8.json", "pairs": [dict(id=p, A=a, B=b) for p, a, b in PAIRS],
           "caveats": CAVEATS, "smoke_P07": smoke, "extract_logs": extract_logs,
           "spec_commit": args.spec_commit, "head_commit": git_head(_HERE.parent),
           "beethoven_root": str(root)}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    jpath = args.out_dir / "literal_sensitivity_n8.json"
    if not smoke["all_ok"]:
        jpath.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print("PRUEBA DE HUMO FALLIDA: DF/E de P07 no coinciden con thresholds_n8_windows.csv", file=sys.stderr)
        raise SystemExit(5)
    print(f"prueba de humo P07: {smoke['rows_checked']} filas idénticas", flush=True)
    if args.smoke_only:
        jpath.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        return out

    # comprobación Vivaldi / estrato
    viv = {"comp_works_vivaldi": len(M.comp_works.get(VIVALDI, set())),
           "excl_default": len(M.excl_of(VIVALDI, VIVALDI)), "excl_noBeethoven": len(M.excl_of(BEETHOVEN, VIVALDI)),
           "n_works_stratum": M.n_works, "widx_B": {b: M.widx.get(b) for _, _, b in PAIRS},
           "A_in_tables": {a: a in M.widx for _, a, _ in PAIRS}}
    for _, _, b in PAIRS:
        if comp_of[b] != VIVALDI or M.widx.get(b) is None:
            raise SystemExit(f"supuesto roto: {b} no es de Vivaldi o no está en meta.json")
    viv["p_comp_is_None"] = all(M.p_comp(np.zeros(M_ORD, np.int64) + 1602, VIVALDI, M.widx[b]) is None for _, _, b in PAIRS)
    out["vivaldi_check"] = viv

    # ventanas
    W = {}
    for p, a, b in PAIRS:
        W[a] = cf.real_windows(sl, kb, a, comp_of[a], args.extra_cache)
        W[b] = cf.real_windows(sl, kb, b, comp_of[b], args.extra_cache)
    out["windows"] = {w: {"windows": len(x), "bars": x.n_bars} for w, x in W.items()}

    # LS-1 y DF de todos los tipos de B (para LS-2)
    t1 = time.time()
    rows, dfsB = [], {}
    for var, slot in VARIANTS.items():
        for p, a, b in PAIRS:
            A, B = W[a], W[b]
            cA, cB = (slot or comp_of[a]), comp_of[b]
            wB = M.widx[b]
            tb = len(B)
            dfsB[(var, p)] = {h: M.df(B.syms[i], cA, cB) for h, i in cf.type_index(B).items()}
            for r in shared_instances(A, B):
                s = r["sym"]
                ivs = (s // 8 - 200).tolist(); rcs = (s % 8 - 2).tolist()
                DF, E = dfsB[(var, p)][r["hash"]], tb * M.p_hier(s, cA, cB, wB)
                rows.append(dict(variant=var, pair=p, work_A=a, work_B=b, hash=r["hash"], occ_A=r["occ_A"],
                                 occ_B=r["occ_B"], mov_A="|".join(map(str, sorted(r["mv_A"]))), windows_B=tb,
                                 DF=DF, E=E, E_laplace=tb * M.p_laplace(s, cA, cB),
                                 intervals=" ".join(map(str, ivs)), rclass=" ".join(map(str, rcs)),
                                 uniform_rhythm=int(len(set(rcs)) == 1 and rcs[0] == 0),
                                 pass_DF=int(DF <= t_df), pass_E=int(E <= t_e), pass_both=int(DF <= t_df and E <= t_e)))
            print(f"LS-1 {var} {p}: {sum(1 for x in rows if x['variant'] == var and x['pair'] == p)} tipos compartidos",
                  flush=True)
    timing["ls1_s"] = round(time.time() - t1, 1)
    with open(args.out_dir / "literal_sensitivity_n8.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    out["LS1"] = {var: summarize([r for r in rows if r["variant"] == var], t_df, t_e) for var in VARIANTS}

    # LS-2
    if not args.skip_ls2:
        t2 = time.time()
        pool = [cf.real_windows(sl, kb, w, comp_of[w], args.extra_cache) for w in pool_ids]
        pool = [x for x in pool if len(x)]
        rng = np.random.default_rng(SEED)
        S = {k: np.array(sorted(h for h, d in v.items() if d <= t_df), dtype=np.uint64) for k, v in dfsB.items()}
        ls2 = {var: {} for var in VARIANTS}
        for p, a, b in PAIRS:
            A = W[a]
            for Lb in LENGTHS_BARS:
                Lw = cf.length_in_windows(A, Lb, "bars")
                obs = cf.sample_fragments(A, Lw, N_OBS, rng)
                nul, _src = cf.sample_null_fragments(pool, Lw, N_NULL_LS2, rng)
                for var in VARIANTS:
                    oc = [cf.count_statistic(f, S[(var, p)]) for f in obs]
                    nc = [cf.count_statistic(f, S[(var, p)]) for f in nul]
                    r = ls2_power(oc, nc) if obs and len(nul) == N_NULL_LS2 else {"error": "sin fragmentos"}
                    r.update(length_bars=Lb, length_windows=Lw, n_obs=len(obs), n_null=len(nul),
                             S_B_size=int(len(S[(var, p)])))
                    ls2[var].setdefault(p, {})[str(Lb)] = r
                print(f"LS-2 {p} {Lb} compases ({Lw} ventanas): potencia "
                      f"{ls2['default'][p][str(Lb)].get('power', {}).get('rate')}", flush=True)
        for var in VARIANTS:                                   # agregado por longitud
            for Lb in LENGTHS_BARS:
                k = sum(ls2[var][p][str(Lb)]["power"]["k"] for p, _, _ in PAIRS if "power" in ls2[var][p][str(Lb)])
                n = sum(ls2[var][p][str(Lb)]["power"]["n"] for p, _, _ in PAIRS if "power" in ls2[var][p][str(Lb)])
                ls2[var].setdefault("all_pairs", {})[str(Lb)] = {"power": rate(k, n)}
        out["LS2"] = {"pool": pool_ids, "pool_size_used": len(pool), "pool_windows": int(sum(len(x) for x in pool)),
                      "pool_rule": f"period <1750, primary, in_analysis, composer != vivaldi_a, prefijos {list(POOL_PREFIXES)}",
                      "seed": SEED, "n_obs": N_OBS, "n_null": N_NULL_LS2, "alpha": ALPHA_LS2,
                      "results": ls2}
        timing["ls2_s"] = round(time.time() - t2, 1)
    timing["total_s"] = round(time.time() - t0, 1)
    timing["ru_maxrss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss   # macOS: bytes
    out["timing"] = timing
    jpath.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"LS1": {v: {k: out["LS1"][v]["global"][k] for k in ("instances", "DF", "E", "combined")}
                              for v in VARIANTS}, "timing": timing}, indent=1, ensure_ascii=False))
    return out


if __name__ == "__main__":
    main()
