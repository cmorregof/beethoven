#!/usr/bin/env python
"""Ledger de numeros del paper (S9).

Cada clave tiene una especificacion: archivo versionado de origen + localizador programatico
(ruta JSON, fila/columna de CSV, celda de tabla Markdown con su encabezado, o regex sobre un
texto) y una regla de formato. Ningun valor esta tecleado. Al ejecutarse escribe:

  paper/numbers.yaml        clave, valor bruto, texto, fuente, localizador, nota, comprobaciones
  paper/numbers.tex         \\nm{clave} (error de compilacion si la clave no existe)
  paper/research/ledger_issues.md   desajustes entre documentos y avisos

Uso:
  python paper/make_numbers.py          # genera
  python paper/make_numbers.py --check  # recalcula y compara con lo escrito (no escribe nada)

Reglas: solo lee archivos versionados (results/, docs/, decisions/, paper/PLAN.md). Toda columna
de work_id leida pasa por scripts/preregistration_guard.py. Si un numero no cuadra con otro
documento, la clave se marca MISMATCH, queda fuera de numbers.tex y se anota en
ledger_issues.md: nunca se corrige.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from preregistration_guard import check_ids, is_forbidden_id  # noqa: E402

PAPER = ROOT / "paper"
OUT_YAML = PAPER / "numbers.yaml"
OUT_TEX = PAPER / "numbers.tex"
OUT_ISSUES = PAPER / "research" / "ledger_issues.md"
OUT_ALIASES = PAPER / "research" / "ledger_aliases.csv"
OUT_INDEX = PAPER / "research" / "ledger_index.md"
SCAN_MARK = "## Claves usadas en el texto sin resolver"

SUMMARY = "results/summary.md"
BASE = "results/base_rate.json"
UNIQ = "results/uniqueness.json"
KNJ = "results/kn_calibration.json"
KNC = "results/kn_calibration.csv"
KNP = "results/kn_calibration_pairs.csv"
KNM = "results/kn_calibration.md"
BGM = "results/background_calibration.md"
LAMC = "results/lambda_by_n.csv"
LAMG = "results/lambda_by_n_grid.csv"
THJ = "results/thresholds_n8.json"
THW = "results/thresholds_n8_windows.csv"
EXTS = "results/extract_summary.md"
EXTL = "results/extract_log.csv"
MISS = "results/missing_dates.md"
ENV = "results/env.txt"
D41 = "decisions/D-41_preregistro.md"
DEC = "docs/DECISIONES.md"
PLAN = "paper/PLAN.md"
LITJ = "results/literal_sensitivity_n8.json"

USED: set[str] = set()
_cache: dict = {}


# --------------------------------------------------------------------------- lectura
def text_of(rel: str) -> str:
    USED.add(rel)
    if rel not in _cache:
        _cache[rel] = (ROOT / rel).read_text(encoding="utf-8")
    return _cache[rel]


def json_of(rel: str):
    USED.add(rel)
    k = ("json", rel)
    if k not in _cache:
        _cache[k] = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    return _cache[k]


GUARD_COLS = ("work", "work_A", "work_B", "work_id", "unit_id", "composer", "composer_id", "A", "B")


def csv_of(rel: str) -> pd.DataFrame:
    USED.add(rel)
    k = ("csv", rel)
    if k not in _cache:
        df = pd.read_csv(ROOT / rel)
        for c in GUARD_COLS:
            if c in df.columns:
                check_ids(df[c].astype(str).unique(), context=f"make_numbers:{rel}:{c}")
        _cache[k] = df
    return _cache[k]


class V:
    """Valor con procedencia."""

    def __init__(self, raw, src, loc):
        self.raw, self.src, self.loc = raw, list(src), loc


def J(rel, *path) -> V:
    o = json_of(rel)
    for p in path:
        o = o[p]
    return V(o, [rel], f"{rel} :: " + ".".join(str(p) for p in path))


def derived(fn, vs, desc) -> V:
    srcs = []
    for v in vs:
        for s in v.src:
            if s not in srcs:
                srcs.append(s)
    return V(fn(*[v.raw for v in vs]), srcs, f"{desc} [" + " ; ".join(v.loc for v in vs) + "]")


def csv_val(rel, fn, desc) -> V:
    return V(fn(csv_of(rel)), [rel], f"{rel} :: {desc}")


def csv_cell(rel, where: dict, col) -> V:
    df = csv_of(rel)
    m = df
    for k, val in where.items():
        m = m[np.isclose(m[k], val)] if isinstance(val, float) else m[m[k] == val]
    if len(m) != 1:
        raise KeyError(f"{rel}: {where} -> {len(m)} filas")
    x = m.iloc[0][col]
    x = x.item() if hasattr(x, "item") else x
    return V(x, [rel], f"{rel} :: fila {where} columna {col}")


# --------------------------------------------------------------------------- Markdown
def clean_cell(c: str) -> str:
    return c.strip().replace("**", "").replace("`", "").strip()


def section_lines(rel: str, sec_re: str | None) -> list[str]:
    lines = text_of(rel).split("\n")
    if sec_re is None:
        return lines
    for i, l in enumerate(lines):
        m = re.match(r"^(#{1,6})\s", l)
        if m and re.search(sec_re, l):
            lvl = len(m.group(1))
            j = i + 1
            while j < len(lines):
                m2 = re.match(r"^(#{1,6})\s", lines[j])
                if m2 and len(m2.group(1)) <= lvl:
                    break
                j += 1
            return lines[i:j]
    raise KeyError(f"{rel}: seccion {sec_re!r} no encontrada")


def md_tables(rel, sec_re):
    lines = section_lines(rel, sec_re)
    tables, cur = [], []
    for l in lines:
        if l.startswith("|"):
            cur.append(l)
        else:
            if cur:
                tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    out = []
    for t in tables:
        rows = [[clean_cell(c) for c in r.strip().strip("|").split("|")] for r in t]
        header, body = rows[0], [r for r in rows[2:]]
        out.append((header, body))
    return out


def MC(rel, sec_re, tidx, row: dict, col) -> V:
    """Celda de tabla Markdown. row: {encabezado: texto exacto}; col: encabezado o indice."""
    header, body = md_tables(rel, sec_re)[tidx]
    hits = []
    for r in body:
        if all(r[header.index(h)] == t for h, t in row.items()):
            hits.append(r)
    if len(hits) != 1:
        raise KeyError(f"{rel} [{sec_re}] tabla {tidx}: fila {row} -> {len(hits)} coincidencias")
    ci = col if isinstance(col, int) else header.index(col)
    return V(hits[0][ci], [rel], f"{rel} :: {sec_re} / tabla {tidx} / fila {row} / columna '{header[ci]}'")


def MR(rel, regex, group=1, sec_re=None) -> V:
    lines = section_lines(rel, sec_re)
    m = re.search(regex, "\n".join(lines))
    if not m:
        raise KeyError(f"{rel}: regex {regex!r} sin coincidencia")
    return V(m.group(group), [rel], f"{rel} :: regex {regex!r} grupo {group}" + (f" en {sec_re}" if sec_re else ""))


# --------------------------------------------------------------------------- numeros en texto
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
NUMRE = re.compile(r"([+-]?\d[\d.,]*)\s*(?:[×x]\s*10\s*([⁻+-]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+|[+-]?\d+))?")


def parse_num(s: str, lang="en"):
    """-> (tipo 'f'|'e', decimales, Decimal). lang 'es': coma decimal y punto de miles."""
    s = s.replace("−", "-").replace(" ", "").replace("\xa0", "")
    m = NUMRE.search(s)
    if not m:
        raise ValueError(f"sin numero en {s!r}")
    mant, ex = m.group(1).rstrip(".,"), m.group(2)
    if lang == "es":
        if re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+", mant):
            mant = mant.replace(".", "")
        mant = mant.replace(",", ".")
    else:
        mant = mant.replace(",", "")
    dec = len(mant.split(".")[1]) if "." in mant else 0
    if ex is not None:
        e = int(ex.translate(SUP))
        return "e", dec, Decimal(f"{mant}E{e}")
    return "f", dec, Decimal(mant)


def num(v: V, lang="en", pick=None) -> V:
    """Convierte una celda/regex en numero (int si no tiene decimales)."""
    s = v.raw
    if pick:
        m = re.search(pick, s)
        s = m.group(1)
    kind, dec, d = parse_num(s, lang)
    raw = int(d) if (kind == "f" and dec == 0) else float(d)
    return V(raw, v.src, v.loc + (f" (pick {pick!r})" if pick else ""))


# --------------------------------------------------------------------------- formatos
def _neg(s):
    return s.replace("-", "−")


def fi(v):
    if abs(v - round(v)) > 1e-9:
        raise ValueError(f"entero esperado, valor {v}")
    return _neg(f"{round(v):,}")


def fd(d):
    return lambda v: _neg(format(v, f",.{d}f"))


def fs(d):
    return lambda v: _neg(format(v, f"+,.{d}f"))


def fp(d):  # el valor ya esta en porcentaje
    return lambda v: _neg(format(v, f",.{d}f")) + r"\%"


def fpf(d):  # el valor es una fraccion
    return lambda v: _neg(format(v * 100, f",.{d}f")) + r"\%"


def fe(d):
    def f(v):
        m, e = format(v, f".{d}e").split("e")
        return rf"\ensuremath{{{m}\times10^{{{int(e)}}}}}"
    return f


def ft(v):
    s = str(v)
    if re.search(r"[#%&_{}\\$^~]", s):
        raise ValueError(f"texto con caracteres especiales de LaTeX: {s!r}")
    return s


def tex_text(text: str) -> str:
    return re.sub(r"(?<=\d),(?=\d{3})", "{,}", text)


# --------------------------------------------------------------------------- registro
class Xc:
    def __init__(self, dv: V, lang="en", scale=1.0, pick=None, label=""):
        self.dv, self.lang, self.scale, self.pick, self.label = dv, lang, scale, pick, label


KEYS: dict[str, dict] = {}
CHECKS: list[dict] = []
NOTES: list[str] = []
PER = [("lt1750", "<1750"), ("1750_1800", "1750–1800"), ("1800_1830", "1800–1830"),
       ("1830_1900", "1830–1900"), ("gt1900", ">1900"), ("unknown", "unknown")]
ALLP = [("all", "todo", None)] + [(k, lab, lab) for k, lab in PER]


def run_xc(key, raw, xc: Xc):
    try:
        if isinstance(xc.dv.raw, str):
            s = xc.dv.raw
            if xc.pick:
                m = re.search(xc.pick, s)
                s = m.group(1)
            kind, dec, d = parse_num(s, xc.lang)
            if kind == "f":
                mine = Decimal(format(raw * xc.scale, f".{dec}f"))
            else:
                mine = Decimal(format(raw * xc.scale, f".{dec}e"))
            ok = mine == d
            doc_txt = s
        else:
            ok = math.isclose(raw * xc.scale, xc.dv.raw, rel_tol=1e-9, abs_tol=1e-12)
            doc_txt = repr(xc.dv.raw)
    except Exception as e:  # noqa: BLE001
        ok, doc_txt = False, f"NO PARSEABLE ({e})"
    return {"key": key, "doc": xc.dv.src[0], "loc": xc.dv.loc, "doc_text": doc_txt,
            "ledger_value": raw * xc.scale, "ok": bool(ok), "label": xc.label}


def add(key, v: V, fmt, note="", xc=()):
    assert re.fullmatch(r"[a-z0-9_]+", key), key
    assert key not in KEYS, f"clave duplicada {key}"
    if hasattr(v.raw, "item"):
        v.raw = v.raw.item()
    text = fmt(v.raw)
    results = [run_xc(key, v.raw, x) for x in xc]
    for r in results:
        CHECKS.append(r)
    KEYS[key] = {"raw": v.raw, "text": text, "source": ", ".join(v.src), "locator": v.loc, "note": note,
                 "checks": [f"{'OK' if r['ok'] else 'MISMATCH'}: {r['doc']} -> {r['doc_text']}" for r in results],
                 "status": "ok" if all(r["ok"] for r in results) else "MISMATCH"}


def chk(desc, ok, detail="", warn=False):
    CHECKS.append({"key": None, "doc": "(interno)", "loc": desc, "doc_text": detail, "ledger_value": None,
                   "ok": bool(ok), "label": desc, "warn": warn})


def note(s):
    NOTES.append(s)


# --------------------------------------------------------------------------- especificacion
def build():
    S = SUMMARY
    base = json_of(BASE)
    uniq = json_of(UNIQ)

    def bj(p, *path):  # base_rate.json por periodo ('all' si p es None)
        return J(BASE, "strata", "all", "all", *path) if p is None else J(BASE, "strata", "period", p, *path)

    # ---------------- corpus
    units_cell = lambda col: MC(S, r"^## 1\.", 0, {"colección": "total"}, col)  # noqa: E731
    add("corpus_units_total", num(units_cell("total"), pick=r"^(\d+)"), fi,
        "Unidades primarias en analisis (fichero/movimiento), incluye las 2 obras objetivo (ver ledger_issues.md).")
    add("corpus_works_total", num(units_cell("total"), pick=r"\((\d+)\)"), fi,
        "SOLO para la seccion de datos (explicar que el catalogo incluye las 2 obras objetivo, excluidas de todo analisis). El corpus analizado que cita el paper es corpus_works_catalog (1,871).",
        xc=[Xc(MR(PLAN, r"Corpus: (\d+) obras primarias"), label="PLAN.md §1")])
    for k, lab in PER:
        c = units_cell(lab)
        add(f"corpus_units_{k}", num(c, pick=r"^(\d+)"), fi, "Unidades primarias del periodo (summary.md §1).")
        add(f"corpus_works_primary_{k}", num(c, pick=r"\((\d+)\)"), fi, "Obras primarias del periodo segun summary.md §1 (incluye objetivo). En analisis usar corpus_works_<periodo> (con ventanas).")

    add("corpus_windows_n4", bj(None, "windows"), fi, "Ventanas de 4 notas analizadas (todo el corpus).",
        xc=[Xc(num(MR(S, r"Ventanas de 4 notas analizadas: \*\*([\d,]+)\*\*", 1, r"^## 1\.")), label="summary.md §1 prosa"),
            Xc(J(UNIQ, "curve", "IVR", 1, "tokens"), label="uniqueness.json IVR n=4 tokens")])
    add("corpus_windows_millions", derived(lambda w: w / 1e6, [bj(None, "windows")], "ventanas / 1e6"), fd(2),
        "Ventanas en millones, como las cita PLAN.md.",
        xc=[Xc(MR(PLAN, r"([\d,]+) M ventanas de 4 notas"), "es", label="PLAN.md §1")])
    add("corpus_works_with_windows", bj(None, "works"), fi, "Obras con ventanas de 4 notas (1,859; las que entran en las tasas).",
        xc=[Xc(num(MR(S, r"Ventanas de 4 notas analizadas: \*\*[\d,]+\*\* en ([\d,]+) obras", 1, r"^## 1\.")), label="summary.md §1 prosa"),
            Xc(J(UNIQ, "works"), label="uniqueness.json works")])
    add("corpus_notes", bj(None, "notes"), fi, "Notas totales de las obras analizadas.",
        xc=[Xc(num(MR(S, r"obras \(([\d,]+) notas\)", 1, r"^## 1\.")), label="summary.md §1 prosa")])
    add("corpus_parse_fail_units", num(MR(S, r"Unidades que no parsean: (\d+)", 1, r"^## 1\.")), fi,
        "Unidades que no parsean segun summary.md §1; se recuenta contra results/extract_log.csv (sin leer unidades prohibidas).")
    add("corpus_pilot_works", num(MC(S, r"^## 2\.", 0, {"estrato": "piloto (music21 art)"}, "obras")), fi, "Piloto: obras (summary.md §2).")
    add("corpus_pilot_windows", num(MC(S, r"^## 2\.", 0, {"estrato": "piloto (music21 art)"}, "ventanas")), fi,
        "Piloto: ventanas (summary.md §2).")
    add("corpus_distinct_ngrams_n4", J(BASE, "n_distinct_ngrams"), fi, "Tipos distintos de ventana de 4 notas (3-gramas de intervalos).",
        xc=[Xc(num(MR(S, r"3-gramas distintos: ([\d,]+)", 1, r"^## 6\.")), label="summary.md §6"),
            Xc(J(UNIQ, "curve", "IV", 1, "types"), label="uniqueness.json IV n=4 types")])
    add("corpus_works_catalog", J(BASE, "works_in_catalog"), fi, "Corpus analizado que cita el paper (1,871, sin las 2 obras objetivo; decision de la torre).")
    add("corpus_works_missing_cache", derived(len, [J(BASE, "works_missing_cache")], "len(works_missing_cache)"), fi,
        "Obras del catalogo sin cache de notas.")
    add("corpus_targets_excluded", derived(len, [J(BASE, "targets_excluded")], "len(targets_excluded)"), fi,
        "Numero de obras objetivo excluidas (no se leen ni se nombran).")
    for k, lab in PER:
        add(f"corpus_works_{k}", bj(lab, "works"), fi, "Obras con ventanas del periodo: la cifra que se usa en analisis (decision de la torre).",
            xc=[Xc(MC(S, r"^## 1\.", 1, {"periodo": lab}, "obras"), label="summary.md §1 tabla periodos")] if lab else [],
            )
        add(f"corpus_windows_{k}", bj(lab, "windows"), fi, "Ventanas de 4 notas del periodo.",
            xc=[Xc(MC(S, r"^## 1\.", 1, {"periodo": lab}, "ventanas"), label="summary.md §1 tabla periodos"),
                Xc(MC(S, r"^## 2\.", 0, {"estrato": lab}, "ventanas"), label="summary.md §2")])
        add(f"corpus_windows_pct_{k}", derived(lambda w, t: 100 * w / t, [bj(lab, "windows"), bj(None, "windows")], "100*windows/windows_total"),
            fp(1), "Porcentaje de ventanas del periodo.",
            xc=[Xc(MC(S, r"^## 1\.", 1, {"periodo": lab}, "% ventanas"), label="summary.md §1 tabla periodos")])
    add("corpus_works_1750_1830", derived(lambda a, b: a + b, [bj("1750–1800", "works"), bj("1800–1830", "works")], "suma"), fi,
        "Obras con ventanas, estrato 1750–1830 (union de los dos bins).")
    add("corpus_windows_1750_1830", derived(lambda a, b: a + b, [bj("1750–1800", "windows"), bj("1800–1830", "windows")], "suma"), fi,
        "Ventanas del estrato 1750–1830.",
        xc=[Xc(num(MR(S, r"D4 = \d+ en ([\d,]+) ventanas", 1, r"^## 2\.")), label="summary.md §2 prosa")])
    chk("suma de ventanas por periodo = ventanas totales",
        sum(base["strata"]["period"][lab]["windows"] for _, lab in PER) == base["strata"]["all"]["all"]["windows"])
    chk("suma de obras por periodo = obras con ventanas",
        sum(base["strata"]["period"][lab]["works"] for _, lab in PER) == base["strata"]["all"]["all"]["works"])
    chk("works_by_period (uniqueness.json) = works (base_rate.json)",
        all(uniq["works_by_period"][lab] == base["strata"]["period"][lab]["works"] for _, lab in PER))
    chk("obras con ventanas = obras del catalogo - obras sin cache",
        base["strata"]["all"]["all"]["works"] == base["works_in_catalog"] - len(base["works_missing_cache"]))
    tot_works = int(units_cell("total").raw.split("(")[1].strip(")"))
    if tot_works - len(base["targets_excluded"]) == base["works_in_catalog"]:
        note(f"summary.md §1 y PLAN.md §1 citan {tot_works} obras primarias, pero base_rate.json analiza {base['works_in_catalog']} "
             f"(= {tot_works} - {len(base['targets_excluded'])} obras objetivo excluidas; aritmetica, sin leer el catalogo). "
             f"Clave corpus_works_total = {tot_works}; corpus_works_catalog = {base['works_in_catalog']}. La torre decide cual cita el paper.")
    else:
        chk("1873 - objetivo = works_in_catalog", False, f"{tot_works} - {len(base['targets_excluded'])} != {base['works_in_catalog']}")

    # extract_summary / fechas / entorno
    es = lambda rx, g=1: num(MR(EXTS, rx, g))  # noqa: E731
    add("corpus_extract_units", es(r"Unidades primarias procesadas: ([\d,]+)"), fi, "Unidades procesadas en la extraccion (antes de deduplicar).")
    add("corpus_extract_ok", es(r"Unidades primarias procesadas: [\d,]+ — ok ([\d,]+)"), fi, "Unidades extraidas con exito.")
    add("corpus_extract_fail", es(r"Unidades primarias procesadas: [\d,]+ — ok [\d,]+, fail ([\d,]+)"), fi,
        "Unidades que fallan en la extraccion (extract_summary.md).")
    add("corpus_cache_works", es(r"Caché: `corpus/cache/\*\.npz` \(([\d,]+) obras"), fi, "Obras en la cache de extraccion (incluye duplicados).")
    add("corpus_extract_parts", num(MC(EXTS, r"^# ", 0, {"colección": "total"}, "partes")), fi, "Partes extraidas (total).")
    add("corpus_extract_parts_collapsed", num(MC(EXTS, r"^# ", 0, {"colección": "total"}, "partes tras colapso")), fi, "Partes tras colapsar voces dobladas (D-13).")
    add("corpus_extract_notes", num(MC(EXTS, r"^# ", 0, {"colección": "total"}, "notas")), fi, "Notas extraidas (antes de deduplicar).")
    add("corpus_collapse_units", es(r"Unidades con alguna voz colapsada: ([\d,]+) de"), fi, "Unidades con voces dobladas colapsadas.")
    add("corpus_collapse_pct", es(r"Unidades con alguna voz colapsada: [\d,]+ de [\d,]+ \(([\d.]+) %\)"), fp(1), "Porcentaje de unidades con colapso.")
    add("corpus_dup_nonprimary_units", num(MR(S, r"([\d,]+) unidades no primarias", 1, r"^## 9\.")), fi, "Unidades no primarias (duplicados, D-29).")
    dl = [l for l in text_of("results/seq_duplicates.md").split("\n") if l.startswith("- **")]
    add("corpus_dup_groups", V(len(dl), ["results/seq_duplicates.md"], "results/seq_duplicates.md :: lineas '- **primaria** <- ...' (solo se cuentan, no se inspeccionan ids)"),
        fi, "Grupos de duplicados por hash de secuencia (D-29).")
    add("corpus_dup_hash_works", V(sum(len(re.findall(r"`[^`]+` \(", l.split("←", 1)[1])) for l in dl), ["results/seq_duplicates.md"],
                                   "results/seq_duplicates.md :: numero de duplicados listados tras '<-'"),
        fi, "Obras duplicadas (no primarias) detectadas por hash de secuencia.",
        xc=[Xc(num(MR(S, r"\((\d+) obras por hash", 1, r"^## 9\.")), label="summary.md §9")])
    add("corpus_manual_dates", num(MR(S, r"\((\d+) obras\); detalle", 1, r"^## 8\.")), fi, "Obras con fecha manual ingerida.")
    add("corpus_catalog_units", num(MR(MISS, r"Total unidades: (\d+)")), fi, "Unidades del catalogo.")
    add("corpus_catalog_works", num(MR(MISS, r"obras \(`work_id`\): (\d+)")), fi, "Obras del catalogo.")
    for k, lab in [("manual", "manual"), ("composer_lifespan", "composer_lifespan"), ("dcml_metadata", "dcml_metadata"),
                   ("kern_odt", "kern_ODT"), ("kern_pdt_publication", "kern_PDT_publication"), ("missing", "missing")]:
        add(f"corpus_date_src_{k}", num(MC(MISS, r"^## Origen de la fecha", 0, {"year_source": lab}, "obras")), fi,
            "Obras segun el origen de su fecha (missing_dates.md).")
    add("corpus_period_none", num(MC(MISS, r"^## Periodo asignado", 0, {"period": "unknown", "period_source": "none"}, "obras")), fi,
        "Obras sin periodo asignado (unknown).")
    for k, rx in [("python", r"^python (\S+)"), ("music21", r"^music21 (\S+)"), ("numpy", r"^numpy (\S+)"),
                  ("pandas", r"^pandas (\S+)"), ("pyarrow", r"^pyarrow (\S+)"), ("matplotlib", r"^matplotlib (\S+)")]:
        v = MR(ENV, rx.replace("^", "(?m)^"))
        add(f"corpus_env_{k}", v, ft, "Version de software (results/env.txt).")

    # extract_log: recuento sin leer unidades prohibidas
    USED.add(EXTL)
    n_fail, n_rows, n_skip = 0, 0, 0
    with open(ROOT / EXTL, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if is_forbidden_id(row["work_id"]) or is_forbidden_id(row["unit_id"]):
                n_skip += 1
                continue
            n_rows += 1
            n_fail += row["status"] != "ok"
    ext_fail = KEYS["corpus_extract_fail"]["raw"]
    sum_fail = KEYS["corpus_parse_fail_units"]["raw"]
    note(f"extract_log.csv: {n_rows} filas permitidas ({n_skip} omitidas por la guardia del preregistro, sin leer su contenido), "
         f"{n_fail} con status != ok. extract_summary.md: {ext_fail}; summary.md §1: {sum_fail}.")
    d23 = int(re.search(r"### D-23 Unidades que no parsean \((\d+) de", text_of(DEC)).group(1))
    note(f"Tres cifras distintas de unidades que no parsean: {d23} (docs/DECISIONES.md D-23, de 6.990), {sum_fail} (summary.md §1) y {ext_fail} (extract_summary.md); "
         f"extract_log.csv recuenta {n_fail}. El paper no cita ninguna hasta que el usuario lo resuelva (decision de la torre).")
    for key, claimed in (("corpus_extract_fail", ext_fail), ("corpus_parse_fail_units", sum_fail)):
        r0 = {"key": key, "doc": DEC, "loc": f"{DEC} :: D-23 titulo 'Unidades que no parsean (N de 6.990)'", "doc_text": str(d23),
              "ledger_value": claimed, "ok": claimed == d23, "label": "D-23"}
        CHECKS.append(r0)
        KEYS[key]["checks"].append(f"{'OK' if r0['ok'] else 'MISMATCH'}: {DEC} -> {d23}")
        if not r0["ok"]:
            KEYS[key]["status"] = "MISMATCH"
        r = {"key": key, "doc": EXTL, "loc": f"{EXTL} :: recuento de status != ok (filas prohibidas omitidas)",
             "doc_text": str(n_fail), "ledger_value": claimed, "ok": claimed == n_fail, "label": "recuento extract_log.csv"}
        CHECKS.append(r)
        KEYS[key]["checks"].append(f"{'OK' if r['ok'] else 'MISMATCH'}: {EXTL} -> {n_fail}")
        if not r["ok"]:
            KEYS[key]["status"] = "MISMATCH"

    # ---------------- baserate
    for sfx, lab, pj in ALLP:
        for d in range(1, 6):
            D = f"D{d}"
            add(f"baserate_d{d}_{sfx}", bj(pj, "rate_per_100k", D), fd(0 if d == 3 else 2),
                f"Ocurrencias de {D} por 100k ventanas ({'todo el corpus' if pj is None else lab}).",
                xc=[Xc(MC(S, r"^## 2\.", 0, {"estrato": lab}, D), label="summary.md §2")])
            add(f"baserate_d{d}_count_{sfx}", bj(pj, "counts", D), fi, f"Ocurrencias de {D}.")
            add(f"baserate_d{d}_prev_{sfx}", bj(pj, "prevalence_pct", D), fp(1), f"% de obras con {D}.",
                xc=[Xc(MC(S, r"^## 2\.", 0, {"estrato": lab}, "obras con D4"), label="summary.md §2")] if d == 4 else [])
            add(f"baserate_d{d}_works_{sfx}", bj(pj, "prevalence", D), fi, f"Obras con {D}.")
    # cifras de PLAN.md §1 (31,6 % y 52,9 %)
    for k, g in (("1750_1800", 1), ("1800_1830", 2)):
        r = run_xc(f"baserate_d4_prev_{k}", KEYS[f"baserate_d4_prev_{k}"]["raw"],
                   Xc(V(re.search(r"D4 aparece en el ([\d,]+) % de las obras de 1750–1800 y en el ([\d,]+) %", text_of(PLAN)).group(g),
                        [PLAN], f"{PLAN} :: regex D4 aparece en el .. % grupo {g}"), "es", label="PLAN.md §1"))
        CHECKS.append(r)
        KEYS[f"baserate_d4_prev_{k}"]["checks"].append(f"{'OK' if r['ok'] else 'MISMATCH'}: {PLAN} -> {r['doc_text']}")
        if not r["ok"]:
            KEYS[f"baserate_d4_prev_{k}"]["status"] = "MISMATCH"
    add("baserate_d4_pilot", num(MC(S, r"^## 2\.", 0, {"estrato": "piloto (music21 art)"}, "D4")), fd(2),
        "D4 por 100k en el piloto (todo el corpus art).")
    add("baserate_d4_pilot_prev", num(MC(S, r"^## 2\.", 0, {"estrato": "piloto (music21 art)"}, "obras con D4")), fp(1),
        "% de obras con D4 en el piloto (obra = fichero; no comparable, summary.md §9).")
    cnt = derived(lambda a, b: a + b, [bj("1750–1800", "counts", "D4"), bj("1800–1830", "counts", "D4")], "suma")
    add("baserate_d4_count_1750_1830", cnt, fi, "Ocurrencias de D4 en el estrato 1750–1830.",
        xc=[Xc(num(MR(S, r"D4 = (\d+) en", 1, r"^## 2\.")), label="summary.md §2 prosa")])
    add("baserate_d4_1750_1830", derived(lambda c, w: c / w * 1e5, [cnt, KEYS_V("corpus_windows_1750_1830")], "D4 / ventanas * 1e5"),
        fd(2), "D4 por 100k ventanas en el estrato 1750–1830.",
        xc=[Xc(MR(S, r"→ \*\*([\d.]+)/100k\*\*", 1, r"^## 2\."), label="summary.md §2 prosa")])

    # ---------------- nulo
    for sfx, lab, pj in ALLP:
        for D in ("D2", "D3", "D4"):
            d = D.lower()
            nj = lambda *p, pj=pj, D=D: bj(pj, "null", D, *p)  # noqa: E731
            xs = (lambda col, **kw: [Xc(MC(S, r"^## 5\.", 0, {"estrato": lab}, col), label="summary.md §5", **kw)]) if D == "D4" else (lambda col, **kw: [])
            add(f"null_{d}_obs_{sfx}", nj("obs"), fi, f"{D} observado (obras con >=150 notas).", xc=xs("D4 obs"))
            add(f"null_{d}_mean_{sfx}", nj("mean"), fd(1), f"{D}: media del nulo (barajado intra-voz).", xc=xs("D4 nulo (media)"))
            add(f"null_{d}_cilo_{sfx}", nj("ci95", 0), fi, f"{D}: IC95 del nulo, limite inferior.", xc=xs("IC95", pick=r"^([\d,]+)–"))
            add(f"null_{d}_cihi_{sfx}", nj("ci95", 1), fi, f"{D}: IC95 del nulo, limite superior.", xc=xs("IC95", pick=r"–([\d,]+)$"))
            add(f"null_{d}_ratio_{sfx}", nj("ratio"), fd(2), f"{D}: razon observado/nulo.", xc=xs("ratio"))
            add(f"null_{d}_p_{sfx}", nj("p"), fd(3), f"{D}: p de la permutacion unilateral ((1+k)/(1+n_perm)).", xc=xs("p"))
        add(f"null_perm_works_{sfx}", bj(pj, "perm_works"), fi, "Obras en el test de permutacion.",
            xc=[Xc(MC(S, r"^## 5\.", 0, {"estrato": lab}, "obras perm."), label="summary.md §5")])
    pr = MR(S, r"D2: obs ([\d,]+) vs nulo ([\d.,]+) \(ratio ([\d.]+), p=([\d.]+)\); D3: obs ([\d,]+) vs ([\d.,]+) \(ratio ([\d.]+), p=([\d.]+)\)", 0, r"^## 5\.")
    grp = lambda i: V(re.search(pr_rx, pr.raw).group(i), pr.src, pr.loc + f" grupo {i}")  # noqa: E731
    pr_rx = r"D2: obs ([\d,]+) vs nulo ([\d.,]+) \(ratio ([\d.]+), p=([\d.]+)\); D3: obs ([\d,]+) vs ([\d.,]+) \(ratio ([\d.]+), p=([\d.]+)\)"
    for key, i in (("null_d2_obs_all", 1), ("null_d2_mean_all", 2), ("null_d2_ratio_all", 3), ("null_d2_p_all", 4),
                   ("null_d3_obs_all", 5), ("null_d3_mean_all", 6), ("null_d3_ratio_all", 7), ("null_d3_p_all", 8)):
        r = run_xc(key, KEYS[key]["raw"], Xc(grp(i), label="summary.md §5 prosa"))
        CHECKS.append(r)
        KEYS[key]["checks"].append(f"{'OK' if r['ok'] else 'MISMATCH'}: {S} -> {r['doc_text']}")
        if not r["ok"]:
            KEYS[key]["status"] = "MISMATCH"
    add("null_n_perm", J(BASE, "n_perm"), fi, "Permutaciones (todo y periodos).")
    add("null_n_perm_small", J(BASE, "n_perm_small"), fi, "Permutaciones (colecciones).")
    add("null_min_windows", J(BASE, "min_windows_for_perm"), fi, "Minimo de ventanas por obra para el test de permutacion (resumen: >=150 notas).")
    add("null_seed", J(BASE, "seed"), lambda v: str(v), "Semilla.")
    # D4 por rol de voz y posicion cadencial (§5b)
    CLS = [("bass_cad", "bajo, cadencial"), ("bass_other", "bajo, otra"), ("other_cad", "otras voces, cadencial"),
           ("other_other", "otras voces, otra")]
    for sfx, lab, pj in ALLP:
        for ck, clab in CLS:
            cj = lambda *p, pj=pj, ck=ck: bj(pj, "d4_by_class", ck, *p)  # noqa: E731
            row = {"estrato": lab, "clase": clab}
            mc = lambda col, row=row: [Xc(MC(S, r"^### 5b", 0, row, col), label="summary.md §5b")]  # noqa: E731
            add(f"null_cls_{ck}_windows_{sfx}", cj("windows"), fi, f"Ventanas de la clase '{clab}'.", xc=mc("ventanas"))
            add(f"null_cls_{ck}_obs_{sfx}", cj("obs"), fi, f"D4 observado, clase '{clab}'.", xc=mc("D4 obs"))
            add(f"null_cls_{ck}_rate_{sfx}", cj("rate_per_100k"), fd(2), f"D4 por 100k, clase '{clab}'.", xc=mc("D4/100k"))
            add(f"null_cls_{ck}_mean_{sfx}", cj("null", "mean"), fd(1), f"Nulo (media), clase '{clab}'.", xc=mc("nulo (media)"))
            add(f"null_cls_{ck}_ratio_{sfx}", cj("null", "ratio"), fd(2), f"Razon obs/nulo, clase '{clab}'.", xc=mc("ratio"))
            add(f"null_cls_{ck}_p_{sfx}", cj("null", "p"), fd(3), f"p, clase '{clab}'.", xc=mc("p"))

    # ---------------- uniqueness
    def uc(rep, n, field):
        row = next(r for r in uniq["curve"][rep] if r["n"] == n)
        return V(row[field], [UNIQ], f"{UNIQ} :: curve.{rep}[n={n}].{field}")

    def up(rep, lab, n, field):
        row = next(r for r in uniq["curve_by_period"][rep][lab] if r["n"] == n)
        return V(row[field], [UNIQ], f"{UNIQ} :: curve_by_period.{rep}.{lab}[n={n}].{field}")

    for rep in ("IV", "IVR"):
        for n in range(3, 13):
            row = {"n": str(n)}
            m = lambda col, row=row, rep=rep: [Xc(MC(S, r"^## 7\.", 0, row, f"{rep} {col}"), label="summary.md §7")]  # noqa: E731
            r_ = rep.lower()
            add(f"uniq_{r_}_n{n}_tokens", uc(rep, n, "tokens"), fi, f"Ventanas ({rep}).", xc=m("tokens"))
            add(f"uniq_{r_}_n{n}_types", uc(rep, n, "types"), fi, f"Tipos de ventana distintos ({rep}).", xc=m("tipos"))
            add(f"uniq_{r_}_n{n}_pcross", uc(rep, n, "p_cross"), fd(4), f"P_cross({n}) ({rep}).", xc=m("P_cross"))
            add(f"uniq_{r_}_n{n}_ppair", uc(rep, n, "p_pair"), fd(5), f"P_pair({n}) ({rep}).", xc=m("P_pair"))
        for k, lab in PER:
            for n in (4, 6, 8, 10, 12):
                ci_c = {4: 2, 6: 3, 8: 4, 12: 5}.get(n)
                ci_p = {4: 6, 6: 7, 8: 8, 12: 9}.get(n)
                x1 = [Xc(MC(S, r"^## 7\.", 1, {"periodo": lab}, ci_c), label="summary.md §7 por periodo")] if (rep == "IVR" and ci_c) else []
                x2 = [Xc(MC(S, r"^## 7\.", 1, {"periodo": lab}, ci_p), label="summary.md §7 por periodo")] if (rep == "IVR" and ci_p) else []
                add(f"uniq_{rep.lower()}_n{n}_pcross_{k}", up(rep, lab, n, "p_cross"), fd(3), f"P_cross({n}) ({rep}) dentro de {lab}.", xc=x1)
                add(f"uniq_{rep.lower()}_n{n}_ppair_{k}", up(rep, lab, n, "p_pair"), fd(5), f"P_pair({n}) ({rep}) dentro de {lab}.", xc=x2)

    # ---------------- calibracion (D-40)
    kj = json_of(KNJ)
    kc = csv_of(KNC)
    seen = kc[kc.obs_occ > 0]
    MD = {"lap": "Laplace (cota superior)", "kn": "Kneser-Ney", "hier": "jerárquico"}
    D40 = {"lap": "Laplace", "kn": "Kneser-Ney", "hier": "jerárquico"}
    for m_, mname in MD.items():
        for st, stname, df in (("all", "todas", kc), ("seen", "vistas", seen)):
            jv = lambda i, m_=m_, stname=stname: V(kj["summary"][f"{m_}|{stname}"][i], [KNJ], f"{KNJ} :: summary.{m_}|{stname}[{i}]")  # noqa: E731
            row = {"modelo": mname, "conjunto": stname}
            mc = lambda col, row=row: Xc(MC(KNM, r"^# Calibración", 0, row, col), label="kn_calibration.md")  # noqa: E731
            add(f"calib_{m_}_{st}_n", csv_val(KNC, lambda d, df=df: len(df), f"filas ({stname})"), fi,
                f"Ventanas de calibracion ({stname}).", xc=[mc("n")])
            x_sl = [mc("pendiente")]
            x_mae = [mc("MAE log")]
            x_b = [mc("sesgo log")]
            x_op = [mc("obs/pred total")]
            if st == "all":
                d40 = lambda col, m_=m_: Xc(MC(DEC, r"^### D-40", 0, {"modelo": D40[m_]}, col), "es", label="DECISIONES.md D-40")  # noqa: E731
                x_sl.append(d40("pendiente"))
                x_mae.append(d40("MAE log"))
                x_b.append(d40("sesgo"))
                x_op.append(d40("obs/pred"))
            add(f"calib_{m_}_{st}_slope", jv(0), fd(3), f"Pendiente OLS log(obs) ~ log(pred), {mname}, {stname}.", xc=x_sl)
            add(f"calib_{m_}_{st}_mae", jv(1), fd(3), f"MAE de log(x+0,05), {mname}, {stname}.", xc=x_mae)
            add(f"calib_{m_}_{st}_bias", jv(2), fs(3), f"Sesgo medio de log, {mname}, {stname}.", xc=x_b)
            add(f"calib_{m_}_{st}_obspred",
                csv_val(KNC, lambda d, df=df, m_=m_: df.obs_occ.sum() / df[f"pred_occ_{m_}"].sum(), f"sum(obs_occ)/sum(pred_occ_{m_}) ({stname})"),
                fd(2), f"Cociente total observado/predicho, {mname}, {stname}.", xc=x_op)
    plan_cal = lambda g: V(re.search(r"pendiente ([\d,]+), MAE log ([\d,]+), sesgo (−[\d,]+), obs/pred ([\d,]+)", text_of(PLAN)).group(g),  # noqa: E731
                           [PLAN], f"{PLAN} :: regex 'pendiente .., MAE log .., sesgo .., obs/pred ..' grupo {g}")
    for key, g in (("calib_hier_all_slope", 1), ("calib_hier_all_mae", 2), ("calib_hier_all_bias", 3), ("calib_hier_all_obspred", 4)):
        r = run_xc(key, KEYS[key]["raw"], Xc(plan_cal(g), "es", label="PLAN.md §1"))
        CHECKS.append(r)
        KEYS[key]["checks"].append(f"{'OK' if r['ok'] else 'MISMATCH'}: {PLAN} -> {r['doc_text']}")
        if not r["ok"]:
            KEYS[key]["status"] = "MISMATCH"
    add("calib_lambda", J(KNJ, "lambda"), fd(2), "lambda del fondo jerarquico (D-40).",
        xc=[Xc(num(MR(KNM, r"λ = ([\d.]+)\.")), label="kn_calibration.md")])
    unseen = kc[kc.obs_occ == 0]
    add("calib_unseen_windows", csv_val(KNC, lambda d: len(d[d.obs_occ == 0]), "filas con obs_occ == 0"), fi,
        "Ventanas sin ocurrencias en otro compositor.",
        xc=[Xc(num(MR(KNM, r"Ventanas no vistas en otro compositor: (\d+)")), label="kn_calibration.md")])
    for m_, mname in (("lap", "Laplace"), ("kn", "KN"), ("hier", "jerárquico")):
        add(f"calib_unseen_e_{m_}", csv_val(KNC, lambda d, m_=m_: d[d.obs_occ == 0][f"pred_occ_{m_}"].mean(), f"mean(pred_occ_{m_}) con obs_occ == 0"),
            fd(3), f"E predicho medio de las ventanas no vistas ({mname}).",
            xc=[Xc(V(re.search(r"E predicho medio: Laplace ([\d.]+), KN ([\d.]+), jerárquico ([\d.]+)\.", text_of(KNM)).group({"lap": 1, "kn": 2, "hier": 3}[m_]),
                     [KNM], f"{KNM} :: regex 'E predicho medio: ..' modelo {m_}"), label="kn_calibration.md")])
    add("calib_obs_occ_total", csv_val(KNC, lambda d: d.obs_occ.sum(), "sum(obs_occ)"), fi, "Ocurrencias observadas (200 ventanas).",
        xc=[Xc(num(MR(BGM, r"ocurrencias: predicho total [\d.]+, observado (\d+)")), label="background_calibration.md")])
    add("calib_obs_works_total", csv_val(KNC, lambda d: d.obs_works.sum(), "sum(obs_works)"), fi, "Obras con q observadas (suma sobre 200 ventanas).",
        xc=[Xc(num(MR(KNM, r"total predicho [\d.]+ vs observado (\d+)")), label="kn_calibration.md"),
            Xc(num(MR(BGM, r"obras con q: predicho total [\d.]+, observado (\d+)")), label="background_calibration.md")])
    # DF
    add("calib_df_pairs", csv_val(KNP, lambda d: len(d), "filas"), fi, "Pares ventana x obra B para DF.",
        xc=[Xc(num(MR(KNM, r"pares ([\d,]+);")), label="kn_calibration.md")])
    for key, col, rx, desc in (("calib_df_present_obs", "present", r"presencia observada ([\d.]+)", "Presencia observada en B"),
                               ("calib_df_mean", "df_pred", r"DF media ([\d.]+)", "DF predicha media"),
                               ("calib_df_kn_pres", "p_present_kn", r"KN medio ([\d.]+)", "1-e^(-E) medio, KN"),
                               ("calib_df_hier_pres", "p_present_hier", r"KN medio [\d.]+; jerárquico ([\d.]+)", "1-e^(-E) medio, jerarquico")):
        m = re.search(rx, text_of(KNM))
        add(key, csv_val(KNP, lambda d, col=col: d[col].mean(), f"mean({col})"), fd(4), desc + " (pares D-40).",
            xc=[Xc(V(m.group(1), [KNM], f"{KNM} :: regex {rx!r}"), label="kn_calibration.md")])
    xx = np.log(kc.pred_works_df + .05)
    yy = np.log(kc.obs_works + .05)
    dfm = re.search(r"DF pendiente ([\d.]+), MAE log ([\d.]+), sesgo ([-\d.]+); total predicho ([\d.]+) vs observado (\d+)", text_of(KNM))
    mdv = lambda g: V(dfm.group(g), [KNM], f"{KNM} :: regex 'DF pendiente .., MAE log .., sesgo ..; total predicho .. vs observado ..' grupo {g}")  # noqa: E731
    add("calib_df_slope", csv_val(KNC, lambda d: float(np.polyfit(xx, yy, 1)[0]), "pendiente OLS log(obs_works+.05) ~ log(pred_works_df+.05)"),
        fd(3), "DF a nivel de ventana: pendiente.", xc=[Xc(mdv(1), label="kn_calibration.md")])
    add("calib_df_mae", csv_val(KNC, lambda d: float(np.abs(yy - xx).mean()), "mean|log obs - log pred|"), fd(3),
        "DF a nivel de ventana: MAE log.", xc=[Xc(mdv(2), label="kn_calibration.md")])
    add("calib_df_bias", csv_val(KNC, lambda d: float((yy - xx).mean()), "mean(log obs - log pred)"), fs(3),
        "DF a nivel de ventana: sesgo.", xc=[Xc(mdv(3), label="kn_calibration.md")])
    tp = csv_val(KNC, lambda d: d.pred_works_df.sum(), "sum(pred_works_df)")
    add("calib_df_total_pred", tp, fd(1), "Total de obras B predichas por DF (200 ventanas).", xc=[Xc(mdv(4), label="kn_calibration.md")])
    add("calib_df_total_pred_int", tp, fd(0), "Total predicho por DF redondeado a entero, como lo cita D-40.",
        xc=[Xc(V(re.search(r"total (\d\.\d{3}) obras predichas", text_of(DEC)).group(1), [DEC], f"{DEC} :: regex 'total X obras predichas'"), "es", label="DECISIONES.md D-40")])
    add("calib_df_total_obs", csv_val(KNC, lambda d: d.obs_works.sum(), "sum(obs_works)"), fi, "Total de obras B observadas.",
        xc=[Xc(mdv(5), label="kn_calibration.md"),
            Xc(V(re.search(r"frente a (\d\.\d{3}) observadas", text_of(DEC)).group(1), [DEC], f"{DEC} :: regex 'frente a X observadas'"), "es", label="DECISIONES.md D-40")])
    # Laplace alpha=1 y Good-Turing (background_calibration.md)
    sec1 = r"^## α = 1 \(Laplace\)"
    sec2 = r"^## α = 0\.9609"
    for pre, sec in (("lap1", sec1), ("gt", sec2)):
        add(f"calib_{pre}_alpha", num(MR(BGM, r"pseudocuenta α = ([\d.]+)", 1, sec)), fd(4 if pre == "gt" else 0), "Pseudocuenta α.")
        add(f"calib_{pre}_pred_total", num(MR(BGM, r"ocurrencias: predicho total ([\d.]+),", 1, sec)), fd(1), "Ocurrencias predichas (suma).")
        add(f"calib_{pre}_ratio", num(MR(BGM, r"ratio obs/pred ([\d.]+)", 1, sec)), fd(2), "Cociente obs/pred de ocurrencias.")
        add(f"calib_{pre}_works_pred", num(MR(BGM, r"obras con q: predicho total ([\d.]+),", 1, sec)), fd(1), "Obras con q predichas.")
        add(f"calib_{pre}_works_ratio", num(MR(BGM, r"obras con q: predicho total [\d.]+, observado \d+, ratio ([\d.]+)", 1, sec)), fd(2),
            "Cociente obs/pred de obras con q.")
        add(f"calib_{pre}_corr", num(MR(BGM, r"correlación log\(pred\+0\.05\) vs log\(obs\+0\.05\): ([\d.]+)", 1, sec)), fd(3), "Correlacion log-log.")
    add("calib_n1_frac", num(MR(BGM, r"N1/N \(tipos únicos\) = ([\d.]+)", 1, sec1)), fd(3), "N1/N (tipos unicos).")
    add("calib_unseen_lap_pred", num(MR(BGM, r"predicho ([\d.]+) ocurrencias, observado 0", 1, sec1)), fd(1),
        "Ocurrencias predichas (Laplace) en las 118 ventanas no vistas.")

    # ---------------- lambda(n)
    lam = csv_of(LAMC)
    grid = csv_of(LAMG)
    ns = [int(n) for n in lam["n"]]
    note(f"lambda_by_n.csv contiene n = {ns}; no hay n = 9 ni n = 11 (D-41 tampoco los incluye). No se inventan.")
    for n in ns:
        cell = lambda col, n=n: csv_cell(LAMC, {"n": n}, col)  # noqa: E731
        pr = lambda i, n=n: Xc(MC(D41, r"^## Longitud de ventana", 0, {"n": str(n)}, i), "es", label="D-41_preregistro.md")  # noqa: E731
        add(f"lambda_n{n}_star", cell("lambda_star"), fd(2), "lambda* por interpolacion borrada.", xc=[pr(1)])
        add(f"lambda_n{n}_loglik", cell("loglik_por_ventana"), fd(4), "Log-verosimilitud por ventana en lambda*.", xc=[pr(2)])
        add(f"lambda_n{n}_nwin", cell("n_ventanas_lambda"), fi, "Ventanas de reserva.", xc=[pr(3)])
        add(f"lambda_n{n}_slope", cell("pendiente"), fd(4), "Pendiente en lambda*.", xc=[pr(4)])
        add(f"lambda_n{n}_mae", cell("MAE_log"), fd(4), "MAE log en lambda*.", xc=[pr(5)])
        add(f"lambda_n{n}_bias", cell("sesgo_log"), fd(4), "Sesgo log en lambda*.", xc=[pr(6)])
        add(f"lambda_n{n}_obspred", cell("obs_pred"), fd(4), "obs/pred en lambda*.", xc=[pr(7)])
        add(f"lambda_n{n}_cal", cell("lambda_cal_D40"), fd(2), "lambda de menor sesgo absoluto con pendiente en [0,9; 1,1].", xc=[pr(8)])
        add(f"lambda_n{n}_mae_cal", cell("MAE_log_lambda_cal"), fd(4), "MAE log en ese lambda.", xc=[pr(9)])
        g = grid[grid.n == n]
        am = float(g.loc[g.loglik.idxmax(), "lam"])
        chk(f"lambda*(n={n}) = argmax loglik de lambda_by_n_grid.csv", math.isclose(am, float(lam[lam.n == n].lambda_star.iloc[0])),
            f"argmax grid {am}")
    for lm in (0.0, 0.25, 0.45, 0.75, 1.0):
        add(f"lambda_n8_ll_at_{int(round(lm * 100)):03d}", csv_cell(LAMG, {"n": 8, "lam": lm}, "loglik"), fd(2),
            f"Log-verosimilitud por ventana (n = 8) en lambda = {lm}.")
    add("lambda_grid_step", derived(lambda a, b: round(b - a, 10), [csv_cell(LAMG, {"n": 4, "lam": 0.0}, "lam"), csv_cell(LAMG, {"n": 4, "lam": 0.05}, "lam")],
                                   "paso de la rejilla"), fd(2), "Paso de la rejilla de lambda.")

    # ---------------- umbrales n = 8
    th = json_of(THJ)
    check_ids([p[k] for p in th["positives"] + th["negatives"] for k in ("A", "B")], context="make_numbers:thresholds")
    win = csv_of(THW)
    pos, neg = win[win.label == 1], win[win.label == 0]
    t_df, t_e = th["DF"]["threshold"], th["E"]["threshold"]
    k_df_fp, k_df_tp = int((neg.DF <= t_df).sum()), int((pos.DF <= t_df).sum())
    k_e_fp, k_e_tp = int((neg.E <= t_e).sum()), int((pos.E <= t_e).sum())
    k_c_fp = int(((neg.DF <= t_df) & (neg.E <= t_e)).sum())
    k_c_tp = int(((pos.DF <= t_df) & (pos.E <= t_e)).sum())
    npos, nneg = len(pos), len(neg)
    chk("instancias del CSV = n_instances del JSON", (npos, nneg) == (th["n_instances"]["pos"], th["n_instances"]["neg"]), f"{npos},{nneg}")
    chk("FPR/sensibilidad del JSON = recuento del CSV (DF, E, conjunto)",
        all(math.isclose(a, b, rel_tol=1e-9) for a, b in (
            (th["DF"]["FPR"], k_df_fp / nneg), (th["DF"]["sensitivity"], k_df_tp / npos),
            (th["E"]["FPR"], k_e_fp / nneg), (th["E"]["sensitivity"], k_e_tp / npos),
            (th["combined"]["FPR"], k_c_fp / nneg), (th["combined"]["sensitivity"], k_c_tp / npos))),
        f"DF {k_df_fp}/{nneg},{k_df_tp}/{npos}; E {k_e_fp}/{nneg},{k_e_tp}/{npos}; ambos {k_c_fp}/{nneg},{k_c_tp}/{npos}")
    chk("instancias por par: suma de shared_types = n_instances",
        sum(th["per_pair"][p["id"]]["shared_types"] for p in th["positives"]) == th["n_instances"]["pos"]
        and sum(th["per_pair"][p["id"]]["shared_types"] for p in th["negatives"]) == th["n_instances"]["neg"])
    chk("prevalencia = positivos / instancias", math.isclose(th["prevalence"], npos / (npos + nneg)))
    T = lambda *p: J(THJ, *p)  # noqa: E731
    row_df, row_e = {"cantidad": "DF"}, {"cantidad": "E (jerárquico, λ = 0,45)"}
    row_c = {"cantidad": "DF y E"}
    pre = lambda row, col, **kw: Xc(MC(D41, r"^## Umbrales", 0, row, col), "es", label="D-41_preregistro.md", **kw)  # noqa: E731
    add("thresh_n", T("n"), fi, "Longitud de ventana del confirmatorio.")
    add("thresh_lambda", T("lambda"), fd(2), "lambda del fondo jerarquico.")
    add("thresh_pos_instances", T("n_instances", "pos"), fi, "Instancias positivas (tipos compartidos en pares con modelado documentado).",
        xc=[Xc(num(MR(D41, r"(\d+) instancias positivas", 1), "es"), label="D-41_preregistro.md")])
    add("thresh_neg_instances", T("n_instances", "neg"), fi, "Instancias negativas.",
        xc=[Xc(num(MR(D41, r"instancias positivas y\s+(\d+)\s+negativas", 1), "es"), label="D-41_preregistro.md")])
    add("thresh_pos_pairs", derived(len, [T("positives")], "len(positives)"), fi, "Pares positivos.")
    add("thresh_neg_pairs", derived(len, [T("negatives")], "len(negatives)"), fi, "Pares negativos.")
    add("thresh_prevalence", T("prevalence"), fd(2), "Prevalencia de positivos.",
        xc=[Xc(MR(D41, r"prevalencia \(([\d,]+)\)"), "es", label="D-41_preregistro.md")])
    for tag, key, row, tv in (("df", "DF", row_df, t_df), ("e", "E", row_e, t_e)):
        j = lambda *p, key=key: T(key, *p)  # noqa: E731
        add(f"thresh_{tag}_t", j("threshold"), fe(2), f"Umbral de {key}.", xc=[pre(row, "umbral")])
        add(f"thresh_{tag}_fpr", j("FPR"), fpf(1), f"FPR de {key} en negativos.", xc=[pre(row, "FPR en negativos", scale=100)])
        add(f"thresh_{tag}_sens", j("sensitivity"), fpf(1), f"Sensibilidad de {key} en positivos.",
            xc=[pre(row, "sensibilidad en positivos", scale=100)])
    add("thresh_df_fpr_k", csv_val(THW, lambda d: k_df_fp, "negativos con DF <= umbral"), fi, "Negativos con DF <= t_DF.")
    add("thresh_df_sens_k", csv_val(THW, lambda d: k_df_tp, "positivos con DF <= umbral"), fi, "Positivos con DF <= t_DF (k de k/360).",
        xc=[pre(row_df, "sensibilidad en positivos", pick=r"\((\d+)/")])
    add("thresh_e_fpr_k", csv_val(THW, lambda d: k_e_fp, "negativos con E <= umbral"), fi, "Negativos con E <= t_E.")
    add("thresh_e_sens_k", csv_val(THW, lambda d: k_e_tp, "positivos con E <= umbral"), fi, "Positivos con E <= t_E (k de k/360).",
        xc=[pre(row_e, "sensibilidad en positivos", pick=r"\((\d+)/")])
    add("thresh_comb_fpr", T("combined", "FPR"), fpf(1), "FPR de la decision conjunta DF y E.", xc=[pre(row_c, "FPR en negativos", scale=100)])
    add("thresh_comb_sens", T("combined", "sensitivity"), fpf(1), "Sensibilidad de la decision conjunta.",
        xc=[pre(row_c, "sensibilidad en positivos", scale=100)])
    add("thresh_comb_fpr_k", csv_val(THW, lambda d: k_c_fp, "negativos con DF y E"), fi, "Negativos que pasan DF y E.")
    add("thresh_comb_sens_k", csv_val(THW, lambda d: k_c_tp, "positivos con DF y E"), fi, "Positivos que pasan DF y E.")
    auc = re.search(r"AUC: DF ([\d,]+); E ([\d,]+); DF→E ([\d,]+)\.", text_of(D41))
    for i, (tag, key) in enumerate((("df", "DF"), ("e", "E"), ("dfe", "DF→E")), 1):
        add(f"thresh_auc_{tag}", T("curves", key, "AUC"), fd(2), f"AUC de {key}.",
            xc=[Xc(V(auc.group(i), [D41], f"{D41} :: regex 'AUC: DF ..; E ..; DF→E ..' grupo {i}"), "es", label="D-41_preregistro.md")])
        add(f"thresh_ap_{tag}", T("curves", key, "AP"), fd(2), f"Precision media de {key}.")
    for pid in [p["id"] for p in th["positives"] + th["negatives"]]:
        q = pid.lower()
        add(f"thresh_{q}_shared_types", T("per_pair", pid, "shared_types"), fi, f"Tipos compartidos en {pid}.")
        add(f"thresh_{q}_pass_df", T("per_pair", pid, "pass_DF"), fi, f"Tipos compartidos con DF <= t_DF en {pid}.")
        add(f"thresh_{q}_pass_e", T("per_pair", pid, "pass_E"), fi, f"Tipos compartidos con E <= t_E en {pid}.")
        add(f"thresh_{q}_pass_both", T("per_pair", pid, "pass_both"), fi, f"Tipos que pasan ambos en {pid}.")
        add(f"thresh_{q}_min_df", T("per_pair", pid, "min_DF"), fe(2), f"DF minimo en {pid}.")
        add(f"thresh_{q}_min_e", T("per_pair", pid, "min_E"), fe(2), f"E minimo en {pid}.")
    # fracciones k/n como texto
    add("thresh_df_sens_frac", derived(lambda k, n: f"{k}/{n}", [KEYS_V("thresh_df_sens_k"), KEYS_V("thresh_pos_instances")], "k/n"), ft,
        "Sensibilidad de DF como fraccion k/n.")
    add("thresh_e_sens_frac", derived(lambda k, n: f"{k}/{n}", [KEYS_V("thresh_e_sens_k"), KEYS_V("thresh_pos_instances")], "k/n"), ft,
        "Sensibilidad de E como fraccion k/n.")


def fpn(d):  # fraccion -> porcentaje SIN signo (el texto anade \\,\\%)
    return lambda v: _neg(format(v * 100, f",.{d}f"))


ALIASES: list[tuple[str, str, str]] = []


def alias(req, existing, why=""):
    ALIASES.append((req, existing, why))


def build_requests():
    base = json_of(BASE)
    SFX = {"pre1750": "lt1750", "1750_1800": "1750_1800", "1800_1830": "1800_1830", "1830_1900": "1830_1900",
           "post1900": "gt1900", "undated": "unknown", "all": "all"}
    JP = {"lt1750": "<1750", "1750_1800": "1750–1800", "1800_1830": "1800–1830", "1830_1900": "1830–1900",
          "gt1900": ">1900", "unknown": "unknown", "all": None}

    def bj(sfx, *path):
        p = JP[sfx]
        return J(BASE, "strata", "all", "all", *path) if p is None else J(BASE, "strata", "period", p, *path)

    # ---- alias A2 / torre / redactores
    for a, b in SFX.items():
        alias(f"baserate_d4_rate_{a}", f"baserate_d4_{b}")
        if a != b:
            alias(f"null_d4_ratio_{a}", f"null_d4_ratio_{b}")
    alias("baserate_d4_rate_1750_1830", "baserate_d4_1750_1830")
    alias("baserate_d1_rate_all", "baserate_d1_all")
    alias("baserate_d2_rate_all", "baserate_d2_all")
    alias("baserate_works_1750_1800", "corpus_works_1750_1800")
    alias("baserate_works_1800_1830", "corpus_works_1800_1830")
    for c, cl in (("basscad", "bass_cad"), ("bassother", "bass_other"), ("uppercad", "other_cad"), ("upperother", "other_other")):
        for a, b in SFX.items():
            alias(f"null_ratio_{c}_{a}", f"null_cls_{cl}_ratio_{b}")
    for m in ("lap", "kn", "hier"):
        alias(f"calib_{m}_obspred", f"calib_{m}_all_obspred")
    alias("calib_windows", "calib_lap_all_n")
    alias("calib_seen", "calib_lap_seen_n")
    alias("calib_unseen", "calib_unseen_windows")
    alias("calib_df_pred_total", "calib_df_total_pred_int")
    alias("calib_df_obs_total", "calib_df_total_obs")
    alias("calib_pairs", "calib_df_pairs")
    for k in (4, 5, 6, 7, 8, 10, 12):
        alias(f"lambda_star_n{k}", f"lambda_n{k}_star")
    for r in ("lambda_heldout_windows_n8", "lambda_holdout_windows_n8"):
        alias(r, "lambda_n8_nwin")
    for r in ("thresh_npos", "thresh_n_pos"):
        alias(r, "thresh_pos_instances")
    for r in ("thresh_nneg", "thresh_n_neg"):
        alias(r, "thresh_neg_instances")
    for r in ("thresh_t_df", "thresh_df_threshold"):
        alias(r, "thresh_df_t")
    for r in ("thresh_t_e", "thresh_e_threshold"):
        alias(r, "thresh_e_t")
    alias("thresh_df_tp", "thresh_df_sens_k")
    alias("thresh_e_tp", "thresh_e_sens_k")
    alias("thresh_df_fp", "thresh_df_fpr_k")
    alias("thresh_e_fp", "thresh_e_fpr_k")
    alias("thresh_fp_n08", "thresh_n08_pass_df")
    alias("thresh_fp_n10", "thresh_n10_pass_df")
    alias("thresh_tp_p08", "thresh_p08_pass_df")
    alias("thresh_tp_p10", "thresh_p10_pass_df")
    alias("corpus_works_primary", "corpus_works_total", "solo seccion de datos; el paper cita corpus_works_catalog")
    alias("corpus_n_units_primary", "corpus_units_total")
    alias("corpus_n_works_primary", "corpus_works_total", "solo seccion de datos; el analisis usa corpus_works_catalog")
    alias("corpus_n_works_windows", "corpus_works_with_windows")
    alias("corpus_n_notes", "corpus_notes")
    alias("corpus_n_windows4", "corpus_windows_n4")
    alias("corpus_n_nonprimary_units", "corpus_dup_nonprimary_units")
    alias("corpus_n_seqdup_works", "corpus_dup_hash_works")
    alias("corpus_manual_dates_works", "corpus_manual_dates")
    alias("corpus_datesrc_dcml", "corpus_date_src_dcml_metadata")
    alias("corpus_datesrc_kern_odt", "corpus_date_src_kern_odt")
    alias("corpus_datesrc_kern_pdt", "corpus_date_src_kern_pdt_publication")
    alias("corpus_datesrc_lifespan", "corpus_date_src_composer_lifespan")
    alias("corpus_datesrc_manual", "corpus_date_src_manual")
    alias("corpus_datesrc_missing", "corpus_date_src_missing")
    alias("corpus_stratum_works", "corpus_works_1750_1830")
    # literal: nombres de A2 -> nombres de A3
    for a, b in (("literal_ls1", "literal_ls1_sens_df"), ("literal_ls1_cilo", "literal_ls1_sens_df_lo"),
                 ("literal_ls1_cihi", "literal_ls1_sens_df_hi"), ("literal_shared_types", "literal_ls1_instances"),
                 ("literal_ls1_min", "literal_ls1_sens_df_min"), ("literal_ls1_max", "literal_ls1_sens_df_max"),
                 ("literal_ls2_at_lmin", "literal_ls2_power_b10"), ("literal_ls2_at_lmax", "literal_ls2_power_b20")):
        alias(a, b, "A2->A3; numero sin signo %, el texto anade \\,\\%")

    # ---- tasas base (formato A2: porcentaje sin signo)
    for a, b in SFX.items():
        add(f"baserate_d4_works_pct_{a}", bj(b, "prevalence_pct", "D4"), fd(1), "% de obras con D4, SIN signo % (el texto anade \\,\\%). Igual que baserate_d4_prev_*.")
    wpw = {}
    for a, lab in (("1750_1800", "1750–1800"), ("1800_1830", "1800–1830")):
        wpw[a] = derived(lambda w, n: w / n, [J(BASE, "strata", "period", lab, "windows"), J(BASE, "strata", "period", lab, "works")], "windows/works")
        add(f"baserate_windows_per_work_{a}", wpw[a], fd(0), "Ventanas por obra.")
    add("baserate_windows_per_work_ratio", derived(lambda a, b: b / a, [wpw["1750_1800"], wpw["1800_1830"]], "wpw(1800-1830)/wpw(1750-1800)"), fd(1),
        "Cociente de ventanas por obra 1800–1830 / 1750–1800.")
    CXP = {"osq_1750_1800": "openscore_quartets|1750–1800", "osq_1800_1830": "openscore_quartets|1800–1830",
           "haydnq_1750_1800": "kern/humdrum-haydn-quartets|1750–1800", "abc_1800_1830": "dcml_abc|1800–1830",
           "mozsonatas_1750_1800": "dcml_mozart_sonatas|1750–1800", "bps_1800_1830": "dcml/beethoven_piano_sonatas|1800–1830"}
    for k, ck in CXP.items():
        add(f"baserate_d4_rate_{k}", J(BASE, "strata", "collection_x_period", ck, "rate_per_100k", "D4"), fd(2), f"D4 por 100k, {ck}.")
        if k.startswith("osq"):
            add(f"baserate_d4_works_pct_{k}", J(BASE, "strata", "collection_x_period", ck, "prevalence_pct", "D4"), fd(1), f"% obras con D4, {ck} (sin signo %).")
            add(f"baserate_windows_per_work_{k}", derived(lambda w, n: w / n, [J(BASE, "strata", "collection_x_period", ck, "windows"),
                                                                              J(BASE, "strata", "collection_x_period", ck, "works")], "windows/works"), fd(0),
                f"Ventanas por obra, {ck}.")
    # ---- nulo
    ex = derived(lambda o, m: o - m, [J(BASE, "strata", "all", "all", "null", "D4", "obs"), J(BASE, "strata", "all", "all", "null", "D4", "mean")], "obs - mean")
    add("null_d4_excess_all", ex, fd(0), "Exceso observado - nulo de D4 (todo).")
    cls = lambda c, *p: J(BASE, "strata", "all", "all", "d4_by_class", c, *p)  # noqa: E731
    cx = lambda c: derived(lambda o, m: o - m, [cls(c, "null", "obs"), cls(c, "null", "mean")], f"exceso {c}")  # noqa: E731
    for nm, cs in (("bass", ("bass_cad", "bass_other")), ("uppercad", ("other_cad",)), ("upperother", ("other_other",))):
        add(f"null_excess_pct_{nm}", derived(lambda *a: sum(a[:-1]) / a[-1] * 100, [cx(c) for c in cs] + [ex], "exceso de clase / exceso total * 100"), fd(0),
            "Porcentaje del exceso de D4 (sin signo %).")
    add("null_windows_pct_bass", derived(lambda a, b, c, d: (a + b) / (a + b + c + d) * 100,
                                         [cls("bass_cad", "windows"), cls("bass_other", "windows"), cls("other_cad", "windows"), cls("other_other", "windows")], "ventanas bajo / total"),
        fd(0), "Porcentaje de ventanas en el bajo (sin signo %).")
    # ---- unicidad (porcentaje sin signo)
    uniq = json_of(UNIQ)

    def uc(rep, n, f):
        return V(next(r for r in uniq["curve"][rep] if r["n"] == n)[f], [UNIQ], f"{UNIQ} :: curve.{rep}[n={n}].{f}")
    for n in (4, 6, 7, 8, 12):
        add(f"uniq_pcross_ivr_n{n}", uc("IVR", n, "p_cross"), fpn(1), f"P_cross({n}) IVR en % (sin signo %).")
    for n in (4, 6, 8, 9, 12):
        add(f"uniq_ppair_ivr_n{n}", uc("IVR", n, "p_pair"), fpn(2), f"P_pair({n}) IVR en % (sin signo %).")
    add("uniq_pcross_iv_n8", uc("IV", 8, "p_cross"), fpn(1), "P_cross(8) IV en % (sin signo %).")
    add("uniq_ppair_iv_n8", uc("IV", 8, "p_pair"), fpn(2), "P_pair(8) IV en % (sin signo %).")
    for a in ("pre1750", "1750_1800", "1800_1830"):
        lab = JP[SFX[a]]
        add(f"uniq_ppair_ivr_n8_{a}", V(next(r for r in uniq["curve_by_period"]["IVR"][lab] if r["n"] == 8)["p_pair"], [UNIQ],
                                         f"{UNIQ} :: curve_by_period.IVR.{lab}[n=8].p_pair"), fpn(2), f"P_pair(8) IVR dentro de {lab} en % (sin signo %).")
    # ---- calibracion
    kj = json_of(KNJ)
    kc = csv_of(KNC)
    D40 = {"lap": "Laplace", "kn": "Kneser-Ney", "hier": "jerárquico"}
    for m in ("lap", "kn", "hier"):
        for i, (nm, f) in enumerate((("slope", fd(2)), ("mae", fd(2)), ("bias", fd(2)))):
            col = ["pendiente", "MAE log", "sesgo"][i]
            add(f"calib_{m}_{nm}", V(kj["summary"][f"{m}|todas"][i], [KNJ], f"{KNJ} :: summary.{m}|todas[{i}]"), f,
                f"{nm} (2 decimales, como D-40), 200 ventanas.", xc=[Xc(MC(DEC, r"^### D-40", 0, {"modelo": D40[m]}, col), "es", label="DECISIONES.md D-40")])
    seen = kc[kc.obs_occ > 0]
    bands = [("[0, 1)", 0, 1), ("[3, 30)", 3, 30), ("[30, 300)", 30, 300), ("[300, 3000)", 300, 3000), ("[3000, 1e+12)", 3000, 1e12)]
    MDB = lambda lab, col: MC(KNM, r"^## obs/pred por tramo", 0, {"tramo E (KN)": lab}, col)  # noqa: E731
    MDC = {"lap": "Laplace", "kn": "KN", "hier": "jerárquico"}

    def ratio(m, lo, hi):
        b = seen[(seen.pred_occ_kn >= lo) & (seen.pred_occ_kn < hi)]
        return b.obs_occ.sum() / b[f"pred_occ_{m}"].sum()
    add("calib_band01_n", csv_val(KNC, lambda d: int(((seen.pred_occ_kn >= 0) & (seen.pred_occ_kn < 1)).sum()), "ventanas vistas con 0 <= pred_occ_kn < 1"), fi,
        "Ventanas vistas en el tramo E < 1.", xc=[Xc(num(MDB("[0, 1)", "n")), label="kn_calibration.md tramos")])
    for m in ("kn", "hier"):
        add(f"calib_{m}_band01", csv_val(KNC, lambda d, m=m: ratio(m, 0, 1), f"sum(obs)/sum(pred_{m}) en el tramo [0,1) de pred_occ_kn (vistas)"), fd(2),
            f"obs/pred en el tramo E < 1 ({m}).", xc=[Xc(MDB("[0, 1)", MDC[m]), label="kn_calibration.md tramos")])
    for m in ("kn", "hier", "lap"):
        vals = [ratio(m, lo, hi) for _, lo, hi in bands[1:]]
        mdv = [float(parse_num(MDB(lab, MDC[m]).raw)[2]) for lab, _, _ in bands[1:]]
        for nm, fn in (("min", min), ("max", max)):
            add(f"calib_{m}_ge3_{nm}", csv_val(KNC, lambda d, vals=vals, fn=fn: fn(vals), f"{nm} de obs/pred ({m}) en los 4 tramos E >= 3 (vistas)"), fd(2),
                f"{nm} del obs/pred por tramo, E >= 3 ({m}).",
                xc=[Xc(V(f"{fn(mdv):.2f}", [KNM], f"{KNM} :: {nm} de las celdas {MDC[m]} de los 4 tramos >= 3"), label="kn_calibration.md tramos")])
    pr = csv_of(KNP)
    for key, col in (("calib_presence_obs", "present"), ("calib_presence_df", "df_pred"), ("calib_presence_poisson_kn", "p_present_kn")):
        add(key, csv_val(KNP, lambda d, col=col: d[col].mean(), f"mean({col})"), fpn(1), f"{col} medio en % (sin signo %).")
    dfb = MDX = md_tables(KNM, r"^## DF: presencia")[0]
    rows = {r[0]: r for r in dfb[1]}
    h = dfb[0]
    ov = []
    for lab in ("[0.01, 0.05)", "[0.05, 0.1)", "[0.1, 0.2)"):
        r = rows[lab]
        ov.append(float(r[h.index("1−e^(−E) KN")]) / float(r[h.index("presencia observada")]))

    def over(d):
        out = []
        for lo, hi in ((0.01, 0.05), (0.05, 0.1), (0.1, 0.2)):
            b = d[(d.df_pred >= lo) & (d.df_pred < hi)]
            out.append(b.p_present_kn.mean() / b.present.mean())
        return out
    for nm, fn in (("min", min), ("max", max)):
        add(f"calib_poisson_over_{nm}", csv_val(KNP, lambda d, fn=fn: fn(over(d)), "mean(p_present_kn)/mean(present) en bins df_pred [0.01,0.05),[0.05,0.1),[0.1,0.2)"), fd(1),
            f"{nm} del sobre-ajuste de 1-e^(-E).", xc=[Xc(V(f"{fn(ov):.1f}", [KNM], f"{KNM} :: cociente KN/observado por bin DF"), label="kn_calibration.md bins DF")])
    # ---- lambda
    kl = json_of("results/kn_lambda_n8.json")
    add("lambda_heldout_works", V(len(kl["holdout_works_used"]), ["results/kn_lambda_n8.json"], "results/kn_lambda_n8.json :: len(holdout_works_used)"), fi,
        "Obras de reserva (n = 8, 20 %).")
    for key, lam in (("star", "0.45"), ("l0", "0.0"), ("l1", "1.0"), ("l025", "0.25"), ("l075", "0.75")):
        add(f"lambda_ll_n8_{key}", J("results/kn_lambda_n8.json", "loglik_per_window", lam), fd(2), f"Log-verosimilitud por ventana, n = 8, lambda = {lam}.",
            xc=[Xc(csv_cell(LAMG, {"n": 8, "lam": float(lam)}, "loglik"), label="lambda_by_n_grid.csv")])
    lam = csv_of(LAMC)
    for key, col in (("slope", "pendiente"), ("mae", "MAE_log"), ("obspred", "obs_pred")):
        add(f"lambda_{key}_n8", csv_cell(LAMC, {"n": 8}, col), fd(2), f"{col} en lambda*, n = 8 (2 decimales).")
    for key, col in (("slope", "pendiente"), ("obspred", "obs_pred")):
        for nm, fn in (("min", min), ("max", max)):
            add(f"lambda_{key}_{nm}", csv_val(LAMC, lambda d, col=col, fn=fn: float(fn(d[col])), f"{nm}({col}) sobre n"), fd(2), f"{nm} de {col} entre n.")
    # ---- umbrales
    win = csv_of(THW)
    for lab, v in (("pos", 1), ("neg", 0)):
        add(f"thresh_uniform_{lab}_pct", csv_val(THW, lambda d, v=v: d[d.label == v].uniform_rhythm.mean(), f"mean(uniform_rhythm) con label == {v}"), fpn(1),
            f"% de instancias {lab} con ritmo uniforme (sin signo %).")
    for tag in ("df", "e", "comb"):
        tj = {"df": "DF", "e": "E", "comb": "combined"}[tag]
        add(f"thresh_{tag}_fpr_pct", J(THJ, tj, "FPR"), fpn(1), "FPR en % SIN signo % (el texto anade \\,\\%).")
        add(f"thresh_{tag}_sens_pct", J(THJ, tj, "sensitivity"), fpn(1), "Sensibilidad en % SIN signo % (el texto anade \\,\\%).")
    alias("thresh_fpr_df", "thresh_df_fpr_pct")
    alias("thresh_sens_df", "thresh_df_sens_pct")
    for tag in ("e", "comb"):
        for q in ("fpr", "sens"):
            alias(f"thresh_{tag}_{q}", f"thresh_{tag}_{q}_pct", "results.tex la usa seguida de \\,\\%; la clave existente incluye \\%")
    for q in ("fpr", "sens"):
        alias(f"thresh_df_{q}", f"thresh_df_{q}_pct", "CONFLICTO: intro/discussion la usan sin \\,\\% (necesitan \\%); results/protocol con \\,\\% (necesitan _pct)")
    # ---- corpus
    S = SUMMARY
    for k, lab in PER:
        add(f"corpus_winpct_{k}", derived(lambda w, t: 100 * w / t, [J(BASE, "strata", "period", lab, "windows"), J(BASE, "strata", "all", "all", "windows")], "100*windows/total"),
            fd(1), "% de ventanas del periodo, SIN signo %.",
            xc=[Xc(MC(S, r"^## 1\.", 1, {"periodo": lab}, "% ventanas"), label="summary.md §1")])
    add("corpus_units_unknown_pct", derived(lambda a, b: a / b * 100, [KEYS_V("corpus_units_unknown"), KEYS_V("corpus_units_total")], "units_unknown/units_total*100"), fd(0),
        "% de unidades en unknown, SIN signo % (redondeo de summary.md §8).",
        xc=[Xc(MR(S, r"903 de 6735 \((\d+) %\)", 1, r"^## 8\."), label="summary.md §8")])
    coll = list(base["strata"]["collection"])
    add("corpus_n_dcml_sub", V(sum(c.startswith("dcml/") for c in coll), [BASE], "results/base_rate.json :: n de claves strata.collection que empiezan por 'dcml/'"), fi,
        "DERIVADA: subcorpus dcml/* con ventanas (excluye dcml_abc y dcml_mozart_sonatas). A1 debe confirmar que es lo que el texto quiere decir.")
    add("corpus_n_kern_repos", V(sum(c.startswith("kern/") for c in coll), [BASE], "results/base_rate.json :: n de claves strata.collection que empiezan por 'kern/'"), fi,
        "DERIVADA: repositorios kern/* con ventanas. A1 debe confirmar.")
    for k_ in json_of("paper/D-43_pool_counts.json")["counts"]:
        add(k_, J("paper/D-43_pool_counts.json", "counts", k_), fi,
            "propuesta D-43 (borrador), generada por paper/make_null_pool.py desde corpus/works.csv")
    # ---- literal (A3)
    L = json_of(LITJ)
    check_ids([p[k] for p in L["pairs"] for k in ("A", "B")], context="make_numbers:literal")
    chk("literal: t_DF y t_E = thresholds_n8.json", math.isclose(L["t_DF"], json_of(THJ)["DF"]["threshold"]) and math.isclose(L["t_E"], json_of(THJ)["E"]["threshold"]))
    LJ = lambda *p: J(LITJ, *p)  # noqa: E731

    def wilson(k, n, z=1.959963984540054):
        p = k / n
        den = 1 + z * z / n
        c = (p + z * z / (2 * n)) / den
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        return c - h, c + h
    bad = []
    for var in ("default", "noBeethoven"):
        g = L["LS1"][var]["global"]
        for st in ("DF", "E", "combined"):
            lo, hi = wilson(g[st]["k"], g[st]["n"])
            if not (math.isclose(lo, g[st]["wilson95"][0], abs_tol=1e-9) and math.isclose(hi, g[st]["wilson95"][1], abs_tol=1e-9)):
                bad.append(f"{var}.{st}")
    chk("literal: IC de Wilson del JSON = recalculo desde k y n (LS1 global)", not bad, ",".join(bad))
    add("literal_npairs", derived(len, [LJ("pairs")], "len(pairs)"), fi, "Pares Le Cene -> Dawson evaluados.")
    add("literal_spec_commit", LJ("spec_commit"), ft, "Commit de la especificacion LS (fijada antes de medir).")
    add("literal_spec_commit_short", derived(lambda c: c[:7], [LJ("spec_commit")], "spec_commit[:7]"), ft, "Commit de la especificacion, 7 caracteres.")
    add("literal_head_commit", LJ("head_commit"), ft, "HEAD cuando se corrio el script.")
    add("literal_ls1_instances", LJ("LS1", "default", "global", "instances"), fi, "Tipos compartidos de 8 notas (instancias LS-1), suma de los pares.")
    PL = [p["id"] for p in L["pairs"]]
    for var, pre in (("default", "literal_ls1"), ("noBeethoven", "literal_ls1_nobeeth")):
        for st, tg in (("DF", "df"), ("E", "e"), ("combined", "comb")):
            g = ("LS1", var, "global", st)
            add(f"{pre}_sens_{tg}", LJ(*g, "rate"), fpn(1), f"Sensibilidad {st} (LS-1, {var}) en % SIN signo %.")
            add(f"{pre}_sens_{tg}_lo", LJ(*g, "wilson95", 0), fpn(1), f"IC de Wilson 95 %, limite inferior ({st}, {var}).")
            add(f"{pre}_sens_{tg}_hi", LJ(*g, "wilson95", 1), fpn(1), f"IC de Wilson 95 %, limite superior ({st}, {var}).")
            add(f"{pre}_sens_{tg}_k", LJ(*g, "k"), fi, f"Instancias que pasan ({st}, {var}).")
        for st, tg in (("DF", "df"), ("E", "e"), ("combined", "comb")):
            rates = derived(lambda *r: list(r), [LJ("LS1", var, "per_pair", p, st, "rate") for p in PL], "tasas por par")
            add(f"{pre}_sens_{tg}_min", derived(min, [rates], "min por par"), fpn(1), f"Sensibilidad minima entre pares ({st}, {var}).")
            add(f"{pre}_sens_{tg}_max", derived(max, [rates], "max por par"), fpn(1), f"Sensibilidad maxima entre pares ({st}, {var}).")
            for p in PL:
                q = p.lower()
                add(f"{pre}_{q}_{tg}", LJ("LS1", var, "per_pair", p, st, "rate"), fpn(1), f"Sensibilidad {st} en el par {p} ({var}).")
                add(f"{pre}_{q}_{tg}_lo", LJ("LS1", var, "per_pair", p, st, "wilson95", 0), fpn(1), f"Wilson inferior, par {p}, {st}.")
                add(f"{pre}_{q}_{tg}_hi", LJ("LS1", var, "per_pair", p, st, "wilson95", 1), fpn(1), f"Wilson superior, par {p}, {st}.")
        for p in PL:
            add(f"{pre}_{p.lower()}_instances", LJ("LS1", var, "per_pair", p, "instances"), fi, f"Instancias del par {p}.")
        add(f"{pre}_pass_nonuniform", LJ("LS1", var, "global", "pass_DF_nonuniform"), fi, f"Instancias DF con ritmo no uniforme ({var}).")
    # LS-2
    r2 = L["LS2"]["results"]
    lens = sorted(int(x) for x in r2["default"]["all_pairs"])
    add("literal_ls2_lmin", V(lens[0], [LITJ], f"{LITJ} :: min de las longitudes en LS2.results.default.all_pairs"), fi, "Longitud minima de fragmento evaluada (compases).")
    add("literal_ls2_lmax", V(lens[-1], [LITJ], f"{LITJ} :: max de las longitudes en LS2.results.default.all_pairs"), fi, "Longitud maxima de fragmento evaluada (compases).")
    ok80 = [x for x in lens if r2["default"]["all_pairs"][str(x)]["power"]["rate"] >= 0.8]
    add("literal_ls2_l80", V(ok80[0] if ok80 else "n/a", [LITJ], f"{LITJ} :: menor L con potencia global >= 0.8"), (fi if ok80 else ft),
        "Menor longitud (compases) con potencia >= 80 %.")
    for var, pre in (("default", "literal_ls2"), ("noBeethoven", "literal_ls2_nobeeth")):
        for L_ in lens:
            for who in ["all_pairs"] + PL:
                nm = "power" if who == "all_pairs" else f"{who.lower()}_power"
                base_ = ("LS2", "results", var, who, str(L_), "power")
                key = f"{pre}_power_b{L_}" if who == "all_pairs" else f"{pre}_{who.lower()}_power_b{L_}"
                add(key, LJ(*base_, "rate"), fpn(1), f"Potencia LS-2 ({var}, {who}, {L_} compases) en % SIN signo %.")
                add(key + "_lo", LJ(*base_, "wilson95", 0), fpn(1), "Wilson inferior.")
                add(key + "_hi", LJ(*base_, "wilson95", 1), fpn(1), "Wilson superior.")
            add(f"{pre}_windows_b{L_}", J(LITJ, "LS2", "results", var, PL[0], str(L_), "length_windows"), fi,
                f"Ventanas del fragmento de {L_} compases (par {PL[0]}); varia por par.")
    for L_ in lens:
        pw = derived(lambda *r: list(r), [LJ("LS2", "results", "default", p, str(L_), "power", "rate") for p in PL], "potencia por par")
        add(f"literal_ls2_power_b{L_}_min", derived(min, [pw], "min por par"), fpn(1), f"Potencia LS-2 minima entre pares, {L_} compases (sin signo %).")
        add(f"literal_ls2_power_b{L_}_max", derived(max, [pw], "max por par"), fpn(1), f"Potencia LS-2 maxima entre pares, {L_} compases (sin signo %).")
    alias("literal_ls1_pair_min", "literal_ls1_sens_df_min", "A2->A3")
    alias("literal_ls1_pair_max", "literal_ls1_sens_df_max", "A2->A3")
    add("literal_ls2_pool_size", LJ("LS2", "pool_size_used"), fi, "Obras del pool nulo LS-2.")
    add("literal_ls2_pool_windows", LJ("LS2", "pool_windows"), fi, "Ventanas del pool nulo LS-2.")
    add("literal_ls2_n_obs", LJ("LS2", "n_obs"), fi, "Fragmentos por par y longitud.")
    add("literal_ls2_n_null", LJ("LS2", "n_null"), fi, "Fragmentos nulos.")


def KEYS_V(key) -> V:
    k = KEYS[key]
    return V(k["raw"], [s.strip() for s in k["source"].split(",")], f"clave {key}")


# --------------------------------------------------------------------------- salida
def yq(s) -> str:
    return json.dumps(s, ensure_ascii=False)


def yraw(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    return yq(v)


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def render():
    out = ["# Generado por paper/make_numbers.py. No editar a mano.",
           "# Cada valor sale de un archivo versionado; 'locator' dice como se extrajo.",
           "sources:"]
    for rel in sorted(USED):
        out.append(f"  {yq(rel)}: {yq(sha(rel))}")
    out.append("numbers:")
    for k, e in KEYS.items():
        out += [f"  - key: {k}", f"    value: {yraw(e['raw'])}", f"    text: {yq(e['text'])}",
                f"    source: {yq(e['source'])}", f"    locator: {yq(e['locator'])}", f"    note: {yq(e['note'])}",
                f"    status: {e['status']}"]
        if e["checks"]:
            out.append("    checks:")
            out += [f"      - {yq(c)}" for c in e["checks"]]
    yaml_s = "\n".join(out) + "\n"

    tex = [r"% Generado por paper/make_numbers.py. No editar a mano.",
           r"% Uso: \nm{clave}. Una clave inexistente (o con desajuste entre documentos) da error de compilacion.",
           r"\makeatletter",
           r"\def\nm@def#1#2{\expandafter\gdef\csname nm@#1\endcsname{#2}}",
           r"\newcommand{\nm}[1]{%",
           r"  \ifcsname nm@\detokenize{#1}\endcsname",
           r"    \csname nm@\detokenize{#1}\endcsname",
           r"  \else",
           r"    \PackageError{numbers}{Unknown number key `\detokenize{#1}'}{The key is not in paper/numbers.tex; add it to paper/make_numbers.py and regenerate.}%",
           r"  \fi}"]
    for k, e in KEYS.items():
        if e["status"] == "ok":
            tex.append(f"\\nm@def{{{k}}}{{{tex_text(e['text'])}}}")
    tex.append(r"\makeatother")
    tex_s = "\n".join(tex) + "\n"

    bad = [c for c in CHECKS if not c["ok"] and not c.get("warn")]
    n_ok = sum(1 for c in CHECKS if c["ok"])
    mism = {k for k, e in KEYS.items() if e["status"] == "MISMATCH"}
    iss = ["# Incidencias del ledger de numeros", "",
           "Generado por `paper/make_numbers.py` (no editar a mano). Nada se ha corregido: las claves en desajuste "
           "quedan fuera de `paper/numbers.tex` (usarlas da error de compilacion) hasta que la torre decida.", "",
           f"- Claves: {len(KEYS)} ({len(KEYS) - len(mism)} validas, {len(mism)} con desajuste).",
           f"- Comprobaciones cruzadas: {len(CHECKS)} ({n_ok} correctas, {len(bad)} fallidas).", ""]
    iss.append("## Desajustes")
    iss.append("")
    if not bad:
        iss.append("Ninguno.")
    else:
        iss += ["| clave | valor del ledger | documento y localizador | valor en el documento |", "|---|---|---|---|"]
        for c in bad:
            iss.append(f"| {c['key'] or c['label']} | {c['ledger_value']} | {c['loc']} | {c['doc_text']} |")
    iss += ["", "## Avisos (no son desajustes numericos)", ""]
    iss += [f"- {n}" for n in NOTES] or ["Ninguno."]
    by_doc: dict[str, list[int]] = {}
    for c in CHECKS:
        d = by_doc.setdefault(c["doc"], [0, 0])
        d[0] += 1
        d[1] += c["ok"]
    iss += ["", "## Comprobaciones por documento", "", "| documento | comprobaciones | correctas |", "|---|---|---|"]
    iss += [f"| {d} | {a} | {b} |" for d, (a, b) in sorted(by_doc.items())]
    iss_s = "\n".join(iss) + "\n"
    # aliases
    al = ["requested,existing,note"]
    for r_, e_, w_ in ALIASES:
        assert e_ in KEYS, f"alias {r_} -> clave inexistente {e_}"
        assert r_ not in KEYS or w_.startswith("CONFLICTO") or "\\%" in w_, f"alias {r_} choca con una clave existente"
        al.append(f"{r_},{e_},\"{w_}\"" if w_ else f"{r_},{e_},")
    alias_s = "\n".join(al) + "\n"
    # indice
    fams = [("corpus_", "Corpus"), ("baserate_", "Tasas base"), ("null_", "Nulo de permutacion"), ("uniq_", "Unicidad"),
            ("calib_", "Calibracion del fondo"), ("lambda_", "lambda(n)"), ("thresh_", "Umbrales n = 8"), ("literal_", "Sensibilidad a cita literal")]
    ix = ["# Indice de claves del ledger", "",
          "Generado por `paper/make_numbers.py` (no editar). Una linea por clave: `\\nm{clave}` produce el texto mostrado. "
          "Las claves con sufijo `_pct` o los porcentajes marcados `(sin %)` no llevan signo de porcentaje: el texto anade `\\,\\%`. "
          "Claves con desajuste (MISMATCH) no existen en `numbers.tex`. Alias pedidos: `paper/research/ledger_aliases.csv`.", ""]
    for pre, title in fams:
        ks = [k for k in KEYS if k.startswith(pre)]
        ix += ["", f"## {title} ({len(ks)})", ""]
        for k in ks:
            e = KEYS[k]
            flag = " **MISMATCH**" if e["status"] != "ok" else ""
            ix.append(f"- `{k}` = {e['text']}{flag}")
    index_s = "\n".join(ix) + "\n"
    return yaml_s, tex_s, iss_s, len(bad), alias_s, index_s


REASONS = {
    "corpus_n_units_fail": "Tres cifras incompatibles (27 / 30 / 32, ver Avisos); el paper no la cita hasta que el usuario lo resuelva.",
    "corpus_pool_orch_works": "Requiere clasificar instrumentacion del catalogo (obras puramente orquestales del estrato); no hay resultado versionado que lo cuente. Lo calcula quien defina el pool (A3/A1) con la guardia.",
    "corpus_pool_orch_composers": "Idem: compositores del pool orquestal.",
    "corpus_pool_choral_works": "Idem: obras para coro y orquesta.",
    "corpus_pool_orchext_works": "Idem: clase orquestal ampliada.",
    "clave": "Marcador de ejemplo en main.tex, no es una clave.",
    "key": "Marcador de ejemplo en results.tex, no es una clave.",
}


def scan_section() -> str:
    import glob
    used: dict[str, set] = {}
    for f in sorted(glob.glob(str(PAPER / "sections" / "*.tex")) + glob.glob(str(PAPER / "tables" / "*.tex")) +
                    glob.glob(str(PAPER / "figures" / "*.tex")) + [str(PAPER / "main.tex")]):
        try:
            t = Path(f).read_text(encoding="utf-8")
        except OSError:
            continue
        for k in re.findall(r"\\nm\{([^}#]+)\}", t):
            used.setdefault(k, set()).add(Path(f).name)
    al = {r: (e, w) for r, e, w in ALIASES}
    lines = ["", SCAN_MARK, "", "Escaneo de `paper/sections`, `paper/tables`, `paper/figures/*.tex` y `main.tex` (no entra en `--check`).", ""]
    unres, aliased, mism = [], [], []
    for k in sorted(used):
        if k in KEYS and KEYS[k]["status"] == "ok" and k not in al:
            continue
        if k in KEYS and KEYS[k]["status"] != "ok":
            mism.append(k)
        elif k in al:
            aliased.append(k)
        else:
            unres.append(k)
    lines.append(f"- Claves distintas usadas: {len(used)}; resueltas directamente: {len(used) - len(unres) - len(aliased) - len(mism)}.")
    lines += ["", f"### Con alias (la torre corrige el texto; {len(aliased)})", ""]
    lines += [f"- `{k}` -> `{al[k][0]}`" + (f" ({al[k][1]})" if al[k][1] else "") + f" [{', '.join(sorted(used[k]))}]" for k in aliased] or ["Ninguna."]
    lines += ["", f"### Sin fuente versionada o con desajuste ({len(unres) + len(mism)})", ""]
    lines += [f"- `{k}` [{', '.join(sorted(used[k]))}]: {REASONS.get(k, 'SIN RESOLVER: no esta en el ledger ni en los alias y no se ha derivado de una fuente versionada.')}" for k in unres]
    lines += [f"- `{k}` [{', '.join(sorted(used[k]))}]: desajuste entre documentos (ver Desajustes); no existe en numbers.tex." for k in mism]
    lines += ["", "### Notas de formato y nombres", "",
              "- `calib_df_slope` y `calib_df_mae` existen con 3 decimales (1.021, 0.192; precision de kn_calibration.md); A2 esperaba 2 decimales. Lo mismo `calib_unseen_e_lap/kn` (1.021 / 0.043).",
              "- `thresh_df_fpr`, `thresh_df_sens` incluyen `\\%`: usadas con `\\,\\%` detras (results, protocol) darian `%%`. Para eso existen los gemelos `thresh_{df,e,comb}_{fpr,sens}_pct`.",
              "- Las claves de porcentaje pedidas por A2 (`*_pct_*`, `uniq_p*_ivr_*`, `literal_*`) no llevan `%`; las del ledger original (`baserate_d4_prev_*`, `corpus_windows_pct_*`) si.",
              "- `literal_spec_commit` = a240875...; el JSON de A3 y el mensaje de la torre mencionan 4c00ffa como commit del resultado; el ledger lee solo `spec_commit` y `head_commit` del JSON."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="recalcula y compara con lo escrito (no escribe)")
    a = ap.parse_args()
    build()
    build_requests()
    yaml_s, tex_s, iss_s, n_bad, alias_s, index_s = render()
    iss_s += scan_section()
    if a.check:
        bad = []
        cut = lambda t: None if t is None else t.split(SCAN_MARK)[0]  # noqa: E731
        for p, s in ((OUT_YAML, yaml_s), (OUT_TEX, tex_s), (OUT_ISSUES, cut(iss_s)), (OUT_ALIASES, alias_s), (OUT_INDEX, index_s)):
            cur = p.read_text(encoding="utf-8") if p.exists() else None
            if p == OUT_ISSUES:
                cur = cut(cur)
            if cur != s:
                bad.append(p.relative_to(ROOT))
        if bad:
            print("CHECK FALLIDO: difieren de lo recalculado:", *map(str, bad))
            return 1
        print(f"CHECK OK: {len(KEYS)} claves, {len(CHECKS)} comprobaciones cruzadas, {n_bad} desajustes (reproducible).")
        return 2 if n_bad else 0
    OUT_ISSUES.parent.mkdir(parents=True, exist_ok=True)
    OUT_YAML.write_text(yaml_s, encoding="utf-8")
    OUT_TEX.write_text(tex_s, encoding="utf-8")
    OUT_ISSUES.write_text(iss_s, encoding="utf-8")
    OUT_ALIASES.write_text(alias_s, encoding="utf-8")
    OUT_INDEX.write_text(index_s, encoding="utf-8")
    print(f"escrito: {len(KEYS)} claves, {len(CHECKS)} comprobaciones cruzadas, {n_bad} desajustes")
    return 2 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
