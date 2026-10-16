"""Registry of the theory contract's functions (theory/contract.yaml, lane p0-w3).

Maps every contract function name to the physics function that implements it and to the
contract symbol ids of its arguments, in call order. Constants (k_B, N_A, R_gas, F_c, q_e,
hbar, m_e) are never arguments: the implementation takes them from nacre.physics.constants.

``valid`` marks inputs where the contract expression is defined but the implementation
rejects the point as outside the physical domain (it raises ValueError there); the
equivalence check samples only valid points and separately confirms the rejection.
"""
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from nacre.physics import adhesion, conformality, film, nucleation, sequestration, stability
from nacre.physics import supersaturation as sat
from nacre.physics import wetting

CONSTANT_IDS = {"k_B", "N_A", "R_gas", "F_c", "q_e", "hbar", "m_e"}


@dataclass(frozen=True)
class Entry:
    impl: Callable
    args: tuple
    valid: Optional[Callable] = None


def _young_ratio_in_unit_interval(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl):
    return np.abs((gamma_sl - gamma_sn0 - Delta_gamma_w) / gamma_nl) <= 1.0


YOUNG = ("gamma_sl", "gamma_sn0", "Delta_gamma_w", "gamma_nl")
CNT = ("gamma_nl", "V_m", "Omega", "T")

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
    # supersaturation
    "Omega_bulk": Entry(sat.saturation_ratio_bulk, ("a_Ca", "a_CO3", "K_sp")),
    "Omega_local": Entry(sat.saturation_ratio_local, ("c_local", "c_bulk", "a_Ca", "a_CO3", "K_sp")),
    "Delta_mu": Entry(sat.driving_force_per_formula_unit, ("Omega", "T")),
    # C3 nucleation
    "r_star": Entry(nucleation.critical_radius_from_saturation, CNT),
    "DG_hom": Entry(nucleation.homogeneous_barrier_from_saturation, CNT),
    "f_theta": Entry(wetting.shape_factor, ("theta",)),
    "DG_het": Entry(nucleation.heterogeneous_barrier_from_saturation, ("theta",) + CNT),
    "cos_theta_young": Entry(wetting.contact_angle_cosine_young, YOUNG),
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
