"""Enrichment, occupancy and the adsorption change of gamma_sl (contract v2, C2).

Under contract v2 the Ca2+ chemical potential is uniform, so enrichment never raises the
driving force; the binding reaches the barrier through Delta_gamma_ads in gamma_sl. The
local-ideal Omega survives only as a named demonstration (wrong_variants).
"""
import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from nacre.physics.constants import GAS_CONSTANT
from nacre.physics.devtools.wrong_variants import driving_force_local_ideal, saturation_ratio_local_ideal
from nacre.physics.sequestration import (
    adsorption_interfacial_energy_change,
    binding_layer_saturation_concentration,
    binding_odds,
    calcium_surface_excess,
    enrichment_factor,
    local_calcium_concentration,
    sequestration_free_energy,
    site_occupancy,
)
from nacre.physics.constants import BOLTZMANN
from nacre.physics.supersaturation import saturation_ratio_bulk

pos = st.floats(min_value=1e-6, max_value=1e6)
temps = st.floats(min_value=1.0, max_value=2000.0)
reals = st.floats(min_value=-1e5, max_value=1e5)


@given(pos, pos, pos)
def test_local_concentration_never_exceeds_saturation_or_the_dilute_value(e, cb, cm):
    c = local_calcium_concentration(e, cb, cm)
    assert c <= cm * (1 + 1e-15)
    assert c <= e * cb * (1 + 1e-15)


@given(pos, pos, pos)
def test_local_concentration_is_harmonic_combination(e, cb, cm):
    assert 1 / local_calcium_concentration(e, cb, cm) == pytest.approx(1 / (e * cb) + 1 / cm, rel=1e-12)


def test_local_concentration_limits():
    assert local_calcium_concentration(0.0, 1.0, 1.0) == 0.0
    assert local_calcium_concentration(3.0, 2.0, 1e300) == pytest.approx(6.0, rel=1e-12)
    assert local_calcium_concentration(3.0, 1e300, 5.0) == pytest.approx(5.0, rel=1e-12)


@given(reals, temps)
def test_enrichment_is_boltzmann_factor(dg, t):
    x = -dg / (GAS_CONSTANT * t)
    if abs(x) < 700:
        assert enrichment_factor(dg, t) == pytest.approx(math.exp(x), rel=1e-12)


def test_no_transfer_free_energy_means_no_enrichment():
    assert enrichment_factor(0.0, 300.0) == 1.0


@given(reals, st.floats(min_value=-20, max_value=20), st.floats(min_value=-20, max_value=20), temps)
def test_protonation_correction_never_favours_binding(g, pka, ph, t):
    assert sequestration_free_energy(g, pka, ph, t) >= g


def test_protonation_correction_at_pka_is_rt_ln2():
    assert sequestration_free_energy(0.0, 7.0, 7.0, 300.0) == pytest.approx(GAS_CONSTANT * 300.0 * math.log(2), rel=1e-12)


@given(pos, pos, pos, pos)
def test_local_ideal_omega_in_the_dilute_limit_is_enrichment_times_bulk(e, a, b, k):
    # demonstration form only: it credits the binding to the driving force
    cb = 1.0
    cl = local_calcium_concentration(e, cb, 1e300)
    assert saturation_ratio_local_ideal(cl, cb, a, b, k) == pytest.approx(e * saturation_ratio_bulk(a, b, k), rel=1e-12)


def test_local_ideal_omega_equals_bulk_without_enrichment():
    assert saturation_ratio_local_ideal(2.0, 2.0, 0.1, 0.2, 1e-3) == pytest.approx(saturation_ratio_bulk(0.1, 0.2, 1e-3))


def test_local_ideal_driving_force_credits_minus_delta_g_seq_per_ion():
    # dilute limit: k_B T ln Omega_local_ideal - k_B T ln Omega_bulk = -Delta_G_seq / N_A
    t, dg = 300.0, -4000.0
    e = enrichment_factor(dg, t)
    excess = driving_force_local_ideal(e * 1e-3, 1e-3, 0.1, 0.2, 1e-3, t) - BOLTZMANN * t * math.log(20.0)
    assert excess == pytest.approx(-BOLTZMANN * t * dg / (GAS_CONSTANT * t), rel=1e-9)


# ---------------------------------------------------------------- contract v2: occupancy and adsorption
BIND = dict(T=300.0, c_bulk=2.0, Gamma_s=4e-6, delta_s=1e-9)


@given(st.floats(min_value=-4e4, max_value=4e4))
def test_occupancy_is_the_langmuir_fraction_of_the_layer(dg):
    x = binding_odds(dg, **BIND)
    th = site_occupancy(dg, **BIND)
    assert 0.0 <= th <= 1.0
    assert th == pytest.approx(x / (1 + x), rel=1e-12)
    e = enrichment_factor(dg, BIND["T"])
    c_max = binding_layer_saturation_concentration(BIND["Gamma_s"], BIND["delta_s"])
    assert th == pytest.approx(local_calcium_concentration(e, BIND["c_bulk"], c_max) / c_max, rel=1e-10)


def test_occupancy_limits_without_overflow():
    assert site_occupancy(-1e9, **BIND) == 1.0
    assert site_occupancy(+1e9, **BIND) == 0.0
    assert calcium_surface_excess(-1e9, **BIND) == pytest.approx(BIND["Gamma_s"] - BIND["delta_s"] * BIND["c_bulk"])


def test_adsorption_change_is_negative_for_binding_and_positive_for_depletion():
    assert adsorption_interfacial_energy_change(-2e4, **BIND) < 0      # binding lowers gamma_sl
    dep = adsorption_interfacial_energy_change(+1e9, **BIND)
    assert dep == pytest.approx(GAS_CONSTANT * BIND["T"] * BIND["delta_s"] * BIND["c_bulk"], rel=1e-12)


@given(st.floats(min_value=-3e4, max_value=3e4))
def test_adsorption_change_has_the_contract_derivatives(dg):
    # d Delta_gamma_ads / d Delta_G_seq = Gamma_s Theta  (each site contributes its occupancy)
    h = 1.0
    num = (adsorption_interfacial_energy_change(dg + h, **BIND) - adsorption_interfacial_energy_change(dg - h, **BIND)) / (2 * h)
    assert num == pytest.approx(BIND["Gamma_s"] * site_occupancy(dg, **BIND), rel=1e-5, abs=1e-18)


def test_gibbs_adsorption_equation_holds():
    # d gamma_sl / d ln c_bulk = -R T Gamma_Ca
    dg, c = -1e4, BIND["c_bulk"]
    kw = {k: v for k, v in BIND.items() if k != "c_bulk"}
    eps = 1e-6
    up = adsorption_interfacial_energy_change(dg, c_bulk=c * math.exp(eps), **kw)
    down = adsorption_interfacial_energy_change(dg, c_bulk=c * math.exp(-eps), **kw)
    want = -GAS_CONSTANT * BIND["T"] * calcium_surface_excess(dg, **BIND)
    assert (up - down) / (2 * eps) == pytest.approx(want, rel=1e-6)


def test_adsorption_change_is_exact_for_tiny_occupancy():
    # ln(1 + x) evaluated without cancellation: for x -> 0 it tends to R T delta_s c_bulk (1 - E)
    dg = 1e5
    x = binding_odds(dg, **BIND)
    want = -GAS_CONSTANT * BIND["T"] * (BIND["Gamma_s"] * x - BIND["delta_s"] * BIND["c_bulk"])
    assert adsorption_interfacial_energy_change(dg, **BIND) == pytest.approx(want, rel=1e-12)


def test_saturation_concentration_is_site_density_over_thickness():
    assert binding_layer_saturation_concentration(6.0, 3.0) == 2.0


@pytest.mark.parametrize("args", [(-1.0, 1.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 0.0)])
def test_unphysical_layer_inputs_are_rejected(args):
    with pytest.raises(ValueError):
        local_calcium_concentration(*args)
