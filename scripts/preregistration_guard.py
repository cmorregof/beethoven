"""Guardia del preregistro D-41 para todo script nuevo (paper, web, confirmatorio, sensibilidad).

Ningún script nuevo puede leer, extraer, comparar ni calcular nada de la obra objetivo
(Beethoven op. 67, `musedata_beethoven-bhl-orch-sym5`) ni de ninguna obra de Cherubini.
Uso:

    from preregistration_guard import check_ids, check_catalog_rows
    check_ids([work_A, work_B], context="literal_sensitivity_n8")
    check_catalog_rows(rows, context="build_data")      # filas de corpus/works.csv

Si aparece algo prohibido, el script aborta con `PreregistrationViolation` (SystemExit, código 3).
No se usa la subcadena "op67": hay obras legítimas con ese número (Chopin, Scriabin).
"""
from __future__ import annotations

from typing import Iterable, Mapping

FORBIDDEN_WORK_IDS = frozenset({"musedata_beethoven-bhl-orch-sym5", "osq-5108725"})
FORBIDDEN_UNIT_PREFIXES = ("musedata_beethoven-bhl-orch-sym5", "osq-11164006")
FORBIDDEN_SUBSTRINGS = ("cherubini",)
TRUE_VALUES = {"1", "1.0", "true", "yes"}


class PreregistrationViolation(SystemExit):
    """Aborta el proceso: se ha intentado usar la obra objetivo o una obra de Cherubini."""

    def __init__(self, msg: str):
        super().__init__(3)
        self.msg = msg

    def __str__(self) -> str:
        return self.msg


def is_forbidden_id(x: object) -> bool:
    s = str(x).strip().lower()
    if not s:
        return False
    if s in FORBIDDEN_WORK_IDS or any(s.startswith(p) for p in FORBIDDEN_UNIT_PREFIXES):
        return True
    return any(f in s for f in FORBIDDEN_SUBSTRINGS)


def check_ids(ids: Iterable[object], context: str = "") -> None:
    """Aborta si algún identificador (work_id, unit_id, composer, composer_id, ruta) está prohibido."""
    for x in ids:
        if is_forbidden_id(x):
            raise PreregistrationViolation(
                f"ABORTADO (D-41): identificador prohibido {x!r} en {context or 'script nuevo'}")


def check_catalog_rows(rows: Iterable[Mapping[str, object]], context: str = "") -> None:
    """Aborta si alguna fila del catálogo es obra objetivo (is_target = 1) o de Cherubini."""
    for r in rows:
        if str(r.get("is_target", "0")).strip().lower() in TRUE_VALUES:
            raise PreregistrationViolation(
                f"ABORTADO (D-41): obra con is_target = 1 ({r.get('work_id')!r}) en {context or 'script nuevo'}")
        check_ids([r.get(k, "") for k in ("work_id", "unit_id", "composer", "composer_id", "path")], context)


def filter_catalog_rows(rows: Iterable[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """Devuelve las filas permitidas (sin objetivo ni Cherubini) sin abortar; para construir conjuntos
    de obras elegibles. Quien use las filas filtradas debe llamar después a check_catalog_rows."""
    out = []
    for r in rows:
        if str(r.get("is_target", "0")).strip().lower() in TRUE_VALUES:
            continue
        if any(is_forbidden_id(r.get(k, "")) for k in ("work_id", "unit_id", "composer", "composer_id", "path")):
            continue
        out.append(r)
    return out
