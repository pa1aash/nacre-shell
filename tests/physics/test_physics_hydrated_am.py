"""E_ub_hydrated_am and Delta_G_gc_w (contract v8; I17a): the eight items of the unit_tests field of the contract.

Every physical constant comes from the constants module; the energies and activities below are inputs of the cases, not
values bound to any phase.
"""
import math

import numpy as np
import pytest

from nacre.physics import amorphous, stability
from nacre.physics.bindings import UNDETERMINED
from nacre.physics.constants import FARADAY, GAS_CONSTANT

T = 298.15
LABEL = "excluded (by the bound dG_g-to-c >= 0, against the crystalline reference plus water)"
REF = {"composition": {"Ca": 3.0, "P": 2.0, "OH": 0.0, "HPO4": 0.0}, "Delta_G_r_ss": 3.7e5, "Delta_n_Li": 6.0}
AM = {"composition": {"Ca": 3.0, "P": 2.0}, "n_hyd": 2.5, "a_w": 0.8, "T": T, "Delta_G_gc_w": 2.0e4}


def e_ub(g=REF["Delta_G_r_ss"], dn=REF["Delta_n_Li"]):
    return stability.onset_solid_salt_sink(g, dn)


def e_am(gc, n, aw, g=REF["Delta_G_r_ss"], dn=REF["Delta_n_Li"]):
    return stability.onset_solid_salt_sink_hydrated_amorphous(g, gc, n, aw, T, dn)


# ------------------------------------------------------------------ (i) no free energy gap and no water: E_ub exactly
@pytest.mark.parametrize("aw", [1e-3, 0.4, 1.0])
def test_i_zero_gap_and_no_water_equals_e_ub_exactly(aw):
    assert e_am(0.0, 0.0, aw) == e_ub()


# ------------------------------------------------------------------ (ii) unit activity, anhydrous-glass gap: E_ub_glass
@pytest.mark.parametrize("gc", [0.0, 1.5e3, 4.0e4])
def test_ii_unit_activity_and_glass_gap_equals_e_ub_glass_exactly(gc):
    got = e_am(gc, 3.0, 1.0)
    assert got == stability.onset_solid_salt_sink_glass(REF["Delta_G_r_ss"], gc, REF["Delta_n_Li"])


# ------------------------------------------------------------------ (iii) never above the reference row
def test_iii_no_larger_than_the_reference_on_a_grid():
    for aw in np.geomspace(1e-4, 1.0, 13):
        for gc in (0.0, 1.0, 5.0e2, 3.0e4, 2.0e5):
            for n in (0.0, 0.5, 2.0, 12.0):
                assert e_am(gc, n, aw) <= e_ub()
    # a negative energy would lift the value above the reference: rejected by the domain, not evaluated
    with pytest.raises(ValueError):
        e_am(-1.0, 2.0, 0.5)


def test_iii_rejects_water_activity_outside_the_registered_interval():
    for aw in (0.0, 1.0 + 1e-9, -0.1):
        with pytest.raises(ValueError):
            e_am(0.0, 2.0, aw)


# ------------------------------------------------------------------ (iv) strictly decreasing in Delta_G_gc_w; water
def test_iv_strictly_decreasing_in_delta_g_gc_w():
    v = e_am(np.linspace(0.0, 1.0e5, 40), 2.0, 0.7)
    assert np.all(np.diff(v) < 0)
    slope = e_am(1.0e4 + 1.0, 2.0, 0.7) - e_am(1.0e4, 2.0, 0.7)
    assert slope == pytest.approx(-1.0 / (REF["Delta_n_Li"] * FARADAY), rel=1e-6)


def test_iv_does_not_increase_in_n_hyd_below_unit_activity():
    v = e_am(5.0e3, np.linspace(0.0, 12.0, 40), 0.6)
    assert np.all(np.diff(v) <= 0)
    step = e_am(5.0e3, 3.0, 0.6) - e_am(5.0e3, 2.0, 0.6)
    assert step == pytest.approx(GAS_CONSTANT * T * math.log(0.6) / (REF["Delta_n_Li"] * FARADAY), rel=1e-9)
    flat = e_am(5.0e3, np.linspace(0.0, 12.0, 40), 1.0)
    assert np.all(flat == flat[0])


# ------------------------------------------------------------------ (v) a gap evaluates at the sign bound
@pytest.mark.parametrize("gap", [None, float("nan")])
def test_v_gap_in_delta_g_gc_w_returns_e_ub_of_the_reference_and_no_other_number(gap):
    am = dict(AM, Delta_G_gc_w=gap)       # n_hyd = 2.5 and a_w = 0.8 are set: the verdict evaluation ignores them
    assert amorphous.onset(REF, am) == e_ub()


def test_v_the_sign_bound_is_zero():
    assert amorphous.SIGN_BOUND == 0.0


def test_v_delta_g_gc_w_definition_and_gap():
    assert amorphous.delta_G_gc_w(-5.0e6, -5.03e6, 2.0, -1.0e4) == pytest.approx(-5.0e6 + 5.03e6 + 2.0e4, rel=1e-12)
    for args in ((None, 1.0, 2.0, 3.0), (1.0, float("nan"), 2.0, 3.0), (1.0, 2.0, None, 3.0), (1.0, 2.0, 2.0, None)):
        assert amorphous.delta_G_gc_w(*args) == UNDETERMINED


# ------------------------------------------------------------------ (vi) same-composition guard
@pytest.mark.parametrize("key,value", [("Ca", 2.9), ("P", 1.0), ("OH", 1.0), ("HPO4", 0.5)])
def test_vi_mismatched_reference_is_undetermined_and_not_evaluated(key, value):
    ref = dict(REF, composition=dict(REF["composition"], **{key: value}))
    assert amorphous.onset(ref, AM) == UNDETERMINED
    assert amorphous.k1_verdicts(ref, AM, 5.0, 0.1, 0.05, LABEL) == {"K1_falsify": UNDETERMINED,
                                                                       "K1_falsify_dilute": UNDETERMINED}


def test_vi_missing_composition_is_not_a_match():
    assert amorphous.onset(dict(REF, composition=None), AM) == UNDETERMINED
    assert amorphous.onset(REF, dict(AM, composition=None)) == UNDETERMINED
    assert amorphous.onset(REF, AM) != UNDETERMINED


# ------------------------------------------------------------------ (vii) verdicts equal the reference row at every class
M, M_SINK = 0.15, 0.07


def _classes(x):
    """Cutoffs well below, just below, just above and well above a crossover x."""
    return [x - 1.0, x - 0.02, x - 1e-9, x + 1e-9, x + 0.02, x + 1.0]


def _ref_words(E_c):
    x = e_ub()
    return {"K1_falsify": LABEL if x + M < E_c else UNDETERMINED,
            "K1_falsify_dilute": LABEL if x + M + M_SINK < E_c else UNDETERMINED}


@pytest.mark.parametrize("gc", [2.0e4, 0.0, None])
def test_vii_verdicts_equal_the_reference_rows_at_every_class(gc):
    am = dict(AM, Delta_G_gc_w=gc)
    for E_c in _classes(e_ub() + M) + _classes(e_ub() + M + M_SINK):
        got = amorphous.k1_verdicts(REF, am, E_c, M, M_SINK, LABEL)
        assert got == _ref_words(E_c)
        assert set(got.values()) <= {LABEL, UNDETERMINED}          # never a pass, never open


def test_vii_a_gap_in_the_margins_leaves_the_dependent_test_undetermined():
    E_c = e_ub() + 5.0
    assert amorphous.k1_verdicts(REF, AM, E_c, M, None, LABEL) == {"K1_falsify": LABEL, "K1_falsify_dilute": UNDETERMINED}
    both = amorphous.k1_verdicts(REF, AM, E_c, None, M_SINK, LABEL)
    assert set(both.values()) == {UNDETERMINED}


# ------------------------------------------------------------------ (viii) reference not excluded, or a gap
def test_viii_reference_not_excluded_is_undetermined_for_the_amorphous_row():
    low = e_ub() + M - 0.3
    assert set(amorphous.k1_verdicts(REF, AM, low, M, M_SINK, LABEL).values()) == {UNDETERMINED}


@pytest.mark.parametrize("field", ["Delta_G_r_ss", "Delta_n_Li"])
@pytest.mark.parametrize("gap", [None, float("nan")])
def test_viii_reference_gap_is_undetermined(field, gap):
    ref = dict(REF, **{field: gap})
    assert amorphous.onset(ref, AM) == UNDETERMINED
    assert set(amorphous.k1_verdicts(ref, AM, 1.0e3, M, M_SINK, LABEL).values()) == {UNDETERMINED}


def test_viii_missing_water_inputs_with_a_bound_gap_value_are_undetermined():
    for field in ("n_hyd", "a_w", "T"):
        assert amorphous.onset(REF, dict(AM, **{field: None})) == UNDETERMINED
