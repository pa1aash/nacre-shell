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


# ----------------------------------------------------------------------------- run helpers and outputs
import csv  # noqa: E402
import json  # noqa: E402

from nacre.pourbaix import ph_cache, ph_k1_run as run  # noqa: E402
from nacre.pourbaix.paths import REPO  # noqa: E402

OUT = REPO / "results" / "preprint" / "pourbaix" / "ph_k1"


def _summ(onset, m, complete=True, undetermined=()):
    return {"expt": {"onset_V": onset, "budget_V": m, "budget_complete": True, "complete": complete,
                     "limiting": "r1", "onset_grid_min_V": onset} if onset is not None else None,
            "expt_undetermined": list(undetermined)}


def test_class_status_below_above_within_and_undetermined():
    assert run.class_status(_summ(3.9, 0.1), 4.2, 4.3)[0] == "below"
    assert run.class_status(_summ(4.5, 0.1), 4.2, 4.3)[0] == "above"
    assert run.class_status(_summ(4.25, 0.1), 4.2, 4.3)[0] == "within budget"
    assert run.class_status(_summ(None, 0.0), 4.2, 4.3)[0] == "undetermined"


def test_a_determined_subset_falsifies_but_never_passes():
    # E_ox is a minimum: a determined reaction below the class falsifies even if another is undetermined,
    # a determined reaction above it cannot pass while another reaction is undetermined
    assert run.class_status(_summ(3.9, 0.1, complete=False, undetermined=["r1s"]), 4.2, 4.3)[0] == "below"
    assert run.class_status(_summ(4.9, 0.1, complete=False, undetermined=["r1s"]), 4.2, 4.3)[0] == "undetermined"


def test_ph_cache_admits_only_by_c_entries():
    man = ph_cache.manifest()
    assert man["files"] and all(f["local_only"] for f in man["files"] if f["kind"] == "mp_entries")
    assert all(not f["location"].startswith("results/") for f in man["files"] if f["kind"] == "mp_entries")


def test_outputs_are_consistent_and_carry_the_provisional_margin_note():
    if not (OUT / "ph_k1.json").is_file():
        pytest.skip("outputs not generated")
    doc = json.loads((OUT / "ph_k1.json").read_text(encoding="utf-8"))
    assert doc["gate"]["passed"]
    rows = [r for r in (OUT / "ladder.csv").read_text(encoding="utf-8").splitlines()]
    assert rows[0].startswith("#") and "PROVISIONAL" in rows[0]
    body = list(csv.DictReader(r for r in rows if not r.startswith("#")))
    assert {r["class"] for r in body} == set(k1.CUTOFF_CLASSES)
    for r in body:
        assert r["status"] in ("below", "above", "within budget", "undetermined")
        if r["status"] == "above":
            assert r["undetermined_reactions"] == ""  # an upper bound above needs the whole registered set determined
        if r["route"] == "none":
            assert r["status"] == "undetermined"
    assert len((OUT / "ph_k1.md").read_text(encoding="utf-8").splitlines()) <= 60


def test_no_phase_passes_without_a_solvated_sink():
    if not (OUT / "ph_k1.json").is_file():
        pytest.skip("outputs not generated")
    doc = json.loads((OUT / "ph_k1.json").read_text(encoding="utf-8"))
    assert all(r["status"] != "pass" for r in doc["ladder"])
    assert all(r["sink"].startswith(("LiClO4", "none")) for ph in doc["phases"].values() for r in ph["reactions"].values())


def test_outputs_contain_no_api_key():
    key = None
    env = REPO / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("MP_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        pytest.skip("no key in .env")
    for p in list(OUT.rglob("*")) + [REPO / "src/nacre/pourbaix/ph_k1.py", REPO / "src/nacre/pourbaix/ph_cache.py"]:
        if p.is_file():
            assert key not in p.read_text(encoding="utf-8", errors="ignore"), p.name
