"""Tests unitarios de las dos correcciones de D-40 (a) y (b) sobre las tablas reales del estrato
1750-1830 (results/background_kn/*.parquet; se omiten si no están construidas).

  (a) p_KN del grama de nota repetida (intervalo 0, rclass 0) coincide con el estimador de máxima
      verosimilitud c_m(q)/N_m a 3 cifras significativas (escala N_1/N_m de D-40a).
  (b) DF de un grama visto es d(q)/N_obras (obras del estrato sin A ni B que lo contienen) y DF de
      un grama nunca visto está acotada por 1/(N_obras + 1).

Ejecutar: .venv/bin/python -m pytest tests/
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kn_background as kb  # noqa: E402

STRATUM, N = "1750-1830", 8
M_ORD = N - 1
REPEATED = np.full(M_ORD, (0 + 200) * 8 + (0 + 2), dtype=np.int64)   # intervalo 0, rclass 0


def sig3(x: float) -> float:
    return float(f"{x:.3g}")


@pytest.fixture(scope="module")
def models():
    if not (kb.OUT / f"{STRATUM}_o{M_ORD}.parquet").exists():
        pytest.skip("tablas KN no construidas (kn_background.py build)")
    return kb.Models(STRATUM, N, lam=0.45)


def test_kn_repeated_note_matches_ml(models):
    T = models.T
    kn = kb.KN(kb.Counts(T.tok))                      # estrato completo, sin exclusión
    q = int(kb.order_hashes(REPEATED, M_ORD)[0])
    c = T.tok[M_ORD].count(q)
    assert c > 0, "el grama de nota repetida debe estar en el estrato"
    ml = c / T.tok[M_ORD].N
    p = kn.prob(REPEATED)
    assert sig3(p) == sig3(ml), f"p_KN={p:.6g} frente a ML={ml:.6g}"
    assert abs(p - ml) / ml < 1e-3


def test_df_seen_is_doc_fraction_and_unseen_bounded(models):
    T = models.T
    cA, cB = "mozart_wa", "beethoven_l"
    excl = models.excl_of(cA, cB)
    nw = models.n_works - len(excl)
    # grama visto: el de nota repetida; d(q) contado directamente en las filas (grama, obra)
    q = np.uint64(kb.order_hashes(REPEATED, M_ORD)[0])
    r = T.rows[M_ORD]
    sel = r["g"] == q
    works_with_q = set(r["w"][sel].tolist()) - excl
    assert len(works_with_q) > 0
    df = models.df(REPEATED, cA, cB)
    assert df == pytest.approx(len(works_with_q) / nw, rel=1e-12)
    # grama nunca visto: saltos de ±90 semitonos alternados con rclass extremas
    weird = np.array([((90 if k % 2 else -90) + 200) * 8 + ((2 if k % 2 else -2) + 2) for k in range(M_ORD)], dtype=np.int64)
    qw = np.uint64(kb.order_hashes(weird, M_ORD)[0])
    assert not (r["g"] == qw).any()
    df_u = models.df(weird, cA, cB)
    assert 0.0 <= df_u <= 1.0 / (nw + 1)
