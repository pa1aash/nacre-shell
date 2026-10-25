"""PH-W4.9: the break-even table is read from the frozen ladder and the thresholds copy, never typed."""
import math

import pytest

from nacre._util import repo_root
from nacre.physics import sink
from nacre.physics.bindings import DEFAULT_T
from nacre.physics.constants import FARADAY, GAS_CONSTANT
from nacre.screen import ph_breakeven, ph_prov

ROOT = repo_root()


@pytest.fixture(scope="module")
def table():
    ph_prov.check_frozen(ROOT)
    data, omitted = ph_breakeven.rows(ROOT)
    return data, omitted


def test_edges_come_from_the_thresholds_copy():
    assert ph_breakeven.cutoff_edges(ROOT) == {"C_mid": [4.2, 4.3], "C_hi": [4.4, 4.5]}


def test_every_row_is_the_formula_applied_to_its_own_inputs(table):
    data, _ = table
    assert data
    for r in data:
        head = r["E_c"] - r["E_ub"] - r["m_expt"]
        assert r["headroom_V"] == pytest.approx(head, abs=1e-6)
        if head < 0:
            assert r["r_star"] == sink.NOT_EXCLUDED_WITHOUT_CORRECTION
        else:
            assert r["r_star"] == pytest.approx(math.exp(head * FARADAY / (2 * GAS_CONSTANT * DEFAULT_T)), rel=1e-12)
            assert r["r_star"] >= 1.0


def test_only_classes_with_an_excluded_edge_are_listed(table):
    data, _ = table
    for key in {(r["phase"], r["framing"], r["stage"], r["class"]) for r in data}:
        rows = [r for r in data if (r["phase"], r["framing"], r["stage"], r["class"]) == key]
        assert any(r["headroom_V"] >= 0 for r in rows)


def test_known_rows_of_the_planning_table(table):
    data, _ = table
    by = {(r["phase"], r["E_c"]): r for r in data}
    assert by[("HAp", 4.2)]["headroom_V"] == pytest.approx(0.0082, abs=1e-6)
    assert by[("CaCO3", 4.2)]["r_star"] == pytest.approx(30.25, rel=1e-3)
    assert by[("brushite", 4.4)]["r_star"] == sink.NOT_EXCLUDED_WITHOUT_CORRECTION
