"""Tests de la guardia del preregistro (D-41): datos sintéticos, sin leer el corpus."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import preregistration_guard as g  # noqa: E402


@pytest.mark.parametrize("x", [
    "musedata_beethoven-bhl-orch-sym5", "musedata_beethoven-bhl-orch-sym5--mvt1", "osq-5108725",
    "osq-11164006", "cherubini_l", "Luigi Cherubini", "corpus/raw/cherubini/hymne.musicxml",
])
def test_forbidden_ids_abort(x):
    with pytest.raises(g.PreregistrationViolation):
        g.check_ids([x], context="test")


@pytest.mark.parametrize("x", [
    "kern-chopin-mazurkas-op67", "kern-scriabin-op67", "musedata_beethoven-bhl-orch-sym3",
    "musedata_vivaldi-dawson-op3-rv230", "musedata_vivaldi-lecene-op3-rv230", "beethoven_l", "",
])
def test_allowed_ids_pass(x):
    g.check_ids([x], context="test")


def test_catalog_rows():
    ok = {"work_id": "dcml_abc-n05op18-5", "composer_id": "beethoven_l", "is_target": "0"}
    target = {"work_id": "whatever", "composer_id": "x", "is_target": "1"}
    cher = {"work_id": "osq-123", "composer": "Luigi Cherubini", "is_target": 0}
    g.check_catalog_rows([ok])
    for bad in (target, cher):
        with pytest.raises(g.PreregistrationViolation):
            g.check_catalog_rows([ok, bad])
    assert g.filter_catalog_rows([ok, target, cher]) == [ok]


def test_violation_exit_code():
    with pytest.raises(SystemExit) as e:
        g.check_ids(["osq-5108725"])
    assert e.value.code == 3
