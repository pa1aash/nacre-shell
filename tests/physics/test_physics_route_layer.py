"""Contract v6 (route layer, K1 bracket, framings): limit cases, sign tests and the contract's own small cases.

The expressions are checked against theory/contract.yaml by nacre.physics.devtools.check_contract_equivalence
(record: configs/preprint/contract_check.json); these tests reproduce the contract's limits numerically and pin the
directions the decision tables of theory/claims_redirect.md Section 9 rely on.
"""
import math

import numpy as np
import pytest

from nacre.physics import coacervate, gelation, hydrolysis, stability
from nacre.physics import supersaturation as sat
from nacre.physics.constants import FARADAY, GAS_CONSTANT
from nacre.physics.devtools import equivalence as eq
from nacre.physics.devtools import wrong_variants


# ------------------------------------------------------------------ K1 bracket
def test_bracket_onsets_are_e_window_forms():
    g, dn = 4.0e5, 1.0
    assert stability.onset_solid_salt_sink(g, dn) == pytest.approx(stability.reaction_limit_potential(g, dn), rel=1e-15)
    assert stability.onset_aqueous_sink(g, dn) == pytest.approx(g / FARADAY, rel=1e-15)


def test_cell_solvent_onset_reduces_to_e_lb_and_bounds_it_under_the_premise():
    g, dn = 3.8e5, 1.0
    assert stability.onset_cell_solvent(g, 0.0, dn) == pytest.approx(stability.onset_aqueous_sink(g, dn), rel=1e-15)
    for tr in (1.0, 1.0e3, 5.0e4):
        assert stability.onset_cell_solvent(g, tr, dn) > stability.onset_aqueous_sink(g, dn)
    assert stability.onset_cell_solvent(g, -1.0e3, dn) < stability.onset_aqueous_sink(g, dn)


def test_born_transfer_vanishes_for_li_and_holds_for_dense_cations():
    r_li = 0.76e-10
    assert stability.relative_transfer_born(2.0e-5, 1.0, r_li, r_li) == pytest.approx(0.0, abs=1e-20)
    assert stability.relative_transfer_born(0.0, 3.0, 0.5e-10, r_li) == 0.0
    # r_M < z_M r_Li: Ca2+ (1.00 A) and Al3+ (0.535 A) satisfy the premise with B_born >= 0
    assert stability.relative_transfer_born(1.0e-5, 2.0, 1.00e-10, r_li) > 0
    assert stability.relative_transfer_born(1.0e-5, 3.0, 0.535e-10, r_li) > 0
    assert stability.relative_transfer_born(1.0e-5, 1.0, 1.0e-10, r_li) < 0


def test_bracket_rejects_a_reaction_without_li():
    for f in (stability.onset_solid_salt_sink, stability.onset_aqueous_sink):
        with pytest.raises(ValueError):
            f(1.0e5, 0.0)


# ------------------------------------------------------------------ framings of the route products (C4)
def test_glass_onsets_reduce_to_crystal_and_lie_below_it():
    g, dn = 4.2e5, 2.0
    assert stability.onset_glass(g, 0.0, dn) == pytest.approx(stability.reaction_limit_potential(g, dn), rel=1e-15)
    assert stability.onset_aqueous_sink_glass(g, 0.0, dn) == pytest.approx(stability.onset_aqueous_sink(g, dn))
    assert stability.onset_solid_salt_sink_glass(g, 0.0, dn) == pytest.approx(stability.onset_solid_salt_sink(g, dn))
    gc = np.array([1.0e3, 1.0e4, 3.0e4])
    e = stability.onset_glass(g, gc, dn)
    assert np.all(e < stability.reaction_limit_potential(g, dn)) and np.all(np.diff(e) < 0)
    with pytest.raises(ValueError):
        stability.onset_glass(g, -1.0, dn)


def test_omega_glass_reduces_to_omega_nu_and_is_smaller():
    args = (1e-3, 2e-4, 1.0, 1.0, 2.0, 0.0, 1.0, 0.0, 1e-12)
    om = sat.saturation_ratio_mineral(*args)
    assert sat.saturation_ratio_glass(*args, 0.0, 298.15) == pytest.approx(om, rel=1e-14)
    dg = 5.0e3
    assert sat.saturation_ratio_glass(*args, dg, 298.15) == pytest.approx(om * math.exp(-dg / (GAS_CONSTANT * 298.15)),
                                                                          rel=1e-13)
    assert sat.saturation_ratio_glass(*args, dg, 298.15) < om


# ------------------------------------------------------------------ hydrolysis (C1)
def test_condensed_fraction_limits():
    assert hydrolysis.condensed_fraction(0.0, 100.0) == 1.0
    assert hydrolysis.condensed_fraction(100.0, 100.0) == pytest.approx(0.5, rel=1e-15)
    assert hydrolysis.condensed_fraction(1.0e6, 1.0) == 0.0


def test_condensed_fraction_first_order_identity_and_monotonicity():
    tau, k, t = 3.0, 2.0e-5, 4.0e3
    th = hydrolysis.half_life(tau, k)
    assert hydrolysis.condensed_fraction(t, th) == pytest.approx(math.exp(-tau * k * t), rel=1e-14)
    assert hydrolysis.effective_rate_constant(1.0, k) == k
    ts = np.array([1.0, 10.0, 100.0])
    assert np.all(np.diff(hydrolysis.condensed_fraction(ts, 50.0)) < 0)
    assert np.all(np.diff(hydrolysis.condensed_fraction(10.0, ts)) > 0)
    assert hydrolysis.half_life(2.0, k) < hydrolysis.half_life(1.0, k)


def test_flip_time_returns_f_min():
    th = 1234.0
    assert hydrolysis.wet_time_flip(th, 1.0) == 0.0
    assert hydrolysis.wet_time_flip(th, 0.5) == pytest.approx(th, rel=1e-15)
    for f_min in (0.9, 0.5, 0.1):
        assert hydrolysis.condensed_fraction(hydrolysis.wet_time_flip(th, f_min), th) == pytest.approx(f_min, rel=1e-13)
    with pytest.raises(ValueError):
        hydrolysis.wet_time_flip(th, 1.5)


# ------------------------------------------------------------------ R1 (C2)
def test_oxide_pinned_aluminium_activity():
    assert gelation.aluminium_activity_oxide_equilibrium(10.0 ** 8.0, 0.0, 1.0) == pytest.approx(1e8, rel=1e-14)
    a6 = gelation.aluminium_activity_oxide_equilibrium(10.0 ** 8.0, 6.0, 1.0)
    assert a6 == pytest.approx(10.0 ** (8.0 - 18.0), rel=1e-12)
    assert gelation.aluminium_activity_oxide_equilibrium(10.0 ** 8.0, 7.0, 1.0) < a6
    assert gelation.aluminium_activity_oxide_equilibrium(10.0 ** 8.0, 6.0, 0.5) == pytest.approx(a6 * 8.0, rel=1e-12)


def test_free_ligand_complexation_limits():
    assert gelation.free_chain_unit_activity(1e-3, 0.0, 1e-9) == 1e-3
    assert gelation.free_chain_unit_activity(1e-3, 1e30, 1.0) < 1e-30
    assert gelation.free_chain_unit_activity(1e-3, 1e5, 1e-5) == pytest.approx(0.5e-3, rel=1e-14)


def test_alpp_saturation_contract_case_and_flip_value():
    a_al, a_pp = 1e-10, 1e-2
    iap = gelation.ion_activity_product_alpp(a_al, a_pp, 1.0, 3.0)
    assert iap == pytest.approx(a_al * a_pp ** 3, rel=1e-13)              # Al(PO3)3 stoichiometry
    assert gelation.saturation_ratio_alpp(a_al, a_pp, 1.0, 3.0, iap) == pytest.approx(1.0, rel=1e-13)
    assert gelation.saturation_ratio_alpp(2 * a_al, a_pp, 1.0, 3.0, iap) > 1.0
    assert gelation.saturation_ratio_alpp(a_al, a_pp, 1.0, 3.0, 2 * iap) < 1.0


# ------------------------------------------------------------------ coacervate wetting (C3)
SITE = dict(T=298.15, Gamma_P=2e-6, K_P=1e4, delta_P=5e-10)


def test_substrate_energies_reduce_to_site_free_contacts():
    assert coacervate.substrate_dilute_energy(0.07, a_P=0.0, Pi_osm=0.0, **SITE) == 0.07
    assert coacervate.substrate_dense_energy(0.05, a_P=0.0, Pi_osm=0.0, **SITE) == 0.05


def test_adsorption_terms_cancel_at_coexistence():
    """Equal a_P and Pi_osm in both liquids: the difference is the site-free difference whatever the binding."""
    for k_p in (1.0, 1e4, 1e9):
        site = dict(SITE, K_P=k_p)
        gl = coacervate.substrate_dilute_energy(0.07, a_P=1e-3, Pi_osm=2e5, **site)
        gn = coacervate.substrate_dense_energy(0.05, a_P=1e-3, Pi_osm=2e5, **site)
        assert gl - gn == pytest.approx(coacervate.dense_phase_preference(0.07, 0.05), rel=1e-12, abs=1e-15)


def test_spreading_limits_and_signs():
    assert coacervate.spreading_coefficient(0.07, 0.05, 0.0) == pytest.approx(0.02)
    assert coacervate.spreading_coefficient(0.05 + 1e-3, 0.05, 1e-3) == pytest.approx(0.0, abs=1e-15)
    assert coacervate.contact_angle_cosine(0.05, 0.05, 1e-3) == 0.0
    # Young form on the partial-wetting branch
    l, n, c = 0.0505, 0.05, 1e-3
    assert coacervate.spreading_coefficient(l, n, c) == pytest.approx(c * (coacervate.contact_angle_cosine(l, n, c) - 1))
    # gamma_nl -> 0: the cosine diverges with the sign of Dgamma
    assert coacervate.contact_angle_cosine(0.051, 0.05, 1e-12) > 1e8
    assert coacervate.contact_angle_cosine(0.049, 0.05, 1e-12) < -1e8
    s = coacervate.spreading_coefficient(np.array([0.05, 0.06]), 0.05, 1e-3)
    assert s[1] > s[0]
    assert coacervate.spreading_coefficient(0.06, 0.05, 2e-3) < coacervate.spreading_coefficient(0.06, 0.05, 1e-3)


def test_rejected_two_concentration_form_credits_binding():
    """The rejected form vanishes only at equal concentrations and grows with the binding constant."""
    assert wrong_variants.coacervate_preference_ideal(298.15, 2e-6, 1.0, 10.0, 10.0, 5e-10) == 0.0
    weak = wrong_variants.coacervate_preference_ideal(298.15, 2e-6, 1e-3, 1e3, 1.0, 5e-10)
    strong = wrong_variants.coacervate_preference_ideal(298.15, 2e-6, 1e2, 1e3, 1.0, 5e-10)
    assert strong > weak


# ------------------------------------------------------------------ checker: auxiliary symbols in a limit case
def test_checker_samples_aux_symbols_as_positive():
    contract_text = "version: 6\nfunctions: [{name: x, expression: 'aux_u'}]\n# aux_u\n"
    symbols_text = "symbols: []\n"
    c = eq.Contract(contract_text, symbols_text)
    assert c.interval("aux_u")[1] == 0.0 and math.isinf(c.interval("aux_u")[2])
