"""The gap-resolution table covers every unsourced input with one allowed treatment (P0-W4.3, R7)."""
from pathlib import Path

import pytest
import yaml

from nacre.screen import gaps

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / gaps.GAP_TABLE
PARAMS = ROOT / "lit" / "params.yaml"


@pytest.fixture(scope="module")
def table():
    return gaps.load(TABLE)


@pytest.fixture(scope="module")
def params():
    return yaml.safe_load(PARAMS.read_text(encoding="utf-8"))


def test_every_unsourced_key_has_a_treatment(table, params):
    assert gaps.check(table, params) == []


def test_table_is_registered_before_output(table):
    assert table["written_before_production_output"] is True
    assert table["inputs"]["params"]["tag"] == "p0-cp3"


def test_analog_keys_are_flagged_table_keys(table, params):
    for gap, key in gaps.analog_keys(table).items():
        assert key in params["params"], gap


def test_an_incomplete_table_is_reported(table, params):
    cut = dict(table, gaps={k: v for k, v in table["gaps"].items() if k != "patch_area"})
    assert any(p.startswith("patch_area") for p in gaps.check(cut, params))


def test_an_unknown_treatment_is_reported(table, params):
    bad = dict(table, gaps=dict(table["gaps"], patch_area={"treatment": "point value"}))
    assert any("not one of" in p for p in gaps.check(bad, params))


def test_ignorance_bounds_name_their_authority(table, params):
    bad = dict(table, gaps=dict(table["gaps"], gamma_op=dict(table["gaps"]["gamma_op"], bound_from="judgement")))
    assert any("ignorance_priors.md" in p for p in gaps.check(bad, params))
