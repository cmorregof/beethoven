"""Tests sintéticos de scripts/confirmatory_n8.py (sin caché, sin parquet, sin obras reales)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import confirmatory_n8 as cf  # noqa: E402
import preregistration_guard as guard  # noqa: E402

M = cf.M_ORD


def seq(midis, qls=None, mv=0, v=0, start=0.0, bar=4.0):
    midis = np.asarray(midis, dtype=float)
    qls = np.ones(len(midis)) if qls is None else np.asarray(qls, dtype=float)
    off = start + np.r_[0, np.cumsum(qls[:-1])]
    br = bar - (off % bar)
    return (mv, v, np.stack([midis, qls, off, br], axis=1))


def ww(seqs, wid="synthA", comp="c_a"):
    return cf.windows_from_sequences(seqs, wid, comp)


def walk(rng, n):
    return 60 + np.cumsum(rng.integers(-5, 6, size=n))


# ---------------------------------------------------------------- ventanas y estadístico
def test_windows_count_order_and_symbols():
    w = ww([seq(range(60, 72)), seq(range(50, 60), v=1)])
    assert len(w) == (12 - 8 + 1) + (10 - 8 + 1)
    assert np.all(np.diff(w.onset[w.mov == 0]) >= 0)
    # ascenso cromático con ritmo uniforme: un solo tipo, símbolo (1 + 200)·8 + 2
    assert np.all(w.syms[0] == 201 * 8 + 2)
    assert cf.uniform_rhythm(w.syms[0])
    assert w.n_bars == 3          # 12 negras en 4/4 en la voz 0 cubren 3 compases


def test_rclass_matches_pipeline_definition():
    s = cf.symbols_from_arr(np.array([[60, 1, 0], [62, 0.25, 1], [64, 1, 1.25], [64, 3, 2.25]], float))
    rc = (s % 8 - 2).tolist()
    assert rc == [-2, 2, 2]
    assert (s // 8 - 200).tolist() == [2, 2, 0]


def test_statistic_counts_distinct_types_in_pass_set():
    rng = np.random.default_rng(1)
    b = walk(rng, 200)
    B = ww([seq(b)], "synthB", "c_b")
    A = ww([seq(np.r_[b[10:40], b[10:40]])], "synthA", "c_a")    # tipos de B repetidos dos veces en A
    types_A = np.unique(A.hashes)
    S_all = np.unique(B.hashes)
    shared = np.intersect1d(types_A, S_all)
    assert cf.count_statistic(A.hashes, S_all) == len(shared) > 0
    # DF inyectada: solo pasan los tipos cuyo primer intervalo es positivo
    df_fn = lambda s: 0.0 if (s[0] // 8 - 200) > 0 else 1.0
    dfs, S = cf.pass_set(B, df_fn, t_df=0.5)
    expect = {h for h, d in dfs.items() if d <= 0.5}
    assert set(S.tolist()) == expect
    assert cf.count_statistic(A.hashes, S) == len(set(types_A.tolist()) & expect)
    assert cf.count_statistic(np.empty(0, np.uint64), S) == 0


# ---------------------------------------------------------------- longitud
def test_fragments_are_contiguous_within_movement_and_length_matched():
    rng = np.random.default_rng(2)
    w = ww([seq(walk(rng, 50), mv=0), seq(walk(rng, 30), mv=1), seq(walk(rng, 9), mv=2)])
    L = 20
    st = cf.fragment_starts(w, L)
    assert len(st) > 0
    for s in st:
        assert w.mov[s] == w.mov[s + L - 1]
    assert all(w.mov[s] in (0, 1) for s in st)            # el movimiento 2 (2 ventanas) no admite L = 20
    frs = cf.sample_fragments(w, L, 50, np.random.default_rng(0))
    assert len(frs) == 50 and all(len(f) == L for f in frs)
    pool = [ww([seq(walk(rng, 100))], f"p{i}", f"c{i}") for i in range(3)] + [ww([seq(walk(rng, 10))], "short", "cs")]
    nf, src = cf.sample_null_fragments(pool, L, 300, np.random.default_rng(0))
    assert len(nf) == 300 and all(len(f) == L for f in nf)
    assert "short" not in src                               # obras demasiado cortas no aportan
    assert cf.fragment_starts(w, 10_000).size == 0


def test_length_in_windows_units():
    w = ww([seq(range(60, 100))])                           # 40 notas, 33 ventanas, 10 compases
    assert w.n_bars == 10
    assert cf.length_in_windows(w, 15, "windows") == 15
    assert cf.length_in_windows(w, 4, "bars") == round(4 * 33 / 10)
    with pytest.raises(ValueError):
        cf.length_in_windows(w, 4, "furlongs")


# ---------------------------------------------------------------- p-valor, Bonferroni, regla
def test_p_value_definition():
    null = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert cf.p_value(5, null) == 0.5
    assert cf.p_value(10, null) == 0.0                      # D-41: sin corrección +1
    assert cf.p_value(0, null) == 1.0
    with pytest.raises(ValueError):
        cf.p_value(1, [])


def test_bonferroni():
    assert cf.bonferroni([0.01, 0.2, 0.6]) == [0.03, pytest.approx(0.6), 1.0]
    assert cf.bonferroni([0.01], m=4) == [0.04]


def test_confirmation_rule():
    c = lambda w, p, nu: {"work_A": w, "p_corrected": p, "n_pass_nonuniform": nu}
    d = cf.confirmation_rule([c("a", 0.04, 1), c("b", 0.5, 3)])
    assert d["confirmed"] and d["confirming_works"] == ["a"]
    d = cf.confirmation_rule([c("a", 0.04, 0), c("b", 0.5, 3)])     # significativa pero solo ritmo uniforme
    assert not d["confirmed"] and d["significant_works"] == ["a"] and not d["refuted_strong_sense"]
    d = cf.confirmation_rule([c("a", 0.051, 2)])
    assert not d["confirmed"] and d["refuted_strong_sense"]
    assert cf.confirmation_rule([c("a", 0.05, 1)])["confirmed"]   # ≤ 0,05 incluye el borde


# ---------------------------------------------------------------- bloqueo
TARGET_IDS = [cf.TARGET_B, "osq-11164006", "cherubini_l"]
GOOD_ENV = {cf.UNLOCK_ENV: cf.UNLOCK_VALUE}


@pytest.mark.parametrize("tid", TARGET_IDS)
def test_aborts_without_unlock(tid):
    with pytest.raises(guard.PreregistrationViolation):
        cf.authorize([tid], run_confirmatory=False, d43_commit=None, env={})
    with pytest.raises(guard.PreregistrationViolation):        # solo la bandera
        cf.authorize([tid], run_confirmatory=True, d43_commit=None, env={})
    with pytest.raises(guard.PreregistrationViolation):        # bandera y hash, sin variable de entorno
        cf.authorize([tid], run_confirmatory=True, d43_commit="abcdef1", env={})
    with pytest.raises(guard.PreregistrationViolation):        # valor de entorno incorrecto
        cf.authorize([tid], run_confirmatory=True, d43_commit="abcdef1", env={cf.UNLOCK_ENV: "yes"})


@pytest.mark.parametrize("bad_hash", [None, "", "HEAD", "main", "xyz1234", "abc"])
def test_unlock_without_valid_hash_does_not_run(bad_hash):
    with pytest.raises(SystemExit) as e:
        cf.authorize([cf.TARGET_B], run_confirmatory=True, d43_commit=bad_hash, env=GOOD_ENV)
    assert e.value.code == 3


def test_unlock_with_nonexistent_commit_does_not_run():
    with pytest.raises(SystemExit):
        cf.authorize([cf.TARGET_B], True, "abcdef1234567", GOOD_ENV, verify_commit=lambda h: False)


def test_full_unlock_returns_true_and_non_targets_are_open():
    assert cf.authorize([cf.TARGET_B], True, "abcdef1234567", GOOD_ENV, verify_commit=lambda h: True) is True
    assert cf.authorize(["dcml_abc-n05op18-5", "kern-chopin-mazurkas-op67"], False, None, {}) is False


def test_main_aborts_before_loading_anything(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no debe cargar datos")
    monkeypatch.setattr(cf, "load_pipeline", boom)
    pool = tmp_path / "pool.csv"
    pool.write_text("work_id,composer_id,fragments\nx,mozart_wa,A1\n")
    base = ["--A", "A1=osq-11164006", "--null-pool", str(pool), "--out-dir", str(tmp_path / "o")]
    with pytest.raises(guard.PreregistrationViolation):                 # sin desbloqueo
        cf.main(base, env={})
    with pytest.raises(SystemExit) as e:                                # desbloqueo sin hash
        cf.main(base + ["--run-confirmatory"], env=GOOD_ENV)
    assert e.value.code == 3
    with pytest.raises(guard.PreregistrationViolation):                 # B = op. 67 por defecto
        cf.main(["--A", "A1=kern-humdrum-haydn-symphonies-sym099", "--null-pool", str(pool),
                 "--out-dir", str(tmp_path / "o")], env={})
    assert not (tmp_path / "o").exists()


# ---------------------------------------------------------------- D-43 (b): notas, compases, colapso
def notes(wid, comp, voices, mov=0, bar=4.0, ql=None):
    """voices: lista de listas de alturas (negras por defecto), todas desde el tiempo 0."""
    cols = {k: [] for k in ("midi", "ql", "offset", "voice", "mov", "gap", "br")}
    for v, mids in enumerate(voices):
        q = np.ones(len(mids)) if ql is None else np.asarray(ql, float)
        off = np.r_[0, np.cumsum(q[:-1])]
        cols["midi"] += list(mids); cols["ql"] += list(q); cols["offset"] += list(off)
        cols["voice"] += [v] * len(mids); cols["mov"] += [mov] * len(mids); cols["gap"] += [0.0] * len(mids)
        cols["br"] += list(bar - off % bar)
    return cf.Notes(wid, comp, *(np.asarray(cols[k], float if k in ("midi", "ql", "offset", "gap", "br") else int)
                                 for k in ("midi", "ql", "offset", "voice", "mov", "gap", "br")))


def test_collapse_of_doubled_voices_on_fragment():
    rng = np.random.default_rng(10)
    m = walk(rng, 40)
    one = cf.fragment_hashes(notes("x", "c", [m]))
    doubled = notes("x", "c", [m, m + 12])                            # doblada a la octava
    assert len(cf.fragment_hashes(doubled)) == len(one) == 33
    assert len(cf.fragment_hashes(doubled, collapse=False)) == 66
    other = notes("x", "c", [m, walk(rng, 40)])
    assert len(cf.fragment_hashes(other)) == 66                         # voz distinta: no se colapsa


def test_bar_table_and_span_drop_border_windows():
    nt = notes("x", "c", [range(60, 100)])                              # 40 negras = 10 compases de 4/4
    bars = cf.bar_table(nt)
    assert len(bars) == 10 and bars[0][1:] == (0.0, 4.0)
    sub = cf.span(nt, 0, bars[2][1], bars[5][2])                        # compases 3–6: 16 notas
    assert len(sub) == 16 and len(cf.note_windows(sub)) == 16 - 7       # sin ventanas que crucen el borde


def test_bar_fragments_within_5_percent_and_rejections_counted():
    rng = np.random.default_rng(11)
    pool = [notes(f"P{i}", f"comp{i % 2}", [walk(rng, 200), walk(rng, 200)]) for i in range(4)]
    bars = [cf.bar_table(w) for w in pool]
    target = 50
    for _ in range(30):
        h, src, tries = cf.draw_bar_fragment(pool, bars, target, rng)
        assert 0.95 * target <= len(h) <= 1.05 * target and tries >= 1
    with pytest.raises(RuntimeError):                                   # objetivo imposible
        cf.draw_bar_fragment(pool, bars, 10_000, rng, max_draws=50)
    hq, _, _ = cf.draw_bar_fragment(pool, bars, 40.0, rng, measure="quarters")
    assert len(hq) > 0


def _case_world(seed=12):
    rng = np.random.default_rng(seed)
    b = walk(rng, 600)
    B = cf.windows_from_sequences([(0, 0, np.stack([b, np.ones(len(b)), np.arange(len(b)), 4 - np.arange(len(b)) % 4], 1))],
                                  "B", "beet")
    pool = [notes(f"M{i}", "mozart", [b[i * 100:i * 100 + 120]]) for i in range(4)]   # idioma de Mozart ⊂ B
    A = notes("A", "cher", [walk(rng, 60)])
    return A, B, pool


def test_null_exclusion_is_per_replicate_composer():
    """D-37/D-43: cada réplica A′ se cuenta contra S_B sin el compositor de A′. Con la exclusión fija
    del observado (código anterior) el nulo de este mundo sería 0 y el test, anticonservador."""
    A, B, pool = _case_world()
    seen = []
    def df_fn(sym, c):                    # los tipos de Mozart solo son raros si Mozart sale del fondo
        seen.append(c)
        return 0.0 if c == "mozart" else 1.0
    r = cf.run_case("A1", A, B, pool, df_fn, 0.5, np.random.default_rng(0), n_null=100,
                    df_common_fn=lambda s: 1.0)
    assert {"mozart", "cher"} <= set(seen)
    assert r["null_mean"] > 5 and r["statistic"] == 0 and r["p"] == 1.0
    sec = r["secondary_common_exclusion"]
    assert sec["null_mean"] == 0 and sec["statistic"] == 0
    assert r["replicate_composers"] == {"mozart": 100}
    assert 0.95 * r["L_A_windows"] <= r["target"] <= 1.05 * r["L_A_windows"]


def test_pool_cannot_contain_composer_of_A_or_B():
    A, B, pool = _case_world()
    with pytest.raises(ValueError):
        cf.run_case("A1", A, B, pool + [notes("X", "cher", [range(60, 80)])], lambda s, c: 0.0, 0.5,
                    np.random.default_rng(0), n_null=5)


def test_literal_quote_detected_and_p_forms():
    # cita literal: 60 notas de B tal cual
    rng = np.random.default_rng(13)
    b = walk(rng, 600)
    Bq = cf.windows_from_sequences([(0, 0, np.stack([b, np.ones(600), np.arange(600), 4 - np.arange(600) % 4], 1))], "B", "beet")
    poolq = [notes(f"P{i}", "haydn", [walk(rng, 300)]) for i in range(3)]
    Aq = notes("A", "cher", [b[100:160]])
    r = cf.run_case("A1", Aq, Bq, poolq, lambda s, c: 0.0, 0.5, np.random.default_rng(0), n_null=200)
    assert r["statistic"] == r["L_A_windows"] == 53
    assert r["p"] == 0.0 and r["p_plus1"] == pytest.approx(1 / 201)


def test_p_plus1():
    assert cf.p_plus1(5, [0, 1, 5, 9]) == pytest.approx(3 / 5)
    assert cf.p_plus1(10, [0] * 999) == pytest.approx(1 / 1000)


def test_seed_per_fragment_independent_of_order():
    rng = np.random.default_rng(14)
    b = walk(rng, 500)
    B = cf.windows_from_sequences([(0, 0, np.stack([b, np.ones(500), np.arange(500), 4 - np.arange(500) % 4], 1))], "B", "beet")
    pool = [notes(f"P{i}", "haydn", [walk(rng, 300), walk(rng, 300)]) for i in range(3)]
    A1, A2 = notes("A1w", "cher", [b[:50]]), notes("A2w", "cher", [walk(rng, 70)])
    df = lambda s, c: 0.0 if (s[0] // 8 - 200) % 2 else 1.0
    o1 = cf.run_confirmatory([("A1", 1, A1, pool), ("A2", 2, A2, pool)], B, df, 0.5, n_null=50)
    o2 = cf.run_confirmatory([("A2", 2, A2, pool), ("A1", 1, A1, pool)], B, df, 0.5, n_null=50)
    get = lambda o: {c["label"]: (c["statistic"], c["null_mean"], c["p"], c["rng"]) for c in o["cases"]}
    assert get(o1) == get(o2)
    assert get(o1)["A1"][3] == [cf.SEED, 1] and get(o1)["A2"][3] == [cf.SEED, 2]
    assert o1["bonferroni_m"] == 2
    for c in o1["cases"]:
        assert c["p_corrected"] == min(1.0, 2 * c["p"]) and c["p_plus1_corrected"] == min(1.0, 2 * c["p_plus1"])


# ---------------------------------------------------------------- piscina CSV
POOL_CSV = """work_id,composer_id,year,period,instrumentation,fragments,rule,title
kern-humdrum-haydn-symphonies-sym099,haydn_fj,1793,1750–1800,orchestra,A1;A2,orquesta,"Symphonie Nr. 99"
mozart-k271,mozart_wa,1777,1750–1800,orchestra_soloist,A1,orquesta con solista,"Piano Concerto, K. 271"
mozart-k588,mozart_wa,1790,1750–1800,voices_orchestra,A1,voces y orquesta,Così
"""


def test_read_null_pool_csv_separates_by_fragment(tmp_path):
    p = tmp_path / "pool.csv"
    p.write_text(POOL_CSV, encoding="utf-8")
    pools = cf.read_null_pool(p)
    assert [r["work_id"] for r in pools["A2"]] == ["kern-humdrum-haydn-symphonies-sym099"]
    assert {r["instrumentation"] for r in pools["A1"]} == {"orchestra", "orchestra_soloist", "voices_orchestra"}
    assert len(pools["A1"]) == 3
    cat = {r["work_id"]: {"work_id": r["work_id"], "is_target": "0"} for r in pools["A1"]}
    assert cf.read_null_pool(p, catalog=cat).keys() == pools.keys()


def test_read_null_pool_guard_and_format(tmp_path):
    p = tmp_path / "pool.csv"
    p.write_text(POOL_CSV + "x,cherubini_l,1794,1750–1800,orchestra,A2,r,t\n", encoding="utf-8")
    with pytest.raises(guard.PreregistrationViolation):
        cf.read_null_pool(p)
    p.write_text(POOL_CSV, encoding="utf-8")
    cat = {"kern-humdrum-haydn-symphonies-sym099": {"work_id": "kern-humdrum-haydn-symphonies-sym099", "is_target": "1"},
           "mozart-k271": {"work_id": "mozart-k271"}, "mozart-k588": {"work_id": "mozart-k588"}}
    with pytest.raises(guard.PreregistrationViolation):                 # is_target en el catálogo
        cf.read_null_pool(p, catalog=cat)
    p.write_text("kern-humdrum-haydn-symphonies-sym099\nmozart-k271\n", encoding="utf-8")   # formato antiguo: lista
    with pytest.raises(ValueError):
        cf.read_null_pool(p)
