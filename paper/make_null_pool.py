"""Piscina nula de D-43 (b) y sus recuentos, solo desde metadatos del catálogo.

Lee únicamente corpus/works.csv, filtrado por scripts/preregistration_guard.py (sin caché ni
parquet; ninguna obra objetivo ni de Cherubini). Escribe:
  paper/D-43_null_pool.csv     lista exacta de work_id de A′ (argumento --null-pool del confirmatorio)
  paper/D-43_pool_counts.json  recuentos citados en paper/sections/protocol.tex y en D-43

Universo: obras con in_analysis = 1, is_primary = 1, period ∈ {1750–1800, 1800–1830}, compositor
distinto de Beethoven y de Cherubini. La instrumentación no está en works.csv: se asigna con las
reglas explícitas de `classify()` (colección + patrón del work_id), revisables por el usuario.

Uso:  /Users/cmorregof/Personal/Beethoven/.venv/bin/python paper/make_null_pool.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
sys.path.insert(0, str(ROOT / "scripts"))
from preregistration_guard import check_catalog_rows, filter_catalog_rows  # noqa: E402

WORKS = ROOT / "corpus" / "works.csv"
OUT_CSV = PAPER / "D-43_null_pool.csv"
OUT_JSON = PAPER / "D-43_pool_counts.json"
PERIODS = ("1750–1800", "1800–1830")
EXCLUDED_COMPOSERS = ("beethoven_l",)        # Cherubini lo elimina la guardia

# Reglas de clasificación (orden: la primera que casa decide). Patrones sobre work_id.
RULES = [
    ("orchestra", r"^kern-humdrum-haydn-symphonies-sym\d+$", "sinfonías de Haydn (KernScores)"),
    ("orchestra", r"^musedata_mozart-(bhl|nma)-sym-k\d+$", "sinfonías de Mozart (MuseData)"),
    ("orchestra_soloist", r"^musedata_mozart-(bhl|nma)-conc-k\d+$", "conciertos de Mozart (MuseData)"),
    ("voices_orchestra", r"^musedata_mozart-nma-opera-k\d+$", "ópera de Mozart (MuseData)"),
    ("string_orchestra", r"^musedata_mozart-bhl-divert-k13[678]$", "divertimentos K. 136–138"),
    ("chorus_orchestra", r"(mass|messe|missa|requiem|oratori|cantat|te-?deum|hymn)", "coro y orquesta (por palabra clave)"),
]
POOL_USE = {   # clase -> (fragmentos que la usan, regla de inclusión para el CSV)
    "orchestra": ("A1;A2", "orquesta sin solista ni voces: piscina de A2 (Eliza) y parte de la de A1 (Hymne)"),
    "orchestra_soloist": ("A1", "orquesta con solista: solo piscina ampliada de A1 (Hymne)"),
    "voices_orchestra": ("A1", "voces y orquesta: solo piscina ampliada de A1 (Hymne)"),
}
SOURCE_ORDER = ("kern-humdrum-haydn", "musedata_mozart-bhl", "musedata_mozart-nma")


def classify(work_id: str, title: str) -> str | None:
    key = f"{work_id} {title}".lower()
    for cls, pat, _ in RULES:
        target = key if cls == "chorus_orchestra" else work_id
        if re.search(pat, target):
            return cls
    return None


def sort_key(cls: str, w: str):
    src = next((i for i, s in enumerate(SOURCE_ORDER) if w.startswith(s)), len(SOURCE_ORDER))
    num = int(re.findall(r"\d+", w.rsplit("-", 1)[-1])[0])
    return (list(POOL_USE).index(cls), src, num)


def main():
    rows = list(csv.DictReader(open(WORKS, encoding="utf-8")))
    allowed = filter_catalog_rows(rows)
    check_catalog_rows(allowed, context="make_null_pool")
    works = {}
    for r in allowed:
        if r["in_analysis"] == "1" and r["is_primary"] == "1" and r["period"] in PERIODS \
                and r["composer_id"] not in EXCLUDED_COMPOSERS:
            works.setdefault(r["work_id"], r)
    classes = {w: classify(w, r["title"]) for w, r in works.items()}

    pool = sorted(((c, w) for w, c in classes.items() if c in POOL_USE), key=lambda x: sort_key(*x))
    out = []
    for cls, w in pool:
        r = works[w]
        frag, rule = POOL_USE[cls]
        out.append(dict(work_id=w, composer_id=r["composer_id"], year=r["composition_year"], period=r["period"],
                        instrumentation=cls, fragments=frag, rule=rule, title=r["title"]))
    check_catalog_rows([{"work_id": o["work_id"], "composer_id": o["composer_id"]} for o in out], "make_null_pool")
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(out[0]))
        wr.writeheader()
        wr.writerows(out)

    def n(cls):
        return sum(1 for c in classes.values() if c == cls)

    def ncomp(clss):
        return len({works[w]["composer_id"] for w, c in classes.items() if c in clss})

    counts = {
        "corpus_pool_universe_works": len(works),
        "corpus_pool_orch_works": n("orchestra"),
        "corpus_pool_orch_composers": ncomp({"orchestra"}),
        "corpus_pool_orch_mozart": sum(1 for w, c in classes.items() if c == "orchestra" and works[w]["composer_id"] == "mozart_wa"),
        "corpus_pool_orch_haydn": sum(1 for w, c in classes.items() if c == "orchestra" and works[w]["composer_id"] == "haydn_fj"),
        "corpus_pool_soloist_works": n("orchestra_soloist"),
        "corpus_pool_voices_works": n("voices_orchestra"),
        "corpus_pool_choral_works": n("chorus_orchestra"),
        "corpus_pool_strorch_works": n("string_orchestra"),
        "corpus_pool_orchext_works": len(out),
        "corpus_pool_orchext_composers": ncomp(set(POOL_USE)),
    }
    meta = {"source": "corpus/works.csv filtrado por scripts/preregistration_guard.py",
            "filter": {"in_analysis": 1, "is_primary": 1, "period": list(PERIODS), "excluded_composers": list(EXCLUDED_COMPOSERS) + ["cherubini (guardia)"]},
            "rules": [dict(cls=c, pattern=p, note=d) for c, p, d in RULES],
            "counts": counts}
    meta["by_class_composer"] = dict(Counter(f"{c}|{works[w]['composer_id']}" for w, c in classes.items() if c))
    OUT_JSON.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
