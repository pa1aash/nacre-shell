"""PH-K1: the carbonate gate, the generic reaction code and the budget recipe (offline)."""
import pytest
from pourbaix_helpers import offline  # noqa: F401

from nacre.pourbaix import ph_k1 as k1


@pytest.fixture(scope="module")
def ctx():
    return k1.Ctx()


def test_gate_carbonate_control_matches_the_frozen_value(offline, ctx):  # noqa: F811
    g = k1.gate(ctx)
    assert g["passed"]
    assert abs(g["difference_to_inventory_mV"]) <= 1.0
    assert abs(g["difference_to_full_precision_mV"]) < 1.0e-6


def test_gate_budget_reproduces_the_registered_window_margin(offline, ctx):  # noqa: F811
    g = k1.gate(ctx)
    assert g["budget_difference_V"] == pytest.approx(0.0, abs=1.0e-9)


def test_carbonate_reaction_is_the_registered_one(offline, ctx):  # noqa: F811
    c = k1.carbonate_control(ctx)["reaction"]
    assert c["CaCO3"] == pytest.approx(-1.0)
    assert c["LiClO4"] == pytest.approx(-2.0)
    assert c["Ca(ClO4)2"] == pytest.approx(1.0)
    assert c["CO2"] == pytest.approx(1.0)
    assert c["O2"] == pytest.approx(0.5)
    assert c["Li"] == pytest.approx(2.0)


def test_reaction_with_a_wrong_sign_is_refused():
    with pytest.raises(ValueError):
        k1.build_reaction("CaCO3", ["LiClO4"], ["Ca(ClO4)2", "CO2", "Li"])


def test_phosphate_reactions_balance_with_the_stated_stoichiometry():
    r = k1.build_reaction("HAp", ["LiClO4"], ["b-TCP", "Ca(ClO4)2", "H2O", "O2", "Li"])
    assert r["b-TCP"] == pytest.approx(1.5)
    assert r["Ca(ClO4)2"] == pytest.approx(0.5)
    assert r["H2O"] == pytest.approx(0.5)
    assert r["O2"] == pytest.approx(0.25)
    assert r["Li"] == pytest.approx(1.0)
    t = k1.build_reaction("Li3PO4", [], ["P2O5", "O2", "Li"])
    assert t["Li"] == pytest.approx(3.0) and t["O2"] == pytest.approx(0.75)


def test_every_registered_reaction_balances():
    for ph in k1.PHASES:
        for rid, _, extra, products in ph["reactions"]:
            r = k1.build_reaction(ph["id"], extra, products)
            assert r[ph["id"]] == pytest.approx(-1.0)
            assert r["Li"] > 0 and r["O2"] > 0, (ph["id"], rid)


def test_a_species_without_data_makes_the_reaction_undetermined(offline, ctx):  # noqa: F811
    r = k1.build_reaction("Ca(PO3)2", ["LiClO4"], ["Ca(ClO4)2", "P2O5", "O2", "Li"])
    res = k1.evaluate(r, k1.ExptBook(ctx))
    assert res["status"] == "undetermined" and res["onset_V"] is None
    assert res["missing"][0]["species"] == "Ca(PO3)2"


def test_row_uncertainty_follows_the_printed_value_or_the_nbs_convention():
    v, u, _ = k1.row_kj("TR-009")  # USGS, +-5.0 as printed
    assert v == pytest.approx(-6337.1) and u == pytest.approx(5.0)
    v, u, basis = k1.row_kj("TR-037")  # NBS brushite, none printed: 20 x 0.01 kcal
    assert v == pytest.approx(-515.0 * 4.184) and u == pytest.approx(20 * 0.1 * 4.184) and "NBS" in basis
