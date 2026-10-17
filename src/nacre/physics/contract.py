"""Registry of the theory contract's functions (theory/contract.yaml, lane p0-w3; contract v3).

Maps every contract function name to the physics function that implements it and to the
contract symbol ids of its arguments, in call order. Constants (k_B, N_A, R_gas, F_c, q_e,
hbar, m_e, m_std) are never arguments: the implementation takes them from nacre.physics.constants.

``valid`` marks inputs where the contract expression is defined but the implementation
rejects the point as outside the physical domain (it raises ValueError there); the
equivalence check samples only valid points and separately confirms the rejection.
"""
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from nacre.physics import adhesion, conformality, film, nucleation, sequestration, speciation, stability, template
from nacre.physics import supersaturation as sat
from nacre.physics import wetting
from nacre.physics.devtools import wrong_variants

#: Contract version this registry implements; the contract tests skip a different version.
CONTRACT_VERSION = 3

CONSTANT_IDS = {"k_B", "N_A", "R_gas", "F_c", "q_e", "hbar", "m_e", "m_std"}


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
}


def evaluate(name, **inputs):
    """Evaluate contract function ``name`` with inputs keyed by contract symbol id."""
    entry = FUNCTIONS[name]
    return entry.impl(*[inputs[a] for a in entry.args])
