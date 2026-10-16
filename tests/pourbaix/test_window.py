"""R-cell Li-referenced window: toy limits, the unbounded-window guard, the contract and the
real CaCO3 / Al2O3 windows from the cache."""
import math
import socket

import pytest
from pourbaix_helpers import mock_config, offline  # noqa: F401

from nacre.pourbaix import cell, provenance
from nacre.pourbaix import window as w


def _toy_pd():
    """Li-A-B toy: AB (formation -1 eV) lithiates to Li2A + B (Li2A formation -3 eV)."""
    from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram
    from pymatgen.core import Composition

    entries = [PDEntry(Composition("Li"), 0.0), PDEntry(Composition("Ne"), 0.0),
               PDEntry(Composition("Ar"), 0.0), PDEntry(Composition("NeAr"), -1.0),
               PDEntry(Composition("Li2Ne"), -3.0)]
    return PhaseDiagram(entries), entries[3]


def test_toy_lithiation_limit():
    pd, ab = _toy_pd()
    red, ox, note = w.li_open_limits(pd, ab)
    # AB + 2 Li -> Li2A + B: Delta_G_r = -3 - (-1) = -2 eV, Delta_n_Li = -2 -> E = 1 V
    assert red.status == "finite"
    assert red.value == pytest.approx(1.0, abs=1e-9)
    assert red.delta_n_li == pytest.approx(-2.0)
    assert note["e_above_hull_eV_per_atom"] == pytest.approx(0.0)
    # Li-free phase: the raw Li-open oxidation limit is unbounded
    assert math.isinf(ox.value)


def test_toy_oxidation_onset():
    # invented energies (eV per formula unit) on real formulas, so pymatgen can balance them
    energies = {"CaO": -6.0, "LiCl": -4.0, "CaCl2": -7.0, "O2": -0.6, "Li": 0.0}

    def energy(f):
        if f not in energies:
            raise w.MissingPhase(f)
        return energies[f], {}

    sink = {"kind": "salt", "li_source": "LiCl", "products": {"Ca": ["CaCl2"]}}
    c = w.oxidation_candidate("CaO", "Ca", "toy", sink, "CaCl2", energy, ("O2",))
    # CaO + 2 LiCl -> CaCl2 + 1/2 O2 + 2 Li: Delta_G = -7 - 0.3 - (-6 - 8) = 6.7 eV over 2 Li
    assert c.status == "finite"
    assert c.delta_n_li == pytest.approx(2.0)
    assert c.onset_V == pytest.approx(3.35, abs=1e-9)


def test_missing_sink_phase_is_undetermined_not_dropped():
    def energy(f):
        raise w.MissingPhase(f)

    sink = {"kind": "salt", "li_source": "LiCl", "products": {"Ca": ["CaCl2"]}}
    c = w.oxidation_candidate("CaO", "Ca", "toy", sink, "CaCl2", energy, ("O2",))
    assert c.status == "undetermined" and "absent" in c.reason


def test_guard_fires_on_li_free_phase_without_oxidation_reaction():
    pd, ab = _toy_pd()
    red, li_open_ox, _ = w.li_open_limits(pd, ab)
    # the raw Li-open result must never be accepted as a window
    with pytest.raises(w.UnboundedWindowError):
        w.guard(w.Window("NeAr", red, li_open_ox, sink="none"))
    # with no oxidation reaction supplied the limit becomes explicitly undetermined
    win = w.build_window("NeAr", red, li_open_ox, candidates=[], active_sink="any")
    assert win.oxidation.status == "undetermined"
    assert win.oxidation.value is None
    assert "no oxidation reaction supplied" in win.oxidation.reason
    # and the screen does not treat it as a pass, however wide the requested range
    assert w.screen_pass(win, 2.0, 2.0) is False


def test_guard_rejects_undetermined_without_reason():
    red = w.Limit(1.0, "finite")
    with pytest.raises(w.UnboundedWindowError):
        w.guard(w.Window("X", red, w.Limit(None, "undetermined"), sink="s"))
    with pytest.raises(w.UnboundedWindowError):
        w.guard(w.Window("X", red, w.Limit(float("nan"), "finite"), sink="s"))


def test_screen_pass_requires_both_finite_limits_around_the_range():
    win = w.Window("X", w.Limit(1.0, "finite"), w.Limit(4.5, "finite"), sink="s")
    assert w.screen_pass(win, 3.0, 4.2)
    assert not w.screen_pass(win, 3.0, 4.6)
    assert not w.screen_pass(win, 0.5, 4.2)


def test_e_window_matches_the_contract_expression():
    text = provenance.git_object(*provenance.W3_CONTRACT)
    if text is None:
        pytest.skip("W3 contract object not in the local object store")
    import sympy
    import yaml
    from scipy import constants

    fns = {f["name"]: f for f in yaml.safe_load(text)["functions"]}
    expr = sympy.sympify(fns["E_window"]["expression"])
    F = constants.e * constants.N_A
    for dg_ev, dn in [(-2.1645, -4 / 3), (8.5489, 2.0), (0.3, 0.5)]:
        dg_j = dg_ev * F
        val = float(expr.subs({"Delta_G_r": dg_j, "Delta_n_Li": dn, "F_c": F}))
        assert w.e_window(dg_ev, dn) == pytest.approx(val, rel=1e-12)
        assert w.e_window_si(dg_j, dn) == pytest.approx(val, rel=1e-12)
    with pytest.raises(ValueError):
        w.e_window(1.0, 0)


# ------------------------------------------------------------------------ real data (cache)
@pytest.fixture(scope="module")
def cell_result():
    cfg, _ = mock_config()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(socket.socket, "connect", lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("network access attempted in an offline test")))
        return cfg["regimes"]["R-cell"], cell.build(cfg["regimes"]["R-cell"])


def test_every_phase_has_finite_or_undetermined_limits(cell_result):
    _, res = cell_result
    assert set(res["phases"]) == {"CaCO3", "Al2O3"}
    for phase, rec in res["phases"].items():
        win = rec["window"]
        for side in ("reduction", "oxidation"):
            lim = win[side]
            if lim["status"] == "finite":
                assert lim["value"] is not None and math.isfinite(lim["value"])
            else:
                assert lim["status"] == "undetermined" and lim["value"] is None and lim["reason"]
        assert win["sink"] == res["active_sink"]


def test_caco3_window_is_ordered_and_reactions_are_reported(cell_result):
    cfg, res = cell_result
    win = res["phases"]["CaCO3"]["window"]
    assert win["reduction"]["status"] == "finite"
    if win["oxidation"]["status"] == "finite":
        assert win["reduction"]["value"] < win["oxidation"]["value"]
        assert "O2" in win["oxidation"]["reaction"] and "CO2" in win["oxidation"]["reaction"]
    sinks_seen = {c["sink"] for c in res["candidates"] if c["phase"] == "CaCO3"}
    assert sinks_seen == set(cfg["sinks"])


def test_reduction_limit_agrees_with_direct_reaction_energy(cell_result):
    # CaCO3 + n Li -> products: recompute Delta_G_r from formation energies of the products
    from pymatgen.analysis.phase_diagram import PhaseDiagram
    from pymatgen.core import Composition

    _, res = cell_result
    lim = res["phases"]["CaCO3"]["window"]["reduction"]
    ents = cell.chemsys_entries("Li-Ca-C-O")
    pd = PhaseDiagram(ents)
    n = -lim["delta_n_li"]
    dec = pd.get_decomposition(Composition("CaCO3") + Composition({"Li": n}))
    natoms = (Composition("CaCO3") + Composition({"Li": n})).num_atoms
    g_products = sum(frac * natoms * pd.get_form_energy_per_atom(e) for e, frac in dec.items())
    calcite = [e for e in ents if (e.data or {}).get("material_id") == "mp-3953"][0]
    g_calcite = pd.get_form_energy_per_atom(calcite) * 5
    assert w.e_window(g_products - g_calcite, -n) == pytest.approx(lim["value"], abs=1e-6)


def test_sink_switch_needs_no_code_change(cell_result):
    cfg, res = cell_result
    other = dict(cfg, active_sink="sulfate")
    res2 = cell.build(other)
    assert res2["active_sink"] == "sulfate"
    for phase in ("CaCO3", "Al2O3"):
        assert res2["phases"][phase]["window"]["sink"] == "sulfate"
    assert res2["phases"]["Al2O3"]["window"]["oxidation"]["status"] == "finite"
    ox = res2["phases"]["Al2O3"]["window"]["oxidation"]["value"]
    cand = [c for c in res2["candidates"] if c["phase"] == "Al2O3" and c["sink"] == "sulfate"]
    assert ox == min(c["onset_V"] for c in cand if c["status"] == "finite")


def test_undefined_sink_is_refused(cell_result):
    cfg, _ = cell_result
    with pytest.raises(ValueError):
        cell.build(dict(cfg, active_sink="perchlorate"))
