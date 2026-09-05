"""Construye corpus/works.csv, corpus/composers.csv, corpus/manual_dates.csv y
results/missing_dates.md a partir de corpus/raw/.

Unidad de fila: `unit_id` (un fichero o directorio parseable = normalmente un movimiento).
`work_id` agrupa los movimientos de una obra (D-15).  Ver docs/DECISIONES.md D-05..D-17.

Uso:  .venv/bin/python scripts/build_catalog.py
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
OUT_WORKS = ROOT / "corpus" / "works.csv"
OUT_COMPOSERS = ROOT / "corpus" / "composers.csv"
MANUAL_DATES = ROOT / "corpus" / "manual_dates.csv"
OUT_MISSING = ROOT / "results" / "missing_dates.md"

ACTIVE_START_AGE = 15          # D-17: periodo activo = [nacimiento+15, muerte]
PERIOD_BINS = [("<1750", -9999, 1749), ("1750–1800", 1750, 1799),
               ("1800–1830", 1800, 1829), ("1830–1900", 1830, 1899),
               (">1900", 1900, 9999)]
# prioridad para duplicados entre colecciones (menor = primaria), D-09
PRIORITY = {"dcml": 0, "musedata": 1, "kern": 2, "s3": 3, "openscore": 4, "m21": 9}   # D-29

COLUMNS = ["unit_id", "work_id", "collection", "composer", "composer_id", "title",
           "movement", "composition_year", "year_start", "year_end", "year_source",
           "year_certainty", "period", "period_source", "format", "path", "license",
           "catalog_key", "duplicate_group", "is_primary", "is_target", "in_analysis"]

# ----------------------------------------------------------------------------
# compositores
# ----------------------------------------------------------------------------
PARTICLES = {"van", "von", "de", "da", "di", "del", "della", "der", "le", "la", "du", "des", "y"}

# vidas de compositores que no aparecen en las tablas de OpenScore (fallback D-17)
LIFESPANS = {
    "bach_js": ("Johann Sebastian Bach", 1685, 1750),
    "bach_cpe": ("Carl Philipp Emanuel Bach", 1714, 1788),
    "bach_wf": ("Wilhelm Friedemann Bach", 1710, 1784),
    "bach_jc": ("Johann Christian Bach", 1735, 1782),
    "handel_gf": ("Georg Friedrich Händel", 1685, 1759),
    "vivaldi_a": ("Antonio Vivaldi", 1678, 1741),
    "corelli_a": ("Arcangelo Corelli", 1653, 1713),
    "telemann_gp": ("Georg Philipp Telemann", 1681, 1767),
    "mozart_wa": ("Wolfgang Amadeus Mozart", 1756, 1791),
    "haydn_fj": ("Franz Joseph Haydn", 1732, 1809),
    "haydn_j": ("Joseph Haydn", 1732, 1809),
    "beethoven_l": ("Ludwig van Beethoven", 1770, 1827),
    "scarlatti_d": ("Domenico Scarlatti", 1685, 1757),
    "chopin_f": ("Frédéric Chopin", 1810, 1849),
    "scriabin_a": ("Alexander Scriabin", 1872, 1915),
    "joplin_s": ("Scott Joplin", 1868, 1917),
    "couperin_f": ("François Couperin", 1668, 1733),
    "frescobaldi_g": ("Girolamo Frescobaldi", 1583, 1643),
    "sweelinck_jp": ("Jan Pieterszoon Sweelinck", 1562, 1621),
    "peri_j": ("Jacopo Peri", 1561, 1633),
    "monteverdi_c": ("Claudio Monteverdi", 1567, 1643),
    "pergolesi_gb": ("Giovanni Battista Pergolesi", 1710, 1736),
    "kozeluch_l": ("Leopold Koželuch", 1747, 1818),
    "pleyel_i": ("Ignaz Pleyel", 1757, 1831),
    "schubert_f": ("Franz Schubert", 1797, 1828),
    "mendelssohn_f": ("Felix Mendelssohn", 1809, 1847),
    "schumann_r": ("Robert Schumann", 1810, 1856),
    "schumann_c": ("Clara Schumann", 1819, 1896),
    "liszt_f": ("Franz Liszt", 1811, 1886),
    "wagner_r": ("Richard Wagner", 1813, 1883),
    "grieg_e": ("Edvard Grieg", 1843, 1907),
    "tchaikovsky_pi": ("Pyotr Ilyich Tchaikovsky", 1840, 1893),
    "dvorak_a": ("Antonín Dvořák", 1841, 1904),
    "mahler_g": ("Gustav Mahler", 1860, 1911),
    "debussy_c": ("Claude Debussy", 1862, 1918),
    "ravel_m": ("Maurice Ravel", 1875, 1937),
    "medtner_n": ("Nikolai Medtner", 1880, 1951),
    "rachmaninoff_s": ("Sergei Rachmaninoff", 1873, 1943),
    "bartok_b": ("Béla Bartók", 1881, 1945),
    "poulenc_f": ("Francis Poulenc", 1899, 1963),
    "schulhoff_e": ("Erwin Schulhoff", 1894, 1942),
}
# alias -> id canónico (variantes ortográficas entre fuentes)
ALIASES = {"haydn_j": "haydn_fj", "handel_g": "handel_gf", "handel_gfh": "handel_gf",
           "haendel_gf": "handel_gf", "tchaikovsky_p": "tchaikovsky_pi",
           "rachmaninov_s": "rachmaninoff_s", "rachmaninoff_sv": "rachmaninoff_s",
           "beethoven_lv": "beethoven_l", "mozart_w": "mozart_wa",
           "kozeluh_l": "kozeluch_l", "kozeluch_la": "kozeluch_l", "koreluch_l": "kozeluch_l",
           "scriabin_an": "scriabin_a", "skryabin_a": "scriabin_a", "chopin_ff": "chopin_f",
           "mendelssohn_fb": "mendelssohn_f", "mendelssohn-bartholdy_f": "mendelssohn_f",
           "bach_jsb": "bach_js", "bach_j": "bach_js", "schumann_rf": "schumann_r"}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def composer_id(name: str) -> str:
    """'Beethoven, Ludwig van' / 'Ludwig van Beethoven' / 'Beethoven,_Ludwig_van' -> beethoven_l"""
    n = strip_accents(name).replace("_", " ").strip()
    n = re.sub(r"\(.*?\)", "", n).strip().strip(".")
    if "," in n:
        sur, given = [x.strip() for x in n.split(",", 1)]
    else:
        toks = n.split()
        if not toks:
            return "unknown"
        sur, given = toks[-1], " ".join(toks[:-1])
    sur = re.sub(r"[^a-z\-]", "", sur.lower())
    initials = "".join(t[0].lower() for t in given.replace("-", " ").split()
                       if t.lower() not in PARTICLES and t[0].isalpha())
    cid = f"{sur}_{initials}" if initials else sur
    return ALIASES.get(cid, cid)


class Composers:
    def __init__(self):
        self.info: dict[str, dict] = {}  # id -> {name, born, died, sources}

    def add(self, name: str, born=None, died=None, source=""):
        cid = composer_id(name)
        rec = self.info.setdefault(cid, {"name": name, "born": "", "died": "", "sources": set()})
        if cid in LIFESPANS:
            rec["name"] = LIFESPANS[cid][0]
            rec["born"], rec["died"] = LIFESPANS[cid][1], LIFESPANS[cid][2]
        if born and not rec["born"]:
            rec["born"] = int(born)
        if died and not rec["died"]:
            rec["died"] = int(died)
        if "," in name and "," not in rec["name"]:
            pass  # preferimos "Nombre Apellido" para mostrar
        elif "," not in name and "," in rec["name"]:
            rec["name"] = name
        rec["sources"].add(source)
        return cid

    def lifespan(self, cid):
        r = self.info.get(cid)
        if r and r["born"] and r["died"]:
            return int(r["born"]), int(r["died"])
        return None


COMP = Composers()

# ----------------------------------------------------------------------------
# utilidades de fechas y catálogo
# ----------------------------------------------------------------------------
YEAR_RE = re.compile(r"(\d{4})")


def parse_year_range(text: str):
    """'1798///-1800///' -> (1798, 1800); '~1750-1755' -> (1750,1755); '1774' -> (1774,1774)."""
    ys = [int(y) for y in YEAR_RE.findall(text or "")]
    ys = [y for y in ys if 1400 <= y <= 2100]
    if not ys:
        return None
    return min(ys), max(ys)


def certainty_for(text: str, lo: int, hi: int) -> str:
    if lo != hi:
        return "range"
    if re.search(r"[~c]\.?\s*\d|circa|ca\.", (text or "").lower()):
        return "approx"
    return "exact"


def period_of(year) -> str:
    if year in (None, ""):
        return "unknown"
    y = int(year)
    for name, lo, hi in PERIOD_BINS:
        if lo <= y <= hi:
            return name
    return "unknown"


def period_of_range(lo: int, hi: int) -> str:
    """Bin único que contiene [lo, hi] entero; si cruza, 'unknown' (D-17)."""
    for name, blo, bhi in PERIOD_BINS:
        if blo <= lo and hi <= bhi:
            return name
    return "unknown"


MOZART_SONATA_K = {1: 279, 2: 280, 3: 281, 4: 282, 5: 283, 6: 284, 7: 309, 8: 310, 9: 311,
                   10: 330, 11: 331, 12: 332, 13: 333, 14: 457, 15: 545, 16: 570, 17: 576, 18: 533}
BEETHOVEN_SYM_OP = {1: 21, 2: 36, 3: 55, 4: 60, 5: 67, 6: 68, 7: 92, 8: 93, 9: 125}


def catalog_key(text: str, composer: str = "") -> str:
    """Clave normalizada de catálogo a partir de texto libre (título, número de obra, ruta)."""
    t = strip_accents(text or "").lower().replace("_", " ")
    if composer == "schubert_f":
        m = re.search(r"\bd\.?\s*(\d{2,4})\b", t)
        if m:
            return f"d{int(m.group(1))}"
    m = re.search(r"\bbwv\s*\.?\s*(\d+[a-z]?)", t)
    if m:
        return f"bwv{m.group(1)}"
    m = re.search(r"\bhwv\s*\.?\s*(\d+[a-z]?)", t)
    if m:
        return f"hwv{m.group(1)}"
    m = re.search(r"\brv\s*\.?\s*(\d+[a-z]?)", t)
    if m:
        return f"rv{m.group(1)}"
    m = re.search(r"\bk\.?\s*v?\.?\s*(\d+)[a-z]?\b", t)
    if m and "hob" not in t:
        return f"k{int(m.group(1))}"
    m = re.search(r"\bhob\.?\s*([ivx]+)\s*[:.]\s*(\d+)", t)
    if m:
        return f"hob{m.group(1)}:{int(m.group(2))}"
    m = re.search(r"\bop(?:us|\.)?\s*(\d+)\s*(?:[/,]|no\.?|n\.?|nr\.?)\s*(\d+)", t)
    if m:
        return f"op{int(m.group(1))}/{int(m.group(2))}"
    m = re.search(r"\bop(?:us|\.)?\s*(\d+)", t)
    if m:
        return f"op{int(m.group(1))}"
    m = re.search(r"\bl\.?\s*(\d+)\s*k\.?\s*(\d+)", t)   # Scarlatti L..K..
    if m:
        return f"k{int(m.group(2))}"
    m = re.search(r"\bsv\s*(\d+)", t)
    if m:
        return f"sv{int(m.group(1))}"
    m = re.search(r"\bd\.?\s*(\d{2,4})\b", t)          # Schubert Deutsch
    if m:
        return f"d{int(m.group(1))}"
    return ""


def slug(s: str, n=40) -> str:
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:n]


def rel(p: Path) -> str:
    return str(p.relative_to(RAW))


# ----------------------------------------------------------------------------
# filas
# ----------------------------------------------------------------------------
def row(**kw) -> dict:
    r = {c: "" for c in COLUMNS}
    r["is_target"] = 0
    r["in_analysis"] = 1
    r["is_primary"] = 1
    r.update(kw)
    return r


def apply_year(r: dict, lo, hi, source: str, certainty: str, raw_text=""):
    if lo is None:
        return
    r["year_start"], r["year_end"] = lo, hi
    # D-30: range -> punto medio; exact/approx -> el año
    r["composition_year"] = int(round((lo + hi) / 2)) if certainty == "range" else hi
    r["year_source"] = source
    r["year_certainty"] = certainty
    r["period"] = period_of(r["composition_year"])
    r["period_source"] = "year_midpoint" if certainty == "range" else "year"


# ---------------------------------------------------------------- kern
KERN_REPOS = {
    # repo: (licencia, regex de fichero -> (work, mov) o None -> usar OPS/ONM)
    "beethoven-piano-sonatas": ("no LICENSE (craigsapp)", r"^(sonata\d+)-(\d+)$"),
    "beethoven-string-quartets": ("no LICENSE (craigsapp)", r"^(quartet\d+)-(\d+[a-z]?)$"),
    "haydn-piano-sonatas": ("CC BY-SA 4.0", r"^(sonata\d+)-(\d+)$"),
    "mozart-piano-sonatas": ("CC BY-SA 4.0", r"^(sonata\d+)-(\d+)$"),
    "scarlatti-keyboard-sonatas": ("CC BY-SA 4.0", r"^(L\d+K\d+)()$"),
    "chopin-mazurkas": ("no LICENSE (craigsapp)", "OPS"),
    "chopin-preludes": ("no LICENSE (craigsapp)", "OPS"),
    "bach-370-chorales": ("CC BY-SA 4.0", r"^(chor\d+)()$"),
    "art-of-the-fugue": ("no LICENSE (craigsapp)", r"^(artfugue)-(\d+)$"),
    "bach-musical-offering": ("no LICENSE (craigsapp)", r"^(offering)-(\d+)$"),
    "bach-wtc": ("no LICENSE (humdrum-tools)", r"^(wtc\d(?:[fp])\d+)()$"),
    "vivaldi-op6": ("no LICENSE (craigsapp)", r"^(vivaldi-op\d+n\d+)m(\d+)$"),
    "scriabin": ("no LICENSE (craigsapp)", "OPS"),
    "joplin": ("CC BY-SA 4.0", r"^(.+?)()$"),
    "humdrum-haydn-quartets": ("no LICENSE (musedata)", r"^(op\d+n\d+)-(\d+)$"),
    "humdrum-mozart-quartets": ("no LICENSE (musedata)", r"^(k\d+)-(\d+)$"),
    "humdrum-haydn-symphonies": ("CC BY-SA 4.0", r"^(sym\d+)([a-z])$"),
    "humdrum-bach-brandenburg": ("CC BY-SA 4.0", r"^(bwv\d+)([a-z])$"),
    "humdrum-corelli": ("CC BY-SA 4.0", r"^(op\d+n\d+)-?([a-z]|\d+)$"),
}


KERN_COMPOSER = {
    "beethoven-piano-sonatas": "Ludwig van Beethoven", "beethoven-string-quartets": "Ludwig van Beethoven",
    "haydn-piano-sonatas": "Joseph Haydn", "mozart-piano-sonatas": "Wolfgang Amadeus Mozart",
    "scarlatti-keyboard-sonatas": "Domenico Scarlatti", "chopin-mazurkas": "Frédéric Chopin",
    "chopin-preludes": "Frédéric Chopin", "bach-370-chorales": "Johann Sebastian Bach",
    "art-of-the-fugue": "Johann Sebastian Bach", "bach-musical-offering": "Johann Sebastian Bach",
    "bach-wtc": "Johann Sebastian Bach", "vivaldi-op6": "Antonio Vivaldi",
    "scriabin": "Alexander Scriabin", "joplin": "Scott Joplin",
    "humdrum-haydn-quartets": "Joseph Haydn", "humdrum-mozart-quartets": "Wolfgang Amadeus Mozart",
    "humdrum-haydn-symphonies": "Joseph Haydn", "humdrum-bach-brandenburg": "Johann Sebastian Bach",
    "humdrum-corelli": "Arcangelo Corelli",
}


def kern_refs(path: Path) -> dict:
    refs = {}
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.startswith("!!!"):
                m = re.match(r"!!!([A-Za-z0-9@-]+):\s*(.*)", line)
                if m and m.group(1) not in refs:
                    refs[m.group(1)] = m.group(2).strip()
    return refs


def read_kern():
    rows = []
    for repo, (lic, pat) in KERN_REPOS.items():
        base = RAW / "kern" / repo
        files = sorted(base.rglob("*.krn"))
        for f in files:
            refs = kern_refs(f)
            stem = f.stem
            if pat == "OPS":
                ops = refs.get("OPS", "").replace("Op.", "").replace("op.", "").strip()
                work_key = f"op{ops}" if ops else stem
                mov = refs.get("ONM", "").replace("No.", "").strip() or stem
            else:
                m = re.match(pat, stem)
                work_key, mov = (m.group(1), m.group(2)) if m else (stem, "")
                if repo == "humdrum-corelli":   # op01n01a y op5n1-02 -> op1n1
                    mm = re.match(r"op(\d+)n(\d+)", work_key)
                    work_key = f"op{int(mm.group(1))}n{int(mm.group(2))}"
                if repo == "bach-wtc":          # pareja preludio+fuga = obra; f/p = movimiento
                    mm = re.match(r"(wtc\d)([fp])(\d+)", stem)
                    work_key, mov = f"{mm.group(1)}-{mm.group(3)}", {"p": "1-prelude", "f": "2-fugue"}[mm.group(2)]
            comp_name = KERN_COMPOSER[repo]
            cid = COMP.add(comp_name, source=f"kern/{repo}")
            title = refs.get("OTL", "") or stem
            work_id = f"kern-{repo}-{work_key}"
            r = row(unit_id=f"{work_id}--{stem}", work_id=work_id, collection=f"kern/{repo}",
                    composer=comp_name, composer_id=cid, title=title, movement=mov,
                    format="kern", path=rel(f), license=lic)
            # fechas (D-05): ODT > MPD > PDT(publicación)
            for key, src in (("ODT", "kern_ODT"), ("MPD", "kern_MPD")):
                pr = parse_year_range(refs.get(key, ""))
                if pr:
                    apply_year(r, pr[0], pr[1], src, certainty_for(refs.get(key, ""), *pr))
                    break
            else:
                pr = parse_year_range(refs.get("PDT", ""))
                if pr:
                    apply_year(r, pr[0], pr[1], "kern_PDT_publication", "approx")
            cat_text = " ".join([refs.get("OPS", ""), refs.get("ONM", ""), refs.get("SCT", ""),
                                 title, stem])
            if repo in ("beethoven-piano-sonatas",):
                cat_text = f"op.{refs.get('OPS','')}/{refs.get('ONM','') or '0'} "
                if not refs.get("ONM"):
                    cat_text = f"op.{refs.get('OPS','')} "
            if repo == "mozart-piano-sonatas":
                mm = re.match(r"sonata(\d+)", stem)
                k = MOZART_SONATA_K.get(int(mm.group(1))) if mm else None
                cat_text = f"K.{k}" if k else cat_text
            if repo == "humdrum-haydn-symphonies":
                cat_text = f"Hob. I:{int(re.sub(r'[^0-9]', '', work_key))}"
            if repo == "bach-370-chorales":
                cat_text = ""       # D-24: varios corales comparten BWV (cantata); no se deduplican por BWV
            if repo == "humdrum-corelli":
                mm = re.match(r"op(\d+)n(\d+)", work_key)
                cat_text = f"op.{int(mm.group(1))}/{int(mm.group(2))}"
            if repo == "scarlatti-keyboard-sonatas":
                mm = re.match(r"L(\d+)K(\d+)", stem)
                cat_text = f"K.{int(mm.group(2))}"
            r["catalog_key"] = catalog_key(cat_text)
            rows.append(r)
    return rows


# ---------------------------------------------------------------- DCML
def read_dcml():
    rows = []
    repos = [RAW / "dcml_abc", RAW / "dcml_mozart_sonatas"] + sorted((RAW / "dcml").iterdir())
    for base in repos:
        meta = base / "metadata.tsv"
        if not meta.exists():
            continue
        name = base.name if base.name.startswith("dcml_") else f"dcml/{base.name}"
        lic = "CC BY-NC-SA 4.0"
        with open(meta, encoding="utf-8") as fh:
            recs = list(csv.DictReader(fh, delimiter="\t"))
        for rec in recs:
            piece = rec.get("piece") or rec.get("fname") or Path(rec.get("rel_path", "")).stem
            notes = base / "notes" / f"{piece}.notes.tsv"
            if not notes.exists():
                continue
            comp_name = rec.get("composer", "").strip() or {
                "debussy_preludes": "Claude Debussy"}.get(base.name, "")
            cid = COMP.add(comp_name, source=name)
            wnum, wtitle = rec.get("workNumber", "").strip(), rec.get("workTitle", "").strip()
            movnum = rec.get("movementNumber", "").strip()
            if base.name in ("ABC", "dcml_abc"):
                mm = re.match(r"(n\d+op\d+(?:-\d+)?)_(\d+)", piece)
                work_key, mov = mm.group(1), mm.group(2)
                cat = catalog_key(work_key.replace("-", " no. ").replace("op", " op. "))
                title = f"String Quartet {work_key[3:]}"
            elif base.name in ("mozart_piano_sonatas", "dcml_mozart_sonatas"):
                mm = re.match(r"(K\d+)-(\d+)", piece)
                work_key, mov = mm.group(1), mm.group(2)
                cat = catalog_key(work_key)
                title = wtitle or work_key
            elif wnum and movnum:
                work_key, mov = slug(wnum, 30), movnum
                cat = catalog_key(wnum, cid)
                title = wtitle or wnum
            else:
                work_key, mov = slug(piece, 40), ""
                cat = catalog_key(wnum or wtitle or piece)
                title = wtitle or piece
            work_id = f"{name.replace('/', '-')}-{work_key}"
            r = row(unit_id=f"{work_id}--{slug(piece, 50)}", work_id=work_id, collection=name,
                    composer=comp_name, composer_id=cid, title=title, movement=mov or piece,
                    format="dcml_tsv", path=rel(notes), license=lic, catalog_key=cat)
            cs, ce = rec.get("composed_start", "").strip(), rec.get("composed_end", "").strip()
            lo = int(cs) if cs.isdigit() else None
            hi = int(ce) if ce.isdigit() else None
            if hi is None and lo is not None:
                hi = lo
            if hi is not None:
                if lo is None:            # '..-1720' terminus ante quem
                    apply_year(r, hi, hi, "dcml_metadata", "approx")
                else:
                    apply_year(r, lo, hi, "dcml_metadata", "exact" if lo == hi else "range")
            rows.append(r)
    return rows


# ---------------------------------------------------------------- OpenScore
TARGET_SETS = {"5108725"}   # Cherubini, String Quartet No. 1 (OpenScore) — obra objetivo (D-35)


def read_openscore(coll: str, prefix: str):
    base = RAW / coll
    data = base / "data"
    rows = []
    with open(data / "scores.tsv", encoding="utf-8") as fh:
        scores = list(csv.DictReader(fh, delimiter="\t"))
    with open(data / "sets.tsv", encoding="utf-8") as fh:
        sets = {s["id"]: s for s in csv.DictReader(fh, delimiter="\t")}
    with open(data / "composers.tsv", encoding="utf-8") as fh:
        comps = {c["id"]: c for c in csv.DictReader(fh, delimiter="\t")}
    per_set = Counter(s["set_id"] for s in scores)
    by_id = {}
    for f in (base / "scores").rglob("*.mxl"):
        m = re.search(r"(\d+)\.mxl$", f.name)
        if m:
            by_id[m.group(1)] = f
    n_unmatched = len(set(by_id) - {s["id"] for s in scores})
    if n_unmatched:
        print(f"  [{coll}] {n_unmatched} ficheros .mxl sin fila en scores.tsv (ignorados)")
    for s in scores:
        mxl = [by_id[s["id"]]] if s["id"] in by_id else []
        if not mxl:
            continue
        st = sets.get(s["set_id"], {})
        c = comps.get(st.get("composer_id", ""), {})
        comp_name = c.get("name") or s["path"].split("/")[0].replace("_", " ")
        cid = COMP.add(comp_name, c.get("born"), c.get("died"), source=coll)
        work_id = f"{prefix}-{s['set_id']}"
        mov = s["name"] if per_set[s["set_id"]] > 1 else "all"
        r = row(unit_id=f"{prefix}-{s['id']}", work_id=work_id, collection=coll,
                is_target=1 if s["set_id"] in TARGET_SETS else 0,
                composer=comp_name, composer_id=cid, title=st.get("name", s["name"]),
                movement=mov, format="musicxml_mxl", path=rel(mxl[0]), license="CC0-1.0",
                catalog_key=catalog_key(st.get("name", "") + " " + s["path"], cid))
        rows.append(r)
    return rows


# ---------------------------------------------------------------- S3
S3_WORKS = {"mo": ("Wolfgang Amadeus Mozart", "Symphony No. 41 in C major, K. 551", "K.551"),
            "be": ("Ludwig van Beethoven", "Symphony No. 9 in D minor, Op. 125", "Op.125"),
            "tc": ("Pyotr Ilyich Tchaikovsky", "Symphony No. 6 in B minor, Op. 74", "Op.74"),
            "dv": ("Antonín Dvořák", "Symphony No. 9 in E minor, Op. 95", "Op.95")}


def read_s3():
    rows = []
    base = RAW / "s3_symphonies" / "symbolic_symphony_set"
    for d in sorted(base.iterdir()):
        if not (d / "sheet.xml").exists():
            continue
        comp_name, title, cat = S3_WORKS[d.name[:2]]
        cid = COMP.add(comp_name, source="s3")
        work_id = f"s3-{d.name[:2]}"
        rows.append(row(unit_id=f"s3-{d.name}", work_id=work_id, collection="s3_symphonies",
                        composer=comp_name, composer_id=cid, title=title, movement=d.name[2:],
                        format="musicxml", path=rel(d / "sheet.xml"), license="MIT",
                        catalog_key=catalog_key(cat)))
    return rows


# ---------------------------------------------------------------- MuseData
MUSEDATA_COMPOSER = {"beethoven": "Ludwig van Beethoven", "mozart": "Wolfgang Amadeus Mozart",
                     "bach": "Johann Sebastian Bach", "handel": "Georg Friedrich Händel",
                     "vivaldi": "Antonio Vivaldi", "corelli": "Arcangelo Corelli",
                     "telemann": "Georg Philipp Telemann"}


def musedata_header(path: Path) -> dict:
    """Devuelve WK#, MV#, edición, título de obra y de movimiento de un fichero stage2/md2."""
    info = {}
    try:
        lines = path.read_text(errors="replace").splitlines()[:60]
    except Exception:
        return info
    for i, line in enumerate(lines):
        m = re.match(r"WK#:\s*([^\s]+(?:\s+\d+)?)\s+MV#:\s*(\S*)", line)
        if m:
            info["wk"], info["mv"] = m.group(1).strip(), m.group(2).strip()
            info["edition"] = lines[i + 1].strip() if i + 1 < len(lines) else ""
            info["work_title"] = lines[i + 2].strip() if i + 2 < len(lines) else ""
            info["mov_title"] = lines[i + 3].strip() if i + 3 < len(lines) else ""
            break
    return info


def read_musedata():
    rows = []
    for repo_dir in sorted(RAW.glob("musedata_*")):
        comp_key = repo_dir.name.split("_", 1)[1]
        comp_name = MUSEDATA_COMPOSER.get(comp_key)
        if not comp_name:
            continue
        cid = COMP.add(comp_name, source=repo_dir.name)
        coll = repo_dir.name
        lic = "CCARH MuseData (uso académico)"
        work_dirs = set()
        for d in repo_dir.rglob("*"):
            if d.is_dir() and d.name in ("stage2", "stage1", "editions") and ".git" not in d.parts:
                work_dirs.add(d.parent)
        for wd in sorted(work_dirs):
            relw = wd.relative_to(repo_dir)
            if any(p.endswith((".tst", ".old", ".bak")) for p in relw.parts):
                continue
            units = []   # (mov_label, path, fmt, header_file)
            md2 = sorted((wd / "editions" / "public" / "score").glob("*.md2")) \
                if (wd / "editions" / "public" / "score").is_dir() else []
            if md2:
                for f in md2:
                    units.append((f.stem, f, "musedata_md2", f))
            else:
                for stage in ("stage2", "stage2s", "stage1"):
                    sdir = wd / stage
                    if not sdir.is_dir():
                        continue
                    direct = sorted(p for p in sdir.iterdir() if p.is_file() and re.fullmatch(r"\d+", p.name))
                    if direct:            # obra de un solo movimiento: partes directamente en stage2/
                        units.append(("1", sdir, f"musedata_{stage.rstrip('s')}", direct[0]))
                    for mdir in sorted(sdir.iterdir()):
                        if not mdir.is_dir():
                            continue
                        parts = sorted(p for p in mdir.iterdir() if p.is_file() and re.fullmatch(r"\d+", p.name))
                        if parts:
                            units.append((mdir.name, mdir, f"musedata_{stage.rstrip('s')}", parts[0]))
                    if units:
                        break
            if not units:
                continue
            work_key = "-".join(relw.parts)
            work_id = f"{coll}-{work_key}"
            hdr = musedata_header(units[0][3]) if units[0][2] != "musedata_stage1" else {}
            title = hdr.get("work_title") or " / ".join(relw.parts)
            wk = hdr.get("wk", "")
            # clave de catálogo
            cat_text = f"{wd.name} {title} {wk}"
            if comp_key == "beethoven":
                mm = re.search(r"sym(\d)", wd.name)
                if mm:
                    cat_text = f"Op.{BEETHOVEN_SYM_OP[int(mm.group(1))]}"
                elif re.match(r"op\d+n\d+", wd.name):
                    mm = re.match(r"op(\d+)n(\d+)", wd.name)
                    cat_text = f"Op.{mm.group(1)} No.{mm.group(2)}"
                elif re.match(r"op\d+$", wd.name):
                    cat_text = f"Op.{wd.name[2:]}"
                elif wd.name == "piano2":
                    cat_text = "Op.19"
                elif wd.name == "violin":
                    cat_text = "Op.61"
            elif comp_key == "mozart":
                cat_text = wd.name if re.match(r"k\d+", wd.name) else cat_text
            elif comp_key == "bach" and re.fullmatch(r"\d{4}[a-z]?", wd.name):
                cat_text = f"BWV {int(wd.name[:4])}{wd.name[4:]}"
            elif comp_key == "handel" and wk:
                cat_text = f"HWV {wk.split(',')[0].split()[0]}"
            elif comp_key == "corelli":
                mm = re.match(r"op(\d+)n(\d+)", wd.name)
                cat_text = f"op.{int(mm.group(1))}/{int(mm.group(2))}" if mm else cat_text
            elif comp_key == "vivaldi":
                mm = re.search(r"rv(\d+)", wd.name)
                cat_text = f"RV {mm.group(1)}" if mm else cat_text
            cat = catalog_key(cat_text)
            is_target = 1 if (comp_key == "beethoven" and cat == "op67") else 0
            for mov, p, fmt, hfile in units:
                h = musedata_header(hfile) if fmt != "musedata_stage1" else {}
                mov_title = h.get("mov_title", "")
                rows.append(row(unit_id=f"{work_id}--{mov}", work_id=work_id, collection=coll,
                                composer=comp_name, composer_id=cid, title=title,
                                movement=f"{mov} {mov_title}".strip(), format=fmt, path=rel(p),
                                license=lic, catalog_key=cat, is_target=is_target))
    return rows


# ---------------------------------------------------------------- music21 bach (regresión)
def read_m21_bach():
    try:
        from music21 import corpus
    except ImportError:
        return []
    rows = []
    cid = COMP.add("Johann Sebastian Bach", source="m21_bach")
    for p in sorted(corpus.getCorePaths()):
        sp = str(p)
        if "/corpus/bach/" not in sp or sp.endswith(".rntxt"):
            continue
        stem = Path(sp).stem
        work_id = f"m21-bach-{stem}-{Path(sp).suffix[1:]}"
        rows.append(row(unit_id=work_id, work_id=work_id, collection="m21_bach",
                        composer="Johann Sebastian Bach", composer_id=cid, title=stem,
                        movement="", format=Path(sp).suffix[1:], path="m21corpus:" + sp.split("/corpus/", 1)[1],
                        license="music21 corpus (BSD/mixed)", catalog_key=catalog_key(stem),
                        in_analysis=0))
    return rows


# ----------------------------------------------------------------------------
# fechas manuales y periodo por vida del compositor
# ----------------------------------------------------------------------------
MANUAL_COLS = ["work_id", "collection", "composer", "title", "catalog_key", "n_units",
               "year_start", "year_end", "year_certainty", "source", "note"]


def _year(x):
    """'1742', '1742.0', '' -> int | None"""
    try:
        v = int(float(str(x).strip()))
    except (TypeError, ValueError):
        return None
    return v if 1400 <= v <= 2100 else None


def load_manual() -> dict:
    if not MANUAL_DATES.exists():
        return {}
    with open(MANUAL_DATES, encoding="utf-8") as fh:
        return {r["work_id"]: r for r in csv.DictReader(fh)}


def write_manual(rows: list[dict], existing: dict):
    """Una fila por work_id canónico sin fecha en la fuente (D-17); conserva lo ya rellenado."""
    canon = [r for r in rows if r["year_source"] in ("missing", "composer_lifespan")
             and not r["collection"].startswith(("openscore_lieder", "m21_bach"))
             and not r["collection"].startswith("dcml")]
    by_work = {}
    for r in canon:
        w = by_work.setdefault(r["work_id"], {"work_id": r["work_id"], "collection": r["collection"],
                                              "composer": r["composer"], "title": r["title"],
                                              "catalog_key": r["catalog_key"], "n_units": 0,
                                              "year_start": "", "year_end": "", "year_certainty": "",
                                              "source": "", "note": ""})
        w["n_units"] += 1
    for wid, old in existing.items():
        if wid in by_work:
            for k in ("year_start", "year_end", "year_certainty", "source", "note"):
                v = old.get(k, "")
                if k in ("year_start", "year_end"):
                    y = _year(v)
                    v = str(y) if y is not None else ""
                by_work[wid][k] = v
        else:
            by_work[wid] = old  # conservar filas que el usuario haya añadido
    with open(MANUAL_DATES, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANUAL_COLS)
        w.writeheader()
        for wid in sorted(by_work):
            w.writerow({k: by_work[wid].get(k, "") for k in MANUAL_COLS})
    return len(by_work)


def finalize_dates(rows: list[dict], manual: dict):
    for r in rows:
        if r["year_source"]:
            continue
        m = manual.get(r["work_id"])
        hi = _year(m.get("year_end")) if m else None
        if hi is not None:
            lo = _year(m.get("year_start")) or hi
            cert = (m.get("year_certainty") or "").strip().lower()
            if cert not in ("exact", "approx", "range"):
                cert = "exact" if lo == hi else "range"
            apply_year(r, lo, hi, "manual", cert)
            continue
        ls = COMP.lifespan(r["composer_id"])
        if ls:
            lo, hi = ls[0] + ACTIVE_START_AGE, ls[1] - 1
            r["year_start"], r["year_end"] = lo, hi
            r["year_source"] = "composer_lifespan"
            r["year_certainty"] = "range"
            r["period"] = period_of_range(lo, hi)
            r["period_source"] = "lifespan" if r["period"] != "unknown" else "none"
        else:
            r["year_source"] = "missing"
            r["year_certainty"] = "unknown"
            r["period"] = "unknown"
            r["period_source"] = "none"


# ----------------------------------------------------------------------------
# duplicados
# ----------------------------------------------------------------------------
def mark_duplicates(rows: list[dict]):
    def prio(r):
        c = r["collection"]
        for k, v in PRIORITY.items():
            if c.startswith(k):
                return v
        return 5

    groups = defaultdict(set)
    for r in rows:
        if r["catalog_key"] and r["in_analysis"]:
            groups[(r["composer_id"], r["catalog_key"])].add(r["work_id"])
    work_prio = {}
    for r in rows:
        work_prio.setdefault(r["work_id"], (prio(r), r["path"]))
    dup_of = {}
    for key, works in groups.items():
        if len(works) < 2:
            continue
        primary = min(works, key=lambda w: work_prio[w])
        for w in works:
            dup_of[w] = (f"{key[0]}:{key[1]}", w == primary)
    for r in rows:
        if r["work_id"] in dup_of:
            r["duplicate_group"], prim = dup_of[r["work_id"]]
            r["is_primary"] = 1 if prim else 0
        else:
            r["duplicate_group"], r["is_primary"] = "", 1
    return sum(1 for r in rows if not r["is_primary"])


# ----------------------------------------------------------------------------
# deduplicación por hash de secuencia (D-29): ediciones distintas de la misma obra
# ----------------------------------------------------------------------------
SEQ_N = 12                 # n-gramas IVR de 12 notas
SEQ_MIN_SHARED = 50        # tipos compartidos mínimos
SEQ_CONTAINMENT = 0.5      # compartidos / min(|A|, |B|)
SEQ_MAX_WORKS_PER_TYPE = 40   # n-gramas más frecuentes se ignoran (escalas, arpegios)


def sequence_dedup(rows: list[dict]):
    """Marca como no primarias las obras cuyo conjunto de 12-gramas IVR está contenido
    (> 50 %) en otra obra del mismo compositor. Requiere corpus/cache. Devuelve grupos."""
    try:
        import numpy as np
        import seqlib as sl
        import uniqueness as un
    except ImportError:
        sys.path.insert(0, str(ROOT / "scripts"))
        import numpy as np
        import seqlib as sl
        import uniqueness as un
    by_work = {}
    for r in rows:
        if r["is_primary"] == 1 and r["in_analysis"] == 1:
            by_work.setdefault(r["work_id"], r)
    sigs, nnotes = {}, {}
    for wid in by_work:
        d = sl.load_work(wid)
        if d is None:
            continue
        h = un.work_windows(d, 0.0)["IVR"].get(SEQ_N)
        if h is None or len(h) == 0:
            continue
        sigs[wid] = np.unique(h)
        nnotes[wid] = int(len(d["midi"]))
    # por compositor
    comp_of = {w: by_work[w]["composer_id"] for w in sigs}
    groups = []
    for cid in sorted(set(comp_of.values())):
        wids = [w for w in sigs if comp_of[w] == cid]
        if len(wids) < 2:
            continue
        H = np.concatenate([sigs[w] for w in wids])
        W = np.concatenate([np.full(len(sigs[w]), i, dtype=np.int32) for i, w in enumerate(wids)])
        order = np.argsort(H, kind="stable")
        H, W = H[order], W[order]
        starts = np.r_[0, np.nonzero(H[1:] != H[:-1])[0] + 1, len(H)]
        shared = Counter()
        for a, b in zip(starts[:-1], starts[1:]):
            k = b - a
            if 2 <= k <= SEQ_MAX_WORKS_PER_TYPE:
                ws = W[a:b]
                for i in range(k):
                    for j in range(i + 1, k):
                        shared[(ws[i], ws[j])] += 1
        parent = list(range(len(wids)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        pair_info = {}
        for (i, j), s in shared.items():
            ci, cj = by_work[wids[i]]["collection"], by_work[wids[j]]["collection"]
            if ci == cj and ci.startswith("dcml"):
                continue        # colecciones DCML curadas: una pieza por fichero, sin ediciones múltiples
            cont = s / min(len(sigs[wids[i]]), len(sigs[wids[j]]))
            if s >= SEQ_MIN_SHARED and cont >= SEQ_CONTAINMENT:
                parent[find(i)] = find(j)
                pair_info[(wids[i], wids[j])] = (s, cont)
        comps = defaultdict(list)
        for i, w in enumerate(wids):
            comps[find(i)].append(w)
        for members in comps.values():
            if len(members) > 1:
                groups.append((members, pair_info))

    def prio(w):
        c = by_work[w]["collection"]
        pr = next((v for k, v in PRIORITY.items() if c.startswith(k)), 5)
        return (pr, -nnotes.get(w, 0), by_work[w]["path"])

    seq_group = {}
    report = ["# Duplicados por hash de secuencia (D-29)", "",
              f"Criterio: n-gramas IVR de {SEQ_N} notas compartidos ≥ {SEQ_MIN_SHARED} y "
              f"compartidos / min(tipos) ≥ {SEQ_CONTAINMENT}; mismo compositor. Primaria = prioridad de "
              "colección (dcml > musedata > kern > s3 > openscore), luego más notas.", ""]
    for members, pair_info in groups:
        primary = min(members, key=prio)
        for w in members:
            seq_group[w] = (primary, w == primary)
        report.append(f"- **{primary}** ← " + ", ".join(
            f"`{w}` ({by_work[w]['collection']})" for w in sorted(members) if w != primary))
    for r in rows:
        g = seq_group.get(r["work_id"])
        if g:
            r["duplicate_group"] = (r["duplicate_group"] + ";" if r["duplicate_group"] else "") + f"seq:{g[0]}"
            r["is_primary"] = 1 if g[1] else 0
    (ROOT / "results" / "seq_duplicates.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return sum(1 for w, g in seq_group.items() if not g[1]), len(groups), len(sigs)


def main():
    rows = []
    for fn in (read_kern, read_dcml, lambda: read_openscore("openscore_quartets", "osq"),
               lambda: read_openscore("openscore_lieder", "osl"), read_s3, read_musedata,
               read_m21_bach):
        part = fn()
        print(f"{fn.__name__ if hasattr(fn,'__name__') and fn.__name__!='<lambda>' else 'openscore':>16}: {len(part):5d} unidades", flush=True)
        rows.extend(part)

    manual = load_manual()
    finalize_dates(rows, manual)
    n_manual_rows = write_manual(rows, manual)
    n_dup = mark_duplicates(rows)
    n_seq_dup, n_seq_groups, n_sigs = sequence_dedup(rows)
    print(f"dedup por secuencia: {n_sigs} obras con caché, {n_seq_groups} grupos, {n_seq_dup} obras marcadas no primarias")

    # unit_id únicos
    seen = Counter(r["unit_id"] for r in rows)
    assert all(v == 1 for v in seen.values()), [k for k, v in seen.items() if v > 1][:10]

    OUT_WORKS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_WORKS, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(OUT_COMPOSERS, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["composer_id", "name", "born", "died", "n_units", "sources"])
        n_by = Counter(r["composer_id"] for r in rows)
        for cid in sorted(COMP.info):
            i = COMP.info[cid]
            w.writerow([cid, i["name"], i["born"], i["died"], n_by[cid], ";".join(sorted(i["sources"]))])

    # informe de fechas
    works = {}
    for r in rows:
        works.setdefault(r["work_id"], r)
    OUT_MISSING.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_MISSING, "w", encoding="utf-8") as fh:
        fh.write("# Obras sin fecha de composición en la fuente\n\n")
        fh.write(f"Generado por `scripts/build_catalog.py`. Total unidades: {len(rows)}; obras (`work_id`): {len(works)}.\n\n")
        by_src = Counter(r["year_source"] for r in works.values())
        fh.write("## Origen de la fecha (por obra)\n\n| year_source | obras |\n|---|---|\n")
        for k, v in by_src.most_common():
            fh.write(f"| {k} | {v} |\n")
        by_per = Counter((r["period"], r["period_source"]) for r in works.values())
        fh.write("\n## Periodo asignado (por obra)\n\n| period | period_source | obras |\n|---|---|---|\n")
        for (p, s), v in sorted(by_per.items()):
            fh.write(f"| {p} | {s} | {v} |\n")
        fh.write(f"\n## Pendientes de fecha manual\n\n`corpus/manual_dates.csv` tiene {n_manual_rows} obras "
                 "canónicas sin fecha en su fuente (rellenar `year_start`, `year_end`, `year_certainty`, `source`; "
                 "las filas de Lieder no se listan: usan la regla del periodo activo, D-17).\n\n")
        fh.write("| colección | obras sin fecha | de ellas con periodo por vida del compositor | periodo unknown |\n|---|---|---|---|\n")
        cc = defaultdict(lambda: [0, 0, 0])
        for r in works.values():
            if r["year_source"] in ("missing", "composer_lifespan"):
                c = cc[r["collection"]]
                c[0] += 1
                if r["period"] != "unknown":
                    c[1] += 1
                else:
                    c[2] += 1
        for k in sorted(cc):
            fh.write(f"| {k} | {cc[k][0]} | {cc[k][1]} | {cc[k][2]} |\n")
        fh.write("\n## Obras en `unknown` (primeras 60)\n\n")
        for r in [w for w in works.values() if w["period"] == "unknown"][:60]:
            fh.write(f"- `{r['work_id']}` — {r['composer']} — {r['title'][:60]}\n")

    print(f"\nworks.csv: {len(rows)} unidades, {len(works)} obras, {n_dup} unidades no primarias "
          f"(duplicadas), manual_dates.csv: {n_manual_rows} obras")
    for col, n in sorted(Counter(r["collection"].split("/")[0] for r in rows).items()):
        print(f"  {col:24s} {n:5d}")


if __name__ == "__main__":
    sys.exit(main())
