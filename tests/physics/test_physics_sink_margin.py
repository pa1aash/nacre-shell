"""m_sink, E_ub_sink, E_ub_prod_unsat and the edge rule (contract v7; unit_tests field of m_sink, items i to vii).

Every number is built from the constants module or the inputs of the case; no solubility or activity coefficient of
LiClO4 is bound anywhere in these tests.
"""
import math

import numpy as np
import pytest

from nacre.physics import sink, stability
from nacre.physics.bindings import UNDETERMINED
from nacre.physics.constants import FARADAY, GAS_CONSTANT, STANDARD_CONCENTRATION
from nacre.screen import thresholds as thr

T = 298.15
RT_F = GAS_CONSTANT * T / FARADAY


# ------------------------------------------------------------------ (i) zero
@pytest.mark.parametrize("a", [1e-3, 0.37, 1.0, 55.0])
def test_zero_at_saturation_exactly(a):
    assert stability.sink_margin(1.0, T, a, a) == 0.0


@pytest.mark.parametrize("nu", [0.0])
def test_zero_when_no_salt_is_consumed(nu):
    assert stability.sink_margin(nu, T, 3.0, 0.5) == 0.0


# ------------------------------------------------------------------ (ii) sign
def test_positive_below_saturation_negative_above():
    assert stability.sink_margin(1.0, T, 2.0, 1.0) > 0
    assert stability.sink_margin(1.0, T, 1.0, 2.0) < 0   # supersaturated: the one-sided margin never uses this region


def test_monotone_directions():
    a = np.geomspace(1e-3, 1.0, 40)
    assert np.all(np.diff(stability.sink_margin(1.0, T, 1.0, a)) < 0)           # more salt, smaller term
    assert np.all(np.diff(stability.sink_margin(1.0, T, np.geomspace(1.0, 50.0, 40), 0.5)) > 0)   # more soluble, larger
    assert np.all(np.diff(stability.sink_margin(np.linspace(0.5, 3.0, 40), T, 2.0, 1.0)) > 0)      # more salt consumed


def test_derivative_in_activity():
    a, h = 0.4, 1e-6
    d = (stability.sink_margin(1.0, T, 1.0, a + h) - stability.sink_margin(1.0, T, 1.0, a - h)) / (2 * h)
    assert d == pytest.approx(-2.0 * RT_F / a, rel=1e-8)


# ------------------------------------------------------------------ (iii) activity and concentration forms agree
def test_activity_and_concentration_forms_agree_on_a_grid():
    for c_sat in (3.0e3, 6.0e3, 1.2e4):                 # mol m^-3
        for c in (1.0e2, 1.0e3, 2.5e3):
            for g_sat in (0.3, 0.8, 1.4):
                for g in (0.25, 0.7, 1.1):
                    a_sat, a = sink.mean_activity(g_sat, c_sat), sink.mean_activity(g, c)
                    by_activity = stability.sink_margin(1.0, T, a_sat, a)
                    by_conc = 2.0 * RT_F * (math.log(c_sat / c) + math.log(g_sat / g))
                    assert by_activity == pytest.approx(by_conc, rel=1e-12, abs=1e-15)


def test_mean_activity_uses_the_standard_concentration_of_the_constants_module():
    assert sink.mean_activity(1.0, STANDARD_CONCENTRATION) == pytest.approx(1.0, rel=1e-15)


# ------------------------------------------------------------------ (iv) one decade
def test_one_decade_of_activity_moves_m_sink_by_2_ln10_nu_RT_over_F():
    for nu in (1.0, 2.0, 0.5):
        step = stability.sink_margin(nu, T, 1.0, 0.01) - stability.sink_margin(nu, T, 1.0, 0.1)
        assert step == pytest.approx(2.0 * math.log(10.0) * nu * GAS_CONSTANT * T / FARADAY, rel=1e-12)


def test_one_decade_is_about_a_tenth_of_a_volt_per_electron_at_298():
    one_decade = stability.sink_margin(1.0, 298.15, 10.0, 1.0)
    assert one_decade == pytest.approx(2.0 * math.log(10.0) * GAS_CONSTANT * 298.15 / FARADAY, rel=1e-13)
    assert 0.5 * 0.2 < one_decade < 0.2          # sanity bracket on the computed value (about 0.118 V)


# ------------------------------------------------------------------ (v) salt-activity form
def test_salt_activity_form_agrees():
    a_sat, a = 3.1, 0.62
    for nu in (1.0, 2.0):
        assert stability.sink_margin(nu, T, a_sat, a) == pytest.approx(nu * RT_F * math.log(a_sat ** 2 / a ** 2), rel=1e-12)


# ------------------------------------------------------------------ (vi) rigorous bound
def test_rigorous_bound_is_never_below_the_central_evaluation():
    c, c_sat, g, g_sat = 1.0e3, (5.0e3, 7.0e3), (0.4, 0.6), (0.7, 0.9)
    central = sink.rigorous_sink_margin(1.0, T, c, sum(c_sat) / 2, sum(g) / 2, sum(g_sat) / 2)
    rigorous = sink.rigorous_sink_margin(1.0, T, c, c_sat, g, g_sat)
    assert rigorous >= central > 0
    # the bound is the evaluation at the upper c_salt_sat and gamma_pm_sat and the lower gamma_pm
    expected = stability.sink_margin(1.0, T, sink.mean_activity(g_sat[1], c_sat[1]), sink.mean_activity(g[0], c))
    assert rigorous == pytest.approx(float(expected), rel=1e-15)


def test_rigorous_bound_scalars_equal_the_pure_function():
    got = sink.rigorous_sink_margin(1.0, T, 1.0e3, 6.0e3, 0.5, 0.8)
    want = stability.sink_margin(1.0, T, sink.mean_activity(0.8, 6.0e3), sink.mean_activity(0.5, 1.0e3))
    assert got == pytest.approx(float(want), rel=1e-15)


def test_rigorous_bound_rejects_a_supersaturated_electrolyte():
    with pytest.raises(ValueError, match="above saturation"):
        sink.rigorous_sink_margin(1.0, T, 9.0e3, 6.0e3, 0.8, 0.8)


# ------------------------------------------------------------------ (vii) a gap is unbound, never zero
@pytest.mark.parametrize("gap", [None, float("nan")])
def test_a_missing_input_is_unbound_not_zero(gap):
    with pytest.raises(sink.SinkInputUnbound, match="undetermined"):
        sink.sink_margin_checked(1.0, T, gap, 0.5)
    with pytest.raises(sink.SinkInputUnbound):
        sink.sink_margin_checked(1.0, T, 2.0, gap)
    assert sink.rigorous_sink_margin(1.0, T, 1.0e3, gap, 0.5, 0.8) == UNDETERMINED
    assert sink.rigorous_sink_margin(1.0, T, 1.0e3, (5.0e3, 6.0e3), (0.4, gap), 0.8) == UNDETERMINED
    assert sink.rigorous_sink_margin(1.0, T, gap, 6.0e3, 0.5, 0.8) == UNDETERMINED


def test_pure_function_rejects_non_physical_inputs_with_a_clear_error():
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            stability.sink_margin(1.0, T, bad, 0.5)
        with pytest.raises(ValueError):
            stability.sink_margin(1.0, T, 2.0, bad)
    with pytest.raises(ValueError):
        stability.sink_margin(-1.0, T, 2.0, 0.5)


# ------------------------------------------------------------------ E_ub_sink and E_ub_prod_unsat
def test_dilute_bound_is_e_ub_plus_m_sink_and_never_below_e_ub():
    g, dn = 3.9e5, 1.0
    e_ub = stability.onset_solid_salt_sink(g, dn)
    assert stability.onset_solid_salt_sink_dilute(g, dn, 1.0, T, 2.0, 2.0) == pytest.approx(e_ub, rel=1e-15)
    below = stability.onset_solid_salt_sink_dilute(g, dn, 1.0, T, 2.0, 0.5)
    assert below == pytest.approx(e_ub + stability.sink_margin(1.0, T, 2.0, 0.5), rel=1e-15) and below > e_ub


def test_product_below_saturation_lowers_the_onset():
    g, dn = 3.9e5, 1.0
    e_ub = stability.onset_solid_salt_sink(g, dn)
    assert stability.onset_solid_salt_sink_product_unsaturated(g, dn, 0.5, T, 1.0) == pytest.approx(e_ub, rel=1e-15)
    low = stability.onset_solid_salt_sink_product_unsaturated(g, dn, 0.5, T, 0.01)
    assert low < e_ub
    assert low == pytest.approx(e_ub + 0.5 * RT_F * math.log(0.01), rel=1e-12)
    with pytest.raises(ValueError):
        stability.onset_solid_salt_sink_product_unsaturated(g, dn, 0.5, T, 1.5)


def test_exchanging_no_lithium_sets_no_dilute_bound():
    with pytest.raises(ValueError):
        stability.onset_solid_salt_sink_dilute(3.9e5, 0.0, 1.0, T, 2.0, 0.5)


# ------------------------------------------------------------------ the 50 mV edge rule (tolerance read from the block)
def _tolerance_volts():
    tol = thr.load_thresholds()["rule"]["screen_ph"]["sink_v10"]["edge_rule"]["tolerance"]
    assert tol["unit"] == "mV"
    return tol["value"] / 1000.0


EDGES = (1.0, 2.0, 3.0)      # synthetic class edges


def test_edge_rule_within_tolerance_states_the_next_edge_that_clears_it():
    tol = _tolerance_volts()
    below = sink.edge_rule(2.0 - 0.16 * tol, EDGES, tol)         # just below an edge
    assert below["within_tolerance"] and below["near_edge"] == 2.0 and below["distance"] > 0
    assert below["robust_threshold"] == 3.0                      # the edge it sits under does not clear it by the tolerance
    above = sink.edge_rule(2.0 + 0.64 * tol, EDGES, tol)         # just above an edge
    assert above["within_tolerance"] and above["distance"] < 0 and above["robust_threshold"] == 3.0


def test_edge_rule_outside_tolerance_keeps_the_edge_above():
    tol = _tolerance_volts()
    r = sink.edge_rule(2.0 - 1.08 * tol, EDGES, tol)
    assert not r["within_tolerance"] and r["robust_threshold"] == 2.0


def test_edge_rule_no_edge_clears_and_gaps():
    tol = _tolerance_volts()
    assert sink.edge_rule(3.5, EDGES, tol)["robust_threshold"] is None
    assert sink.edge_rule(None, EDGES, tol)["status"] == UNDETERMINED
    assert sink.edge_rule(2.0, EDGES, float("nan"))["status"] == UNDETERMINED
