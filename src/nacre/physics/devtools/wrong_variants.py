"""DELIBERATELY WRONG or REJECTED forms of the template barrier. Never use them for results.

They exist only for the C3 item-13 double-counting demonstration and its tests: they show
that the contract implementation (nacre.physics.template, contract v2) differs from forms
that count the template's action twice or in the wrong channel, and in which direction.

saturation_ratio_local_ideal, driving_force_local_ideal  (contract Omega_local_ideal,
    Delta_mu_local_ideal; demonstration: true)
    The local-ideal bookkeeping of contract v1: the enriched Ca2+ in the binding layer is
    given the bulk standard state, Omega_local = (c_local / c_bulk) Omega_bulk, which
    credits the binding free energy to the driving force (exactly -Delta_G_seq per Ca2+ in
    the dilute limit). Inconsistent at equilibrium, where the Ca2+ chemical potential is
    uniform (theory derivation, Section 7).

local_ideal_barrier
    The rejected alternative of SF2: Ca-free gamma_sl0 in Young (no Delta_gamma_ads) and
    the local-ideal Omega. It counts the binding once, but in the wrong channel.

double_counted_sequestration_barrier
    The binding counted twice: Delta_gamma_ads in gamma_sl (as in the contract) AND the
    local-ideal Omega in the driving force.

double_counted_water_barrier
    The water-displacement correction applied inside the deck's gamma_eff = gamma_nl -
    Delta_gamma_w (Young's denominator and the homogeneous barrier) AND again through
    gamma_sn = gamma_sn0 + Delta_gamma_w in Young's numerator.
"""
import numpy as np

from nacre.physics import nucleation, sequestration, wetting
from nacre.physics import supersaturation as sat
from nacre.physics._domain import positive, scalar_or_array
from nacre.physics.constants import BOLTZMANN
from nacre.physics.template import template_liquid_energy_in_situ


def saturation_ratio_local_ideal(c_local, c_bulk, a_Ca, a_CO3, K_sp):
    """DEMONSTRATION ONLY. Local-ideal saturation ratio (c_local / c_bulk) Omega_bulk."""
    cl = positive("c_local (layer Ca2+ concentration)", c_local)
    cb = positive("c_bulk (bulk Ca2+ concentration)", c_bulk)
    return scalar_or_array(cl / cb * np.asarray(sat.saturation_ratio_bulk(a_Ca, a_CO3, K_sp)))


def driving_force_local_ideal(c_local, c_bulk, a_Ca, a_CO3, K_sp, T):
    """DEMONSTRATION ONLY. k_B T ln Omega_local_ideal, J per formula unit."""
    om = saturation_ratio_local_ideal(c_local, c_bulk, a_Ca, a_CO3, K_sp)
    t = positive("T (temperature)", T)
    return scalar_or_array(BOLTZMANN * t * np.log(om))


def _omega_local_ideal(Delta_G_seq, T, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp):
    e = sequestration.enrichment_factor(Delta_G_seq, T)
    c_max = sequestration.binding_layer_saturation_concentration(Gamma_s, delta_s)
    c_local = sequestration.local_calcium_concentration(e, c_bulk, c_max)
    return saturation_ratio_local_ideal(c_local, c_bulk, a_Ca, a_CO3, K_sp)


def local_ideal_barrier(gamma_sl0, gamma_sn0, Delta_gamma_w, gamma_nl, V_m, T, Delta_G_seq, c_bulk,
                        Gamma_s, delta_s, a_Ca, a_CO3, K_sp):
    """REJECTED (contract v1 bookkeeping): Ca-free gamma_sl0 in Young, local-ideal Omega."""
    theta = wetting.contact_angle_young(gamma_sl0, gamma_sn0, Delta_gamma_w, gamma_nl)
    omega = _omega_local_ideal(Delta_G_seq, T, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp)
    return nucleation.heterogeneous_barrier_from_saturation(theta, gamma_nl, V_m, omega, T)


def double_counted_sequestration_barrier(gamma_sl0, gamma_sn0, Delta_gamma_w, gamma_nl, V_m, T,
                                         Delta_G_seq, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp):
    """WRONG: Delta_gamma_ads in gamma_sl and the local-ideal Omega (binding counted twice)."""
    sl = template_liquid_energy_in_situ(gamma_sl0, Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    theta = wetting.contact_angle_young(sl, gamma_sn0, Delta_gamma_w, gamma_nl)
    omega = _omega_local_ideal(Delta_G_seq, T, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp)
    return nucleation.heterogeneous_barrier_from_saturation(theta, gamma_nl, V_m, omega, T)


def double_counted_water_barrier(gamma_sl0, gamma_sn0, Delta_gamma_w, gamma_nl, V_m, T,
                                 Delta_G_seq, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp):
    """WRONG: Delta_gamma_w inside the deck's gamma_eff and again in gamma_sn."""
    g_eff = wetting.effective_nucleus_liquid_energy_deck(gamma_nl, Delta_gamma_w)
    sl = template_liquid_energy_in_situ(gamma_sl0, Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    theta = wetting.contact_angle_young(sl, gamma_sn0, Delta_gamma_w, g_eff)
    omega = sat.saturation_ratio_bulk(a_Ca, a_CO3, K_sp)
    return nucleation.heterogeneous_barrier_from_saturation(theta, g_eff, V_m, omega, T)
