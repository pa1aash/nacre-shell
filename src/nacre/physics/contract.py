"""Registry of the theory contract's functions (theory/contract.yaml, lane p0-w3; contract v8).

Maps every contract function name to the physics function that implements it and to the
contract symbol ids of its arguments, in call order. Constants (k_B, N_A, R_gas, F_c, q_e,
hbar, m_e, m_std, c_std) are never arguments: the implementation takes them from nacre.physics.constants.

``valid`` marks inputs where the contract expression is defined but the implementation
rejects the point as outside the physical domain (it raises ValueError there); the
equivalence check samples only valid points and separately confirms the rejection.
"""
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from nacre.physics import (adhesion, coacervate, conformality, film, gelation, hydrolysis, nucleation, sequestration,
                           speciation, stability, template)
from nacre.physics import supersaturation as sat
from nacre.physics import wetting
from nacre.physics.devtools import wrong_variants

#: Contract version this registry implements; the contract tests skip a different version.
CONTRACT_VERSION = 8

CONSTANT_IDS = {"k_B", "N_A", "R_gas", "F_c", "q_e", "hbar", "m_e", "m_std", "c_std"}


@dataclass(frozen=True)
class Entry:
    impl: Callable
    args: tuple
    valid: Optional[Callable] = None


def _young_ratio_in_unit_interval(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl):
    return np.abs((gamma_sl - gamma_sn0 - Delta_gamma_w) / gamma_nl) <= 1.0


def _theta_in_open_interval(theta, d_max):
    return (theta > 0) & (theta < np.pi)


def _davies_representable(z2):
    def ok(A_DH, I_ionic, b_D):
        with np.errstate(all="ignore"):
            return np.abs(speciation.davies_ln_coefficient(z2, A_DH, I_ionic, b_D)) <= speciation.LN_RANGE
    return ok


YOUNG = ("gamma_sl", "gamma_sn0", "Delta_gamma_w", "gamma_nl")
CNT = ("gamma_nl", "V_m", "Omega", "T")
BIND = ("Delta_G_seq", "T", "c_bulk", "Gamma_s", "delta_s")
DAVIES = ("A_DH", "I_ionic", "b_D")

MINERAL = ("a_Ca", "a_X", "a_Y", "nu_Ca", "nu_X", "nu_Y", "a_w", "n_hyd")
PHOS_A = ("pK1_phosphoric", "pK2_phosphoric", "pK3_phosphoric", "pH", "g_1", "g_2", "g_3")


def _supersaturated_mineral(**kw):
    """Validity filter of the mineral barriers: Omega_nu > 1 (the barrier is undefined below it)."""
    with np.errstate(all="ignore"):
        return sat.ln_saturation_ratio_mineral(*[kw[n] for n in MINERAL + ("K_sp",)]) > 0


def _li_exchanged(**kw):
    return kw["Delta_n_Li"] != 0


FUNCTIONS = {
    # C1 adhesion in water
    "W_adh_wet": Entry(adhesion.work_of_adhesion_wet, ("gamma_ow", "gamma_pw", "gamma_op")),
    "W_adh_dry_fn": Entry(adhesion.work_of_adhesion_dry, ("gamma_o", "gamma_p", "gamma_op")),
    "W_adh_wet_from_pmf": Entry(adhesion.work_of_adhesion_from_pmf, ("Delta_F_pmf", "A_c")),
    # C2 sequestration
    "Delta_G_seq_cycle": Entry(sequestration.sequestration_free_energy, ("Delta_G_site", "pKa", "pH", "T")),
    "E_enr": Entry(sequestration.enrichment_factor, ("Delta_G_seq", "T")),
    "c_max": Entry(sequestration.binding_layer_saturation_concentration, ("Gamma_s", "delta_s")),
    "c_local": Entry(sequestration.local_calcium_concentration, ("E_enr", "c_bulk", "c_max")),
    "x_bind": Entry(sequestration.binding_odds, BIND),
    "Theta_occ": Entry(sequestration.site_occupancy, BIND),
    "Gamma_Ca": Entry(sequestration.calcium_surface_excess, BIND),
    "Delta_gamma_ads": Entry(sequestration.adsorption_interfacial_energy_change, BIND),
    "gamma_sl_insitu": Entry(template.template_liquid_energy_in_situ, ("gamma_sl0",) + BIND),
    # admissibility of gamma_sl and the analog route (contract v4, D27)
    "Pi_ads": Entry(template.adsorption_lowering, BIND),
    "Pi_ads_max": Entry(template.maximum_adsorption_lowering, ("Gamma_s", "Delta_G_seq", "T")),
    "gamma_sl_floor": Entry(template.template_liquid_energy_floor, ("gamma_sl0", "Gamma_s", "Delta_G_seq", "T")),
    "r_ads": Entry(template.adsorption_validity_ratio, ("gamma_sl0",) + BIND),
    "Delta_G_seq_cycle_2H": Entry(sequestration.sequestration_free_energy_two_proton,
                                  ("Delta_G_site", "pKa", "pKa2", "pH", "T")),
    "Delta_G_site_from_K": Entry(sequestration.site_free_energy_from_solution_constant,
                                 ("K_Ca_L", "Gamma_s", "delta_s", "T")),
    "x_bind_K": Entry(sequestration.binding_odds_from_solution_constant, ("K_Ca_L", "c_bulk", "pKa", "pKa2", "pH")),
    # carbonate speciation (contract v3)
    "gamma_act_1": Entry(speciation.activity_coefficient_charge_one, DAVIES, _davies_representable(1.0)),
    "gamma_act_2": Entry(speciation.activity_coefficient_charge_two, DAVIES, _davies_representable(4.0)),
    "m_CT_fn": Entry(speciation.total_carbon_molal, ("C_T", "rho_water")),
    "m_CaT_fn": Entry(speciation.total_calcium_molal, ("Ca_T", "rho_water")),
    "A_carb_fn": Entry(speciation.carbonate_speciation_factor, ("pK1_carbonic", "pK2_carbonic", "pH", "g_1", "g_2")),
    "P_pair_fn": Entry(speciation.ion_pair_factor, ("K_CaCO3_aq", "K_CaHCO3", "pK2_carbonic", "pH", "g_1")),
    "D_Ca_fn": Entry(speciation.free_calcium_factor, ("g_1", "g_2", "K_CaOH", "a_w", "pH")),
    "a_CO3_speciation": Entry(speciation.carbonate_activity, ("m_CT", "D_Ca", "A_carb", "P_pair", "m_CaT")),
    "a_Ca_speciation": Entry(speciation.calcium_activity, ("m_CaT", "D_Ca", "P_pair", "a_CO3")),
    "c_Ca_free": Entry(speciation.free_calcium_concentration, ("a_Ca", "rho_water", "g_2")),
    # supersaturation
    "Omega_bulk": Entry(sat.saturation_ratio_bulk, ("a_Ca", "a_CO3", "K_sp")),
    "Omega_bulk_hydrated": Entry(sat.saturation_ratio_bulk_hydrated, ("a_Ca", "a_CO3", "a_w", "n_hyd", "K_sp")),
    "Omega_local_ideal": Entry(wrong_variants.saturation_ratio_local_ideal,
                               ("c_local", "c_bulk", "a_Ca", "a_CO3", "K_sp")),
    "Delta_mu": Entry(sat.driving_force_per_formula_unit, ("Omega", "T")),
    "Delta_mu_local_ideal": Entry(wrong_variants.driving_force_local_ideal,
                                  ("c_local", "c_bulk", "a_Ca", "a_CO3", "K_sp", "T")),
    # C3 nucleation
    "r_star": Entry(nucleation.critical_radius_from_saturation, CNT),
    "DG_hom": Entry(nucleation.homogeneous_barrier_from_saturation, CNT),
    "f_theta": Entry(wetting.shape_factor, ("theta",)),
    "DG_het": Entry(nucleation.heterogeneous_barrier_from_saturation, ("theta",) + CNT),
    "B_acc": Entry(nucleation.accessible_barrier, ("J0_het", "t_proc", "N_req", "T")),
    "N_nuc": Entry(nucleation.nucleus_areal_density, ("J0_het", "t_proc", "DG_het", "T")),
    "cos_theta_young": Entry(wetting.contact_angle_cosine_young, YOUNG),
    "cos_theta_template": Entry(template.contact_angle_cosine_template,
                                ("gamma_sl0", "gamma_sn0", "Delta_gamma_w", "gamma_nl") + BIND),
    "theta_young": Entry(wetting.contact_angle_young, YOUNG, _young_ratio_in_unit_interval),
    "gamma_eff_deck": Entry(wetting.effective_nucleus_liquid_energy_deck, ("gamma_nl", "Delta_gamma_w")),
    "cos_theta_deck": Entry(wetting.contact_angle_cosine_deck,
                            ("gamma_sl", "gamma_sn0", "gamma_nl", "Delta_gamma_w"),
                            lambda gamma_sl, gamma_sn0, gamma_nl, Delta_gamma_w: gamma_nl - Delta_gamma_w > 0),
    "cos_theta_young_at0": Entry(wetting.contact_angle_cosine_young_uncorrected,
                                 ("gamma_sl", "gamma_sn0", "gamma_nl")),
    # stoichiometric generalisation (contract v5)
    "nu_ions": Entry(sat.ions_per_formula_unit, ("nu_Ca", "nu_X", "nu_Y")),
    "IAP": Entry(sat.ion_activity_product, MINERAL),
    "Omega_nu": Entry(sat.saturation_ratio_mineral, MINERAL + ("K_sp",)),
    "Delta_mu_fu": Entry(sat.driving_force_formula_unit, MINERAL + ("K_sp", "T")),
    "V_m_fu": Entry(sat.molar_volume_formula_unit, ("M_fu", "rho_s")),
    "n_star_fu": Entry(nucleation.critical_formula_units, ("gamma_nl", "V_m") + MINERAL + ("K_sp", "T"),
                       _supersaturated_mineral),
    "DG_hom_mineral": Entry(nucleation.homogeneous_barrier_mineral, ("gamma_nl", "V_m") + MINERAL + ("K_sp", "T"),
                            _supersaturated_mineral),
    "DG_het_mineral": Entry(nucleation.heterogeneous_barrier_mineral,
                            ("theta", "gamma_nl", "V_m") + MINERAL + ("K_sp", "T"), _supersaturated_mineral),
    "ln_Omega_exponent_error": Entry(wrong_variants.ln_omega_exponent_error, MINERAL + ("K_sp",)),
    "DG_hom_per_ion": Entry(wrong_variants.homogeneous_barrier_per_ion,
                            ("gamma_nl", "V_m", "nu") + MINERAL + ("K_sp", "T"), _supersaturated_mineral),
    "a_OH_fn": Entry(sat.hydroxide_activity, ("a_w", "pH", "pKw")),
    # phosphate speciation (contract v5)
    "gamma_act_3": Entry(speciation.activity_coefficient_charge_three, DAVIES, _davies_representable(9.0)),
    "m_PT_fn": Entry(speciation.total_phosphate_molal, ("P_T", "rho_water")),
    "A_phos_fn": Entry(speciation.phosphate_speciation_factor, PHOS_A),
    "P_pair_phos_fn": Entry(speciation.phosphate_ion_pair_factor,
                            ("K_CaHPO4_aq", "K_CaH2PO4", "K_CaPO4", "pK2_phosphoric", "pK3_phosphoric", "pH", "g_1")),
    "a_PO4_speciation": Entry(speciation.phosphate_activity, ("m_PT", "D_Ca", "A_phos", "P_pair_phos", "m_CaT")),
    "a_Ca_speciation_phos": Entry(speciation.calcium_activity_phosphate, ("m_CaT", "D_Ca", "P_pair_phos", "a_PO4")),
    "a_HPO4_speciation": Entry(speciation.hydrogen_phosphate_activity, ("a_PO4", "pK3_phosphoric", "pH")),
    "f_PO4_acidbase": Entry(speciation.phosphate_fraction_acidbase, ("g_3",) + PHOS_A[:4] + ("g_1", "g_2")),
    "f_PO4_free": Entry(speciation.fraction_po4_free, ("a_PO4", "g_3", "m_PT")),
    "f_HPO4_free": Entry(speciation.fraction_hpo4_free, ("a_HPO4", "g_2", "m_PT")),
    "f_H2PO4_free": Entry(speciation.fraction_h2po4_free,
                          ("a_PO4", "pK2_phosphoric", "pK3_phosphoric", "pH", "g_1", "m_PT")),
    "f_H3PO4_free": Entry(speciation.fraction_h3po4,
                          ("a_PO4", "pK1_phosphoric", "pK2_phosphoric", "pK3_phosphoric", "pH", "m_PT")),
    "f_pairs_phos": Entry(speciation.fraction_pairs_phosphate, ("a_Ca", "a_PO4", "P_pair_phos", "m_PT")),
    "f_phos_closure": Entry(speciation.phosphate_closure_residual, ("A_phos", "a_Ca", "P_pair_phos", "a_PO4", "m_PT")),
    # C4 conformality
    "S_spread": Entry(conformality.spreading_coefficient, YOUNG),
    "h_c": Entry(conformality.coalescence_thickness, ("theta", "N_s")),
    "h_cl": Entry(conformality.closure_thickness, ("theta", "N_s")),
    "N_s_closure": Entry(conformality.closure_island_density, ("theta", "d_max"), _theta_in_open_interval),
    # C5 stability
    "Psi_pbx": Entry(stability.pourbaix_potential,
                     ("G_phase", "mu_H2O", "N_O", "N_H", "N_M", "Q_charge", "T", "pH", "E_SHE")),
    "Delta_G_pbx": Entry(stability.energy_above_pourbaix_hull, ("Psi_pbx", "Psi_hull"),
                         lambda Psi_pbx, Psi_hull: Psi_pbx >= Psi_hull),
    "mu_Li": Entry(stability.lithium_chemical_potential, ("mu_Li0", "E_Li")),
    "Phi_Li": Entry(stability.lithium_grand_potential, ("G_phase", "N_Li", "mu_Li0", "E_Li")),
    "Delta_Phi_r": Entry(stability.reaction_grand_potential_change, ("Delta_G_r", "Delta_n_Li", "E_Li")),
    "E_window": Entry(stability.reaction_limit_potential, ("Delta_G_r", "Delta_n_Li"),
                      lambda Delta_G_r, Delta_n_Li: Delta_n_Li != 0),
    # insulating-film limitation
    "R_A": Entry(film.area_specific_resistance, ("rho_e", "d_film")),
    "d_max_ohm": Entry(film.ohmic_thickness_bound, ("R_A_max", "rho_e")),
    "kappa": Entry(film.tunnelling_decay_constant, ("phi_B",)),
    "d_max_tun": Entry(film.tunnelling_thickness_bound, ("j_0", "j_req", "kappa")),
    # K1 bracket and the framings of the route products (contract v6; cp4 F2, ruling C4)
    "E_ub": Entry(stability.onset_solid_salt_sink, ("Delta_G_r_ss", "Delta_n_Li"), _li_exchanged),
    "E_lb": Entry(stability.onset_aqueous_sink, ("Delta_G_r_aq", "Delta_n_Li"), _li_exchanged),
    "E_solv": Entry(stability.onset_cell_solvent, ("Delta_G_r_aq", "Delta_G_tr_rel", "Delta_n_Li"), _li_exchanged),
    "Delta_G_tr_rel_born": Entry(stability.relative_transfer_born, ("B_born", "z_M", "r_M", "r_Li")),
    "E_window_glass": Entry(stability.onset_glass, ("Delta_G_r", "Delta_G_gc", "Delta_n_Li"), _li_exchanged),
    "E_lb_glass": Entry(stability.onset_aqueous_sink_glass, ("Delta_G_r_aq", "Delta_G_gc", "Delta_n_Li"), _li_exchanged),
    "E_ub_glass": Entry(stability.onset_solid_salt_sink_glass, ("Delta_G_r_ss", "Delta_G_gc", "Delta_n_Li"),
                        _li_exchanged),
    "Omega_glass": Entry(sat.saturation_ratio_glass, MINERAL + ("K_sp", "Delta_G_gc", "T")),
    # hydrated amorphous phases against the crystalline reference plus water (contract v8; I17a)
    "E_ub_hydrated_am": Entry(stability.onset_solid_salt_sink_hydrated_amorphous,
                              ("Delta_G_r_ss", "Delta_G_gc_w", "n_hyd", "a_w", "T", "Delta_n_Li"), _li_exchanged),
    # sink reference state of E_ub (contract v7; PH-W3.8 ruling 2)
    "m_sink": Entry(stability.sink_margin, ("nu_salt", "T", "a_pm_sat", "a_pm")),
    "E_ub_sink": Entry(stability.onset_solid_salt_sink_dilute,
                       ("Delta_G_r_ss", "Delta_n_Li", "nu_salt", "T", "a_pm_sat", "a_pm"), _li_exchanged),
    "E_ub_prod_unsat": Entry(stability.onset_solid_salt_sink_product_unsaturated,
                             ("Delta_G_r_ss", "Delta_n_Li", "nu_prod", "T", "x_sat_prod"),
                             lambda Delta_G_r_ss, Delta_n_Li, nu_prod, T, x_sat_prod: (Delta_n_Li != 0) & (x_sat_prod <= 1.0)),
    # hydrolysis descriptor (contract v6; ruling C1)
    "k_hyd_eff": Entry(hydrolysis.effective_rate_constant, ("tau_k", "k_hyd")),
    "t_half_hyd_fn": Entry(hydrolysis.half_life, ("tau_k", "k_hyd")),
    "f_cond": Entry(hydrolysis.condensed_fraction, ("t_wet", "t_half_hyd")),
    "t_wet_max": Entry(hydrolysis.wet_time_flip, ("t_half_hyd", "f_min")),
    # R1 formation criterion (contract v6; ruling C2)
    "a_Al_oxide_eq": Entry(gelation.aluminium_activity_oxide_equilibrium, ("K_ox_Al", "pH", "a_w")),
    "a_PP_free": Entry(gelation.free_chain_unit_activity, ("a_PP_tot", "beta_AlPP", "a_Al")),
    "IAP_AlPP": Entry(gelation.ion_activity_product_alpp, ("a_Al", "a_PP", "nu_Al", "nu_PP")),
    "Omega_AlPP": Entry(gelation.saturation_ratio_alpp, ("a_Al", "a_PP", "nu_Al", "nu_PP", "K_sp_AlPP")),
    # liquid wetting of the coacervate (contract v6; ruling C3)
    "gamma_al_l_ads": Entry(coacervate.substrate_dilute_energy,
                            ("gamma_al_l0", "T", "Gamma_P", "K_P", "a_P", "delta_P", "Pi_osm")),
    "gamma_al_n_ads": Entry(coacervate.substrate_dense_energy,
                            ("gamma_al_n0", "T", "Gamma_P", "K_P", "a_P", "delta_P", "Pi_osm")),
    "Dgamma_coac": Entry(coacervate.dense_phase_preference, ("gamma_al_l0", "gamma_al_n0")),
    "S_coac": Entry(coacervate.spreading_coefficient, ("gamma_al_l", "gamma_al_n", "gamma_nl_c")),
    "cos_theta_coac": Entry(coacervate.contact_angle_cosine, ("gamma_al_l", "gamma_al_n", "gamma_nl_c")),
    "Dgamma_coac_ideal": Entry(wrong_variants.coacervate_preference_ideal, ("T", "Gamma_P", "K_Pc", "c_n", "c_l", "delta_P")),
}


def evaluate(name, **inputs):
    """Evaluate contract function ``name`` with inputs keyed by contract symbol id."""
    entry = FUNCTIONS[name]
    return entry.impl(*[inputs[a] for a in entry.args])
