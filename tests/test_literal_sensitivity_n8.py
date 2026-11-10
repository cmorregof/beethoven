"""Tests sintéticos de scripts/literal_sensitivity_n8.py (sin caché, sin parquet)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import confirmatory_n8 as cf  # noqa: E402
import literal_sensitivity_n8 as ls  # noqa: E402
import preregistration_guard as guard  # noqa: E402


def seq(midis, mv=0, v=0, qls=None):
    midis = np.asarray(midis, dtype=float)
    qls = np.ones(len(midis)) if qls is None else np.asarray(qls, dtype=float)
    off = np.r_[0, np.cumsum(qls[:-1])]
    return (mv, v, np.stack([midis, qls, off, 4.0 - off % 4.0], axis=1))


def walk(rng, n):
    return 60 + np.cumsum(rng.integers(-5, 6, size=n))


def test_shared_instances_counts_occurrences_and_movements():
    rng = np.random.default_rng(0)
    b = walk(rng, 100)
    B = cf.windows_from_sequences([seq(b)], "B", "x")
    A = cf.windows_from_sequences([seq(b[:20], mv=0), seq(b[:20], mv=1), seq(walk(rng, 30), mv=2)], "A", "x")
    inst = ls.shared_instances(A, B)
    hb = set(B.hashes.tolist())
    assert {r["hash"] for r in inst} == set(A.hashes.tolist()) & hb
    for r in inst:
        if r["hash"] in set(cf.windows_from_sequences([seq(b[:20])], "t", "x").hashes.tolist()):
            assert r["occ_A"] >= 2 and {1, 2} <= r["mv_A"]
        assert r["occ_B"] == int((B.hashes == np.uint64(r["hash"])).sum())


def test_wilson_known_values():
    lo, hi = ls.wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-4)
    lo, hi = ls.wilson(5, 10)
    assert (lo, hi) == (pytest.approx(0.2366, abs=1e-4), pytest.approx(0.7634, abs=1e-4))
    lo, hi = ls.wilson(10, 10)
    assert hi == pytest.approx(1.0) and lo == pytest.approx(0.7225, abs=1e-4)
    assert all(np.isnan(ls.wilson(0, 0)))


def test_summarize_sensitivity():
    rows = [dict(pair="P", DF=1e-5, E=1e-5, uniform_rhythm=0),
            dict(pair="P", DF=1e-5, E=1.0, uniform_rhythm=1),
            dict(pair="Q", DF=0.5, E=1e-5, uniform_rhythm=0),
            dict(pair="Q", DF=0.5, E=1.0, uniform_rhythm=0)]
    s = ls.summarize(rows, t_df=1e-4, t_e=1e-3)
    g = s["global"]
    assert g["instances"] == 4
    assert (g["DF"]["k"], g["E"]["k"], g["combined"]["k"]) == (2, 2, 1)
    assert g["DF"]["rate"] == 0.5 and g["DF"]["wilson95"] == list(ls.wilson(2, 4))
    assert g["pass_DF_nonuniform"] == 1 and g["pass_both_nonuniform"] == 1
    assert s["per_pair"]["Q"]["DF"]["k"] == 0 and s["per_pair"]["P"]["combined"]["k"] == 1


def test_ls2_intersections_and_power():
    rng = np.random.default_rng(1)
    b = walk(rng, 500)
    B = cf.windows_from_sequences([seq(b)], "B", "x")
    dfs, S = cf.pass_set(B, lambda s: 0.0 if (s[0] % 8 - 2) == 0 else 1.0, 0.5)
    A = cf.windows_from_sequences([seq(b[:200])], "A", "x")            # A ⊂ B: cita literal
    pool = [cf.windows_from_sequences([seq(walk(rng, 300))], f"P{i}", f"y{i}") for i in range(4)]
    L = 30
    obs = cf.sample_fragments(A, L, 50, np.random.default_rng(2))
    nul, _ = cf.sample_null_fragments(pool, L, 200, np.random.default_rng(3))
    oc = [cf.count_statistic(f, S) for f in obs]
    for f, c in zip(obs, oc):                                           # intersección por fuerza bruta
        assert c == len(set(f.tolist()) & set(S.tolist()))
    nc = [cf.count_statistic(f, S) for f in nul]
    r = ls.ls2_power(oc, nc, alpha=0.025)
    assert r["power"]["n"] == 50 and r["power"]["rate"] > 0.9
    assert r["obs_mean"] > r["null_mean"]
    # sin señal: un fragmento nulo frente a su propia distribución no tiene potencia
    r0 = ls.ls2_power(nc[:50], nc, alpha=0.025)
    assert r0["power"]["rate"] < 0.2


def test_pool_selection_filters():
    rows = [
        dict(work_id="musedata_corelli-chry-concerto-op6n01", period="<1750", is_primary="1", in_analysis="1",
             composer_id="corelli_a", is_target="0"),
        dict(work_id="musedata_corelli-chry-concerto-op6n02", period="<1750", is_primary="0", in_analysis="1",
             composer_id="corelli_a", is_target="0"),
        dict(work_id="musedata_handel-haa-op6n1", period="1750–1800", is_primary="1", in_analysis="1",
             composer_id="handel_gf", is_target="0"),
        dict(work_id="musedata_vivaldi-lecene-op3-rv522", period="<1750", is_primary="1", in_analysis="1",
             composer_id="vivaldi_a", is_target="0"),
        dict(work_id="dcml-corelli-op-1-no-1", period="<1750", is_primary="1", in_analysis="1",
             composer_id="cherubini_l", is_target="0"),
        dict(work_id="dcml-corelli-op-3-no-1", period="<1750", is_primary="1", in_analysis="1",
             composer_id="corelli_a", is_target="1"),
    ]
    assert ls.select_string_pool(rows) == ["musedata_corelli-chry-concerto-op6n01"]


def test_guard_aborts_on_forbidden_or_unlisted_works():
    ab = [w for _, a, b in ls.PAIRS for w in (a, b)]
    ok_rows = [dict(work_id=w, composer_id="vivaldi_a", is_target="0") for w in ab]
    ls.check_touched(ab, ["musedata_corelli-chry-concerto-op6n01"], ok_rows)
    with pytest.raises(guard.PreregistrationViolation):
        ls.check_touched(ab + ["musedata_beethoven-bhl-orch-sym5"], [], ok_rows)
    with pytest.raises(guard.PreregistrationViolation):
        ls.check_touched(ab, ["osq-11164006"], ok_rows)
    with pytest.raises(guard.PreregistrationViolation):
        ls.check_touched(ab, [], ok_rows + [dict(work_id="x", composer="Luigi Cherubini", is_target="0")])
    with pytest.raises(guard.PreregistrationViolation):
        ls.check_touched(ab, [], ok_rows + [dict(work_id="y", composer_id="z", is_target="1")])
    with pytest.raises(guard.PreregistrationViolation):                 # A/B fuera de la lista
        ls.check_touched(ab + ["dcml_abc-n05op18-5"], [], ok_rows)
    with pytest.raises(guard.PreregistrationViolation):                 # A/B dentro de la piscina
        ls.check_touched(ab, [ab[0]], ok_rows)
    assert ls.ALLOWED_AB == frozenset(ab) and len(ab) == 8
