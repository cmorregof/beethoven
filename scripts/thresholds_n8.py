"""Umbrales de E y DF para n = 8 sin usar la obra objetivo (D-41, punto 2).

Instancia = tipo de ventana de 8 notas (7-grama IVR) de la obra A que también aparece en la obra B.
  positivos: tipos compartidos en pares con préstamo/modelado documentado cuyas dos obras están en
             el corpus (controls_positive_candidates.csv: P07–P10). Ningún par incluye a Cherubini
             ni a Beethoven op. 67 (el script aborta si aparecen).
  negativos: tipos compartidos en pares sin relación documentada, emparejados por franja temporal
             de A y B e instrumentación (cuarteto de cuerda), en igual número de pares.
Para cada instancia: DF (fracción de obras del estrato 1750-1830 sin los compositores de A ni B que
contienen q) y E = ventanas_B · p_jerárquico(q), λ = 0,45 (D-40).
Umbrales: DF ≤ t_DF con t_DF = mayor valor con FPR ≤ 5 % en los negativos; E ≤ t_E con t_E = percentil
5 de E en el nulo estratificado (= percentil 95 de −log E), siendo el nulo los pares negativos.
Salida: results/thresholds_n8.json, results/thresholds_n8_windows.csv, figures/roc_pr_n8.png
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqlib as sl  # noqa: E402
import kn_background as kb  # noqa: E402

N, LAM, STRATUM = 8, 0.45, "1750-1830"
M_ORD = N - 1
RES, FIG = sl.ROOT / "results", sl.ROOT / "figures"
FORBIDDEN = ("cherubini", "sym5", "op67", "op-67")

POS = [  # id, A, B, cita
    ("P07", "musedata_mozart-bhl-qrtets-k464", "dcml_abc-n05op18-5", "Kerman, The Beethoven Quartets (1967), cap. 2"),
    ("P08", "dcml_abc-n15op132", "dcml-mendelssohn_quartets-op-13", "Todd, Mendelssohn: A Life in Music (2003); Krummacher (1978)"),
    ("P09", "dcml_abc-n11op95", "dcml-mendelssohn_quartets-op-13", "Todd (2003)"),
    ("P10", "dcml_abc-n10op74", "dcml-mendelssohn_quartets-op-12", "Todd (2003)"),
]
NEG = [  # emparejado con, A, B, criterio
    ("N07", "kern-humdrum-haydn-quartets-op64n5", "dcml_abc-n05op18-5", "cuarteto 1750-1800 → mismo B que P07"),
    ("N08", "osq-13145872", "dcml-mendelssohn_quartets-op-13", "Schubert D.804 (1824), cuarteto 1800-1830 → mismo B que P08"),
    ("N09", "osq-5116346", "dcml-mendelssohn_quartets-op-13", "Arriaga n.º 1 (1823), cuarteto 1800-1830 → mismo B que P09"),
    ("N10", "osq-5108909", "dcml-mendelssohn_quartets-op-12", "Schubert D.810 (1824), cuarteto 1800-1830 → mismo B que P10"),
]


def windows_with_movement(wid):
    d = sl.load_work(wid)
    out = []
    for mv, _v, _b, arr in sl.sequences_ex(d, 0.0):
        sym, _, _ = kb.symbols_of(arr[:, :3])
        for k in range(len(sym) - M_ORD + 1):
            out.append((mv, sym[k:k + M_ORD]))
    return out


def roc(score, y):
    """score alto = más sospechoso.  Devuelve fpr, tpr, precision, recall, auc, ap."""
    order = np.argsort(-score, kind="stable")
    s, y = score[order], y[order]
    tp, fp = np.cumsum(y), np.cumsum(1 - y)
    last = np.r_[s[1:] != s[:-1], True]            # un punto por valor distinto (empates juntos)
    tp, fp = tp[last], fp[last]
    P, Nn = y.sum(), (1 - y).sum()
    tpr, fpr = np.r_[0, tp / P], np.r_[0, fp / Nn]
    prec, rec = tp / (tp + fp), tp / P
    auc = float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2))
    ap = float(np.sum(np.diff(np.r_[0, rec]) * prec))
    return fpr, tpr, prec, rec, auc, ap


def main():
    for _, a, b, _ in POS + NEG:
        assert not any(f in (a + b).lower() for f in FORBIDDEN), (a, b)
    M = kb.Models(STRATUM, N, LAM)
    rows = []
    for label, pairs in ((1, POS), (0, NEG)):
        for pid, wa, wb, note in pairs:
            ca, cb = M.T.composer[wa], M.T.composer[wb]
            assert "cherubini" not in ca and "cherubini" not in cb
            A = windows_with_movement(wa)
            B = windows_with_movement(wb)
            hb = {}
            for _, s in B:
                h = int(kb.order_hashes(s, M_ORD)[0]); hb[h] = hb.get(h, 0) + 1
            tb = len(B)
            seen = {}
            for mv, s in A:
                h = int(kb.order_hashes(s, M_ORD)[0])
                if h in hb:
                    r = seen.setdefault(h, {"sym": s, "occ_A": 0, "mv_A": set()})
                    r["occ_A"] += 1; r["mv_A"].add(int(mv) + 1)
            for h, r in seen.items():
                s = r["sym"]
                ph = M.p_hier(s, ca, cb, M.widx[wb])
                ivs = (s // 8 - 200).tolist(); rcs = (s % 8 - 2).tolist()
                rows.append(dict(pair=pid, label=label, work_A=wa, work_B=wb, hash=h, occ_A=r["occ_A"], occ_B=hb[h],
                                 mov_A="|".join(map(str, sorted(r["mv_A"]))), windows_B=tb,
                                 DF=M.df(s, ca, cb), E=tb * ph, E_laplace=tb * M.p_laplace(s, ca, cb),
                                 intervals=" ".join(map(str, ivs)), rclass=" ".join(map(str, rcs)),
                                 uniform_rhythm=int(len(set(rcs)) == 1 and rcs[0] == 0)))
            print(f"{pid}: {wa} → {wb}: {len(seen)} tipos compartidos", flush=True)
    with open(RES / "thresholds_n8_windows.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    y = np.array([r["label"] for r in rows]); DF = np.array([r["DF"] for r in rows]); E = np.array([r["E"] for r in rows])
    neg, pos = y == 0, y == 1
    # t_DF: mayor valor observado con FPR ≤ 5 % en negativos
    cands = np.unique(DF)
    ok = [t for t in cands if (DF[neg] <= t).mean() <= 0.05]
    t_df = float(max(ok)) if ok else 0.0
    t_e = float(np.quantile(E[neg], 0.05))
    gate = DF <= t_df
    comb = np.where(gate, -np.log(E), -1e9)
    out = {"n": N, "lambda": LAM, "stratum": STRATUM,
           "positives": [dict(id=p, A=a, B=b, ref=c) for p, a, b, c in POS],
           "negatives": [dict(id=p, A=a, B=b, criterio=c) for p, a, b, c in NEG],
           "excluded": "ningún par incluye Beethoven op. 67 ni Cherubini (X01 de controls_positive_candidates.csv)",
           "n_instances": {"pos": int(pos.sum()), "neg": int(neg.sum())},
           "DF": {"threshold": t_df, "rule": "mayor DF con FPR ≤ 5 % en negativos; presencia significativa si DF ≤ umbral",
                  "FPR": float((DF[neg] <= t_df).mean()), "sensitivity": float((DF[pos] <= t_df).mean())},
           "E": {"threshold": t_e, "rule": "percentil 5 de E en el nulo estratificado (pares negativos) = percentil 95 de −log E",
                 "FPR": float((E[neg] <= t_e).mean()), "sensitivity": float((E[pos] <= t_e).mean())},
           "combined": {"rule": "DF ≤ t_DF (presencia) y después ranking por E; decisión conjunta DF ≤ t_DF y E ≤ t_E",
                        "FPR": float((gate & (E <= t_e))[neg].mean()), "sensitivity": float((gate & (E <= t_e))[pos].mean())},
           "per_pair": {}}
    for pid in [p[0] for p in POS + NEG]:
        sel = np.array([r["pair"] == pid for r in rows])
        out["per_pair"][pid] = {"shared_types": int(sel.sum()), "pass_DF": int((DF[sel] <= t_df).sum()),
                                "pass_E": int((E[sel] <= t_e).sum()), "pass_both": int((gate & (E <= t_e))[sel].sum()),
                                "min_DF": float(DF[sel].min()), "min_E": float(E[sel].min())}
    curves = {}
    for name, sc in (("DF", -DF), ("E", -np.log(E)), ("DF→E", comb)):
        fpr, tpr, prec, rec, auc, ap = roc(sc, y)
        curves[name] = (fpr, tpr, prec, rec)
        out.setdefault("curves", {})[name] = {"AUC": auc, "AP": ap}
    out["prevalence"] = float(pos.mean())
    (RES / "thresholds_n8.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n_instances", "DF", "E", "combined", "curves", "per_pair")}, indent=1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    for (name, (fpr, tpr, prec, rec)), col in zip(curves.items(), ("#4c72b0", "#c44e52", "#55a868")):
        c = out["curves"][name]
        ax[0].plot(fpr, tpr, color=col, label=f"{name} (AUC {c['AUC']:.2f})")
        ax[1].plot(rec, prec, color=col, label=f"{name} (AP {c['AP']:.2f})")
    ax[0].plot([0, 1], [0, 1], "k--", lw=1); ax[0].axvline(0.05, color="gray", ls=":", lw=1, label="FPR = 5 %")
    ax[0].set_xlabel("FPR (negativos)"); ax[0].set_ylabel("sensibilidad (positivos)"); ax[0].set_title("ROC")
    ax[1].axhline(out["prevalence"], color="k", ls="--", lw=1, label="prevalencia")
    ax[1].set_xlabel("recall"); ax[1].set_ylabel("precisión"); ax[1].set_title("Precision-recall")
    for a in ax:
        a.grid(alpha=0.3); a.legend(fontsize=8)
    fig.suptitle(f"n = 8, tipos compartidos: {int(pos.sum())} en 4 pares documentados vs {int(neg.sum())} en 4 pares emparejados")
    fig.tight_layout(); FIG.mkdir(exist_ok=True); fig.savefig(FIG / "roc_pr_n8.png", dpi=150)


if __name__ == "__main__":
    main()
