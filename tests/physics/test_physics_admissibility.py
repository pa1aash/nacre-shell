"""Admissibility of the template-liquid energy and the analog route (contract v4, decision D27).

gamma_sl = gamma_sl0 + Delta_gamma_ads >= 0 is a condition on the state the model describes.
Pi_ads = -Delta_gamma_ads is the lowering by adsorption; along the Ca2+ axis it is largest at
the zero-excess concentration c_0 = c_max (1 - 1/E_enr), where it equals Pi_ads_max, which
depends on Gamma_s and Delta_G_seq only. SF4: the admissible set is an upper set in
Delta_G_seq. The analog route maps a solution constant onto Delta_G_site with the site-volume
standard state and charges both protons of a catecholate (Delta_G_seq_cycle_2H).

W3 registers no saturating form (thresholds Section 1, "Why not a saturating form"), so the
small-coverage test is the reduction of the registered term itself: Pi_ads -> R T (Gamma_s x -
delta_s c_bulk) for small occupancy and Pi_ads -> 0 as c_bulk -> 0.
"""
import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from nacre.physics import sequestration as seq
from nacre.physics import template
from nacre.physics.constants import GAS_CONSTANT, STANDARD_CONCENTRATION

T = 298.15
RT = GAS_CONSTANT * T
dg_bind = st.floats(-60e3, -1.0)
dg_any = st.floats(-60e3, 60e3)
gamma_s = st.floats(1e-8, 1e-5)
delta_s = st.floats(1e-10, 1e-8)
c_bulk = st.floats(1e-4, 1e2)
gamma_sl0 = st.floats(1e-4, 0.1)


def c_zero_excess(dg, gs, ds):
    return (gs / ds) * (1.0 - math.exp(dg / RT))


# ------------------------------------------------------------------ Pi_ads and its maximum
@given(dg_any, c_bulk, gamma_s, delta_s)
def test_lowering_is_minus_the_adsorption_change(dg, cb, gs, ds):
    assert template.adsorption_lowering(dg, T, cb, gs, ds) == \
        -seq.adsorption_interfacial_energy_change(dg, T, cb, gs, ds)


def test_lowering_vanishes_as_calcium_vanishes():
    p = [template.adsorption_lowering(-20e3, T, cb, 3e-6, 1e-9) for cb in (1e-9, 1e-12, 1e-15)]
    assert p[1] / p[0] == pytest.approx(1e-3, rel=1e-3) and p[2] / p[1] == pytest.approx(1e-3, rel=1e-6)
    assert 0 < p[2] < 1e-14


def test_small_occupancy_reduces_to_the_linear_gibbs_term():
    dg, gs, ds, cb = -5e3, 3e-6, 1e-9, 1e-6
    x = seq.binding_odds(dg, T, cb, gs, ds)
    assert x < 1e-6
    linear = RT * (gs * x - ds * cb)
    assert template.adsorption_lowering(dg, T, cb, gs, ds) == pytest.approx(linear, rel=1e-5)


@given(dg_bind, gamma_s, delta_s)
def test_maximum_is_reached_at_the_zero_excess_concentration(dg, gs, ds):
    c0 = c_zero_excess(dg, gs, ds)
    assert seq.calcium_surface_excess(dg, T, c0, gs, ds) == pytest.approx(0.0, abs=1e-9 * gs)
    assert template.adsorption_lowering(dg, T, c0, gs, ds) == \
        pytest.approx(template.maximum_adsorption_lowering(gs, dg, T), rel=1e-8)


@given(dg_bind, gamma_s, delta_s, c_bulk)
def test_no_dose_lowers_more_than_the_maximum(dg, gs, ds, cb):
    pmax = template.maximum_adsorption_lowering(gs, dg, T)
    assert template.adsorption_lowering(dg, T, cb, gs, ds) <= pmax * (1 + 1e-12) + 1e-18


@given(dg_bind, gamma_s)
def test_maximum_is_positive_and_below_a_full_layer_of_binding(dg, gs):
    pmax = template.maximum_adsorption_lowering(gs, dg, T)
    assert 0.0 < pmax < -gs * dg


def test_maximum_equals_its_enrichment_form_and_its_limits():
    gs = 3e-6
    for dg in (-1e-3, -1.0, -1e3, -3e4):
        e = math.exp(-dg / RT)
        assert template.maximum_adsorption_lowering(gs, dg, T) == \
            pytest.approx(RT * gs * (math.log(e) - 1.0 + 1.0 / e), rel=1e-9)
    assert template.maximum_adsorption_lowering(gs, -1e-9, T) < 1e-20
    assert template.maximum_adsorption_lowering(gs, -1e7, T) > 1.0


def test_maximum_is_monotone():
    a = template.maximum_adsorption_lowering(3e-6, np.array([-3e4, -2e4, -1e4]), T)
    assert np.all(np.diff(a) < 0)                       # decreasing in Delta_G_seq
    b = template.maximum_adsorption_lowering(np.array([1e-6, 2e-6, 4e-6]), -2e4, T)
    assert np.all(np.diff(b) > 0)                       # increasing in Gamma_s


@pytest.mark.parametrize("dg", [0.0, 1.0, 5e3])
def test_maximum_is_defined_only_for_a_binding_template(dg):
    with pytest.raises(ValueError):
        template.maximum_adsorption_lowering(3e-6, dg, T)


# ------------------------------------------------------------------ floor and validity ratio
@given(gamma_sl0, dg_bind, gamma_s, delta_s, c_bulk)
def test_floor_is_below_the_energy_at_every_dose(sl0, dg, gs, ds, cb):
    floor = template.template_liquid_energy_floor(sl0, gs, dg, T)
    sl = template.template_liquid_energy_in_situ(sl0, dg, T, cb, gs, ds)
    assert floor <= sl + 1e-12 * max(1.0, abs(sl))


@given(gamma_sl0, dg_any, gamma_s, delta_s, c_bulk)
def test_validity_ratio_identity_and_admissibility(sl0, dg, gs, ds, cb):
    r = template.adsorption_validity_ratio(sl0, dg, T, cb, gs, ds)
    sl = template.template_liquid_energy_in_situ(sl0, dg, T, cb, gs, ds)
    assert sl == pytest.approx(sl0 * (1.0 - r), rel=1e-9, abs=1e-15)
    if abs(sl) > 1e-12 * sl0:
        assert (sl >= 0) == (r <= 1.0)


def test_validity_ratio_vanishes_as_calcium_vanishes():
    assert abs(template.adsorption_validity_ratio(0.02, -2e4, T, 1e-12, 3e-6, 1e-9)) < 1e-6


def test_validity_ratio_needs_a_positive_reference_energy():
    with pytest.raises(ValueError):
        template.adsorption_validity_ratio(0.0, -2e4, T, 1.0, 3e-6, 1e-9)


# ------------------------------------------------------------------ SF4 and gamma_sl
def test_sf4_witness():
    t = 1.0 / GAS_CONSTANT                              # R T = 1, as in the contract witness
    weak = template.template_liquid_energy_in_situ(1.0, 0.0, t, 1.0, 1.0, 1.0)
    strong = template.template_liquid_energy_in_situ(1.0, -3.0, t, 1.0, 1.0, 1.0)
    assert weak >= 0 > strong


@given(gamma_sl0, gamma_s, delta_s, c_bulk, dg_any, st.floats(0.0, 3e4))
def test_sf4_admissible_set_is_an_upper_set_in_the_binding_free_energy(sl0, gs, ds, cb, dg, up):
    lo = template.template_liquid_energy_in_situ(sl0, dg, T, cb, gs, ds)
    hi = template.template_liquid_energy_in_situ(sl0, dg + up, T, cb, gs, ds)
    assert hi >= lo - 1e-15
    if lo >= 0:
        assert hi >= 0


def test_strong_enough_binding_overshoots_every_reference_energy():
    for sl0 in (1e-3, 0.05, 1.0):
        assert template.template_liquid_energy_in_situ(sl0, -1e6, T, 1.0, 3e-6, 1e-9) < 0


def test_energy_is_bounded_above_by_the_depletion_term_and_decreasing_in_sites():
    sl0, ds, cb = 0.02, 1e-9, 1.0
    for dg in (-3e4, 0.0, 3e4):
        assert template.template_liquid_energy_in_situ(sl0, dg, T, cb, 3e-6, ds) <= sl0 + RT * ds * cb + 1e-15
    s = template.template_liquid_energy_in_situ(sl0, -2e4, T, cb, np.array([1e-6, 2e-6, 4e-6]), ds)
    assert np.all(np.diff(s) < 0)


def test_calcium_free_limit_reduces_admissibility_to_the_truncation():
    assert template.template_liquid_energy_in_situ(0.02, -4e4, T, 1e-14, 3e-6, 1e-9) == pytest.approx(0.02, rel=1e-6)


# ------------------------------------------------------------------ analog route
@given(st.floats(-6e4, 6e4), st.floats(5, 14), st.floats(0, 4), st.floats(7, 14))
def test_two_proton_cycle_bounds(site, pka, gap, ph):
    pka2 = pka + gap
    two = seq.sequestration_free_energy_two_proton(site, pka, pka2, ph, T)
    assert two >= seq.sequestration_free_energy(site, pka2, ph, T) - 1e-9
    one = seq.sequestration_free_energy(site, pka, ph, T)
    excess = RT * math.log((1 + 10 ** (pka2 - ph) + 10 ** (pka + pka2 - 2 * ph)) / (1 + 10 ** (pka - ph)))
    assert two >= one
    if gap > 0 and excess > 1e-12 * max(1.0, abs(two)):         # strict wherever the excess is representable
        assert two > one
    assert two - seq.sequestration_free_energy(site, pka, ph, T) == pytest.approx(excess, rel=1e-9, abs=1e-9)


def test_two_proton_cycle_limits():
    assert seq.sequestration_free_energy_two_proton(-1e4, 9.3, 12.0, 60.0, T) == pytest.approx(-1e4, abs=1e-6)
    assert seq.sequestration_free_energy_two_proton(-1e4, -200.0, 12.0, 11.0, T) == \
        pytest.approx(seq.sequestration_free_energy(-1e4, 12.0, 11.0, T), rel=1e-12)


def test_two_proton_cycle_is_monotone():
    a = seq.sequestration_free_energy_two_proton(-1e4, 9.3, 12.0, np.array([10.0, 11.0, 12.0, 13.0]), T)
    assert np.all(np.diff(a) < 0)
    b = seq.sequestration_free_energy_two_proton(-1e4, 9.3, np.array([11.0, 12.0, 13.0]), 11.0, T)
    assert np.all(np.diff(b) > 0)


@given(st.floats(1e-2, 1e8), gamma_s, delta_s)
def test_site_free_energy_from_a_solution_constant(k, gs, ds):
    v_site_n_a = ds / gs                                # N_A V_site
    expected = -RT * math.log(k) + RT * math.log(STANDARD_CONCENTRATION * v_site_n_a)
    assert seq.site_free_energy_from_solution_constant(k, gs, ds, T) == pytest.approx(expected, rel=1e-12, abs=1e-9)


@given(st.floats(1e-2, 1e8), gamma_s, delta_s, c_bulk, st.floats(8, 10), st.floats(10.5, 13.5), st.floats(10, 13))
def test_analog_odds_equal_the_contract_odds_on_the_analog_route(k, gs, ds, cb, pka, pka2, ph):
    site = seq.site_free_energy_from_solution_constant(k, gs, ds, T)
    dg = seq.sequestration_free_energy_two_proton(site, pka, pka2, ph, T)
    assert seq.binding_odds(dg, T, cb, gs, ds) == \
        pytest.approx(seq.binding_odds_from_solution_constant(k, cb, pka, pka2, ph), rel=1e-9)


def test_analog_odds_at_high_ph_are_the_bare_solution_odds():
    assert seq.binding_odds_from_solution_constant(1e3, 2.0, 9.3, 12.0, 80.0) == \
        pytest.approx(1e3 * 2.0 / STANDARD_CONCENTRATION, rel=1e-12)
