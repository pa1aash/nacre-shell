"""DELIBERATELY WRONG variants of the template barrier. Never use them for results.

They exist only to demonstrate, in tests and in the C3 item-13 double-counting
demonstration, that the contract implementation differs from forms that count the
template's action twice, and in which direction.

double_counted_sequestration_barrier
    The template's Ca2+ binding enters through Omega_local (as in the contract) AND again
    as a shift of an interfacial energy by the binding free energy per unit area,
    Gamma_s Delta_G_seq (J mol^-1 x mol m^-2 = J m^-2), inside Young. The shifted energy is
    either gamma_sn (``interface="sn"``: the bound Ca2+ is credited with stabilising the
    template-nucleus contact) or gamma_sl (``interface="sl"``: a Gibbs-adsorption-like
    lowering of the template-liquid energy).

double_counted_water_barrier
    The water-displacement correction Delta_gamma_w applied inside the deck's
    gamma_eff = gamma_nl - Delta_gamma_w (in Young's denominator and in the homogeneous
    barrier) AND again through gamma_sn = gamma_sn0 + Delta_gamma_w in Young's numerator.
"""
import numpy as np

from nacre.physics import nucleation, wetting
from nacre.physics.template import enrichment_channel


def double_counted_sequestration_barrier(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl, V_m, T,
                                         Delta_G_seq, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp,
                                         interface="sn"):
    shift = np.asarray(Gamma_s, float) * np.asarray(Delta_G_seq, float)
    if interface == "sn":
        theta = wetting.contact_angle_young(gamma_sl, np.asarray(gamma_sn0) + shift, Delta_gamma_w, gamma_nl)
    elif interface == "sl":
        theta = wetting.contact_angle_young(np.asarray(gamma_sl) + shift, gamma_sn0, Delta_gamma_w, gamma_nl)
    else:
        raise ValueError("interface must be 'sn' or 'sl'")
    omega = enrichment_channel(Delta_G_seq, T, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp)
    return nucleation.heterogeneous_barrier_from_saturation(theta, gamma_nl, V_m, omega, T)


def double_counted_water_barrier(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl, V_m, T,
                                 Delta_G_seq, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp):
    g_eff = wetting.effective_nucleus_liquid_energy_deck(gamma_nl, Delta_gamma_w)
    theta = wetting.contact_angle_young(gamma_sl, gamma_sn0, Delta_gamma_w, g_eff)
    omega = enrichment_channel(Delta_G_seq, T, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp)
    return nucleation.heterogeneous_barrier_from_saturation(theta, g_eff, V_m, omega, T)
