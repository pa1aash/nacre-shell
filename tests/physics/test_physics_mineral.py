"""Contract v5 in the physics core: the stoichiometric Omega, the per-formula-unit driving force and
barrier, and the phosphate speciation. Calcite (nu = 2) must reproduce the carbonate functions exactly."""
import numpy as np
import pytest

from nacre.physics import nucleation, speciation, supersaturation as sat
from nacre.physics.constants import AVOGADRO, BOLTZMANN
from nacre.physics.devtools import wrong_variants as wrong

T = 298.15
SPEC = dict(pK1_phosphoric=2.15, pK2_phosphoric=7.2, pK3_phosphoric=12.35, K_CaHPO4_aq=500.0, K_CaH2PO4=20.0,
            K_CaPO4=1.0e6, K_CaOH=10.0, a_w=1.0, A_DH=0.509, b_D=0.3, I_val=0.5, rho_water=997.0)


def test_calcite_is_the_nu_two_case_of_every_function():
    a_ca, a_co3, k = 3.0e-4, 2.0e-5, 3.3e-9
    om = sat.saturation_ratio_bulk(a_ca, a_co3, k)
    assert sat.saturation_ratio_mineral(a_ca, a_co3, 1.0, 1, 1, 0, 1.0, 0, k) == pytest.approx(om, rel=1e-12)
    assert sat.ions_per_formula_unit(1, 1, 0) == 2
    dmu = sat.driving_force_per_formula_unit(om, T)
    assert sat.driving_force_formula_unit(a_ca, a_co3, 1.0, 1, 1, 0, 1.0, 0, k, T) == pytest.approx(dmu, rel=1e-12)
    hom = nucleation.homogeneous_barrier_from_saturation(0.08, 3.7e-5, om, T)
    got = nucleation.homogeneous_barrier_mineral(0.08, 3.7e-5, a_ca, a_co3, 1.0, 1, 1, 0, 1.0, 0, k, T)
    assert got == pytest.approx(hom, rel=1e-12)
    het = nucleation.heterogeneous_barrier_from_saturation(1.1, 0.08, 3.7e-5, om, T)
    assert nucleation.heterogeneous_barrier_mineral(1.1, 0.08, 3.7e-5, a_ca, a_co3, 1.0, 1, 1, 0, 1.0, 0, k, T) \
        == pytest.approx(het, rel=1e-12)
    hyd = sat.saturation_ratio_bulk_hydrated(a_ca, a_co3, 0.7, 6, k)
    assert sat.saturation_ratio_mineral(a_ca, a_co3, 1.0, 1, 1, 0, 0.7, 6, k) == pytest.approx(hyd, rel=1e-12)


def test_hydroxyapatite_nu_nine_exponents_and_per_ion_overstatement():
    a_ca, a_po4, a_oh, k = 2.0e-3, 1.0e-6, 1.0e-4, 1.0e-55
    assert sat.ions_per_formula_unit(5, 3, 1) == 9
    om = sat.saturation_ratio_mineral(a_ca, a_po4, a_oh, 5, 3, 1, 1.0, 0, k)
    assert om == pytest.approx(a_ca ** 5 * a_po4 ** 3 * a_oh / k, rel=1e-12)
    args = (0.05, 1.6e-4, a_ca, a_po4, a_oh, 5, 3, 1, 1.0, 0, k, T)
    hom = nucleation.homogeneous_barrier_mineral(*args)
    per_ion = wrong.homogeneous_barrier_per_ion(0.05, 1.6e-4, 9, a_ca, a_po4, a_oh, 5, 3, 1, 1.0, 0, k, T)
    assert per_ion / hom == pytest.approx(81.0, rel=1e-12)
    n_star = nucleation.critical_formula_units(*args)
    assert hom == pytest.approx(0.5 * n_star * BOLTZMANN * T * np.log(om), rel=1e-12)
    assert hom == pytest.approx(16 * np.pi * 0.05 ** 3 * (1.6e-4) ** 2 / (3 * AVOGADRO ** 2 * (BOLTZMANN * T * np.log(om)) ** 2),
                                rel=1e-12)


def test_octacalcium_phosphate_water_enters_as_a_w_power():
    a = dict(a_Ca=1e-3, a_X=1e-6, a_Y=1e-5, k=1e-48)
    om1 = sat.saturation_ratio_mineral(a["a_Ca"], a["a_X"], a["a_Y"], 8, 4, 2, 1.0, 5, a["k"])
    om2 = sat.saturation_ratio_mineral(a["a_Ca"], a["a_X"], a["a_Y"], 8, 4, 2, 0.8, 5, a["k"])
    assert om2 / om1 == pytest.approx(0.8 ** 5, rel=1e-12)
    assert sat.ions_per_formula_unit(8, 4, 2) == 14


def test_barrier_rejects_undersaturation():
    with pytest.raises(ValueError):
        nucleation.homogeneous_barrier_mineral(0.05, 1.6e-4, 1e-9, 1e-9, 1.0, 5, 3, 1, 1.0, 0, 1e-55, T)


def test_molar_volume_and_hydroxide():
    assert sat.molar_volume_formula_unit(1.0e-1, 2.0e3) == pytest.approx(5.0e-5)
    assert sat.hydroxide_activity(1.0, 12.0, 14.0) == pytest.approx(1e-2)
    assert sat.hydroxide_activity(1.0, 7.0, 7.0) == 1.0


def _speciate(pH, P_T, Ca_T, I):
    return speciation.speciate_phosphate(pH, P_T, Ca_T, I, **SPEC)


def test_speciation_no_calcium_is_the_acid_base_system():
    s = _speciate(9.0, 5.0, 1e-12, 0.01)
    assert s["a_PO4"] == pytest.approx(s["m_PT"] / s["A_phos"], rel=1e-9)
    assert s["a_Ca"] == pytest.approx(s["m_CaT"] / s["D_Ca"], rel=1e-6)


def test_speciation_zero_ionic_strength_gives_ideal_activities():
    s = _speciate(9.0, 5.0, 2.0, 0.0)
    assert (s["g_1"], s["g_2"], s["g_3"]) == (1.0, 1.0, 1.0)


def test_speciation_high_ph_leaves_only_po4():
    s = _speciate(14.5, 5.0, 1e-12, 0.0)
    frac = speciation.phosphate_fraction_acidbase(s["g_3"], SPEC["pK1_phosphoric"], SPEC["pK2_phosphoric"],
                                                  SPEC["pK3_phosphoric"], 14.5, s["g_1"], s["g_2"])
    assert frac > 0.98
    assert s["a_HPO4"] < 0.02 * s["a_PO4"]


def test_speciation_closure_and_ion_pairs_lower_free_phosphate():
    s = _speciate(10.0, 5.0, 10.0, 0.05)
    res = speciation.phosphate_closure_residual(s["A_phos"], s["a_Ca"], s["P_pair_phos"], s["a_PO4"], s["m_PT"])
    assert abs(res) < 1e-12
    assert s["a_PO4"] <= s["m_PT"] / s["A_phos"]
    parts = (speciation.fraction_po4_free(s["a_PO4"], s["g_3"], s["m_PT"])
             + speciation.fraction_hpo4_free(s["a_HPO4"], s["g_2"], s["m_PT"])
             + speciation.fraction_h2po4_free(s["a_PO4"], SPEC["pK2_phosphoric"], SPEC["pK3_phosphoric"], 10.0,
                                              s["g_1"], s["m_PT"])
             + speciation.fraction_h3po4(s["a_PO4"], SPEC["pK1_phosphoric"], SPEC["pK2_phosphoric"],
                                         SPEC["pK3_phosphoric"], 10.0, s["m_PT"])
             + speciation.fraction_pairs_phosphate(s["a_Ca"], s["a_PO4"], s["P_pair_phos"], s["m_PT"]))
    assert parts == pytest.approx(1.0, rel=1e-12)


def test_speciation_refuses_ionic_strength_beyond_validity():
    with pytest.raises(speciation.ActivityModelRange):
        _speciate(10.0, 5.0, 10.0, 0.6)


def test_acidification_lowers_free_phosphate():
    hi = _speciate(12.0, 5.0, 1.0, 0.01)
    lo = _speciate(6.0, 5.0, 1.0, 0.01)
    assert lo["a_PO4"] < hi["a_PO4"]
