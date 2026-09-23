"""λ por longitud de ventana (D-41, punto 1).

Para cada n ∈ NS:
  * λ*_ll: máximo de la log-verosimilitud por interpolación borrada (results/kn_lambda_n{n}.json,
    producido por `kn_background.py lambda --n n`; el perfil se lee de ahí).
  * Calibración leave-both-composers-out con el mismo protocolo de `kn_background.calibrate`
    (200 ventanas del estrato 1750-1830, semilla 20260903), guardando p_comp y p_KN por
    (ventana, obra B) para evaluar el fondo jerárquico en toda la rejilla de λ de una vez.
  * λ*_cal: regla de D-40 aplicada a λ: menor |sesgo| en log entre los λ con pendiente en [0,9, 1,1].
Salida: results/lambda_by_n.csv (una fila por n con λ*, pendiente, MAE_log, obs/pred en λ*_ll),
results/lambda_by_n_grid.csv (métricas para todo (n, λ)), figures/lambda_profile_by_n.png.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402
import background as bgl  # noqa: E402
import kn_background as kb  # noqa: E402

NS = [4, 5, 6, 7, 8, 10, 12]
RES = sl.ROOT / "results"
FIG = sl.ROOT / "figures"
GRID = kb.LAMBDA_GRID
CACHE = RES / "lambda_by_n"   # obs, Σ tb·p_comp, Σ tb·p_KN por n (se regeneran con el script)


def calibrate_grid(n: int, rest_break=0.0, tables=None):
    """Devuelve (obs[q], PC[q, λ-independiente], PS, TB) agregados: pred_hier(λ) = Σ_B tb·(λ·pc + (1−λ)·ps).

    Bucle con los modelos por fuera y las consultas por dentro: cada modelo KN (uno por par de
    compositores (cA, cB) para p_KN, uno por obra B para p_comp) se construye una sola vez y se
    descarta; la memoria queda acotada por Tables + un puñado de modelos, no por 200 × 306."""
    M = kb.Models(kb.CAL_STRATUM, n, tables=tables)
    rng = np.random.default_rng(kb.SEED)
    m = n - 1
    works = sl.load_catalog(exclude_target=True)
    wl = sorted(w for w, r in works.items() if r["period"] in kb.STRATA[kb.CAL_STRATUM])
    per_work, hashes = {}, {}
    for wid in wl:
        wins = kb.work_symbol_windows(wid, m, rest_break)
        if wins:
            per_work[wid] = wins
            hashes[wid] = np.array([kb.order_hashes(s, m)[0] for s in wins], dtype=np.uint64)
    queries = kb.sample_windows(rng, per_work, bgl.N_CAL)
    wlist = sorted(per_work)
    Q = len(queries)
    q_hash = np.array([kb.order_hashes(sym, m)[0] for _, sym in queries], dtype=np.uint64)
    q_comp = [M.T.composer[wa] for wa, _ in queries]
    by_ca = {}                                   # compositor de A -> índices de consulta
    for qi, ca in enumerate(q_comp):
        by_ca.setdefault(ca, []).append(qi)
    by_cb = {}                                   # compositor de B -> obras B
    for wb in wlist:
        by_cb.setdefault(M.T.composer[wb], []).append(wb)
    obs = np.zeros(Q)
    sum_pc = np.zeros(Q)      # Σ_B tb·pc  (pc = ps si el compositor de B no tiene otras obras)
    sum_ps = np.zeros(Q)      # Σ_B tb·ps
    t0 = time.time()
    for ci, (cb, wbs) in enumerate(sorted(by_cb.items())):
        ps = np.zeros(Q)                                        # p_KN(q | estrato sin cA ni cB)
        valid = np.zeros(Q, dtype=bool)
        for ca, qis in by_ca.items():
            if ca == cb:
                continue
            kn_s = M.minus(M.excl_of(ca, cb))                   # un modelo por par (cA, cB)
            for qi in qis:
                ps[qi] = kn_s.prob(queries[qi][1])
            valid[qis] = True
        tb_tot = 0
        for wb in wbs:
            tb = len(per_work[wb])
            obs += valid * np.array([int((hashes[wb] == h).sum()) for h in q_hash])
            incl = M.comp_works.get(cb, set()) - {M.widx[wb]}
            if incl:
                kn_c = M.subset(incl)                           # un modelo por obra B
                pc = np.array([kn_c.prob(queries[qi][1]) if valid[qi] else 0.0 for qi in range(Q)])
            else:
                pc = ps
            sum_pc += tb * np.where(valid, pc, 0.0)
            sum_ps += tb * np.where(valid, ps, 0.0)
            tb_tot += tb
        print(f"  n={n} {cb:14s} {len(wbs):3d} obras {(time.time()-t0)/60:.1f} min", flush=True)
    return obs, sum_pc, sum_ps


def main():
    ns = [int(a) for a in sys.argv[1:] if a.isdigit()] or NS
    T = kb.Tables(kb.CAL_STRATUM)         # ~1-2 GB; se carga UNA vez y se comparte entre todos los n
    if "--only-cache" in sys.argv:        # solo calcular y cachear
        ns = [int(a) for a in sys.argv[1:] if a.isdigit()]
        for n in ns:
            cache = CACHE / f"n{n}.npz"
            if not cache.exists():
                obs, spc, sps = calibrate_grid(n, tables=T)
                CACHE.mkdir(parents=True, exist_ok=True)
                np.savez(cache, obs=obs, spc=spc, sps=sps)
        return
    rows, grid_rows, profiles = [], [], {}
    for n in ns:
        lam_json = json.loads((RES / f"kn_lambda_n{n}.json").read_text())
        ll = {float(k): v for k, v in lam_json["loglik_per_window"].items()}
        profiles[n] = ll
        lam_ll = float(lam_json["lambda"])
        cache = CACHE / f"n{n}.npz"
        if cache.exists():
            z = np.load(cache); obs, spc, sps = z["obs"], z["spc"], z["sps"]
        else:
            obs, spc, sps = calibrate_grid(n, tables=T)
            CACHE.mkdir(parents=True, exist_ok=True)
            np.savez(cache, obs=obs, spc=spc, sps=sps)
        met = {}
        for lam in GRID:
            pred = lam * spc + (1 - lam) * sps
            s, mae, b = kb.metrics(pred, obs)
            met[float(lam)] = (s, mae, b, float(obs.sum() / pred.sum()))
            grid_rows.append(dict(n=n, lam=float(lam), loglik=ll.get(float(lam)), pendiente=s, MAE_log=mae,
                                  sesgo_log=b, obs_pred=obs.sum() / pred.sum()))
        ok = [l for l, v in met.items() if 0.9 <= v[0] <= 1.1]
        lam_cal = min(ok, key=lambda l: abs(met[l][2])) if ok else None
        s, mae, b, op = met[lam_ll]
        rows.append({"n": n, "lambda_star": lam_ll, "lambda_cal_D40": lam_cal, "pendiente": round(s, 4),
                     "MAE_log": round(mae, 4), "sesgo_log": round(b, 4), "obs_pred": round(op, 4),
                     "loglik_por_ventana": round(ll[lam_ll], 4), "n_ventanas_lambda": lam_json["n_windows"],
                     "MAE_log_lambda_cal": round(met[lam_cal][1], 4) if lam_cal is not None else None})
        print(rows[-1], flush=True)
    with open(RES / "lambda_by_n.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    with open(RES / "lambda_by_n_grid.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(grid_rows[0]))
        w.writeheader(); w.writerows(grid_rows)
    # figura: perfil de log-verosimilitud (relativo al máximo) por n, y MAE_log por λ
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    cmap = plt.get_cmap("viridis")
    for i, n in enumerate(ns):
        col = cmap(i / max(len(ns) - 1, 1))
        ll = profiles[n]
        xs = sorted(l for l in ll if 0 < l < 1)
        best = max(ll.values())
        axes[0].plot(xs, [ll[x] - best for x in xs], "o-", ms=3, color=col, label=f"n={n} (λ*={rows[[r['n'] for r in rows].index(n)]['lambda_star']})")
        g = [r for r in grid_rows if r["n"] == n and 0 < r["lam"] < 1]
        axes[1].plot([r["lam"] for r in g], [r["MAE_log"] for r in g], "o-", ms=3, color=col, label=f"n={n}")
    axes[0].set_xlabel("λ"); axes[0].set_ylabel("log-verosimilitud por ventana − máximo")
    axes[0].set_title("Interpolación borrada (20 % de obras de reserva)"); axes[0].grid(alpha=0.3); axes[0].legend(fontsize=8)
    axes[1].set_xlabel("λ"); axes[1].set_ylabel("MAE log (calibración, 200 ventanas)")
    axes[1].set_title("Calibración leave-both-composers-out"); axes[1].grid(alpha=0.3); axes[1].legend(fontsize=8)
    fig.suptitle(f"Perfil de λ por longitud de ventana, estrato {kb.CAL_STRATUM}")
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "lambda_profile_by_n.png", dpi=150)
    print(f"figura en {FIG / 'lambda_profile_by_n.png'}")


if __name__ == "__main__":
    main()
