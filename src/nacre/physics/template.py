"""Heterogeneous barrier on the template through its two channels (claims C2 and C3).

Theory contract, no_double_counting: the template acts on the barrier only

    through theta  (interfacial energies, Young):  cos theta = (gamma_sl - gamma_sn0 - Delta_gamma_w) / gamma_nl
    through Omega  (Ca2+ enrichment):              Omega_local = (c_local / c_bulk) a_Ca a_CO3 / K_sp,
                                                   c_local from E_enr = exp(-Delta_G_seq / (R T)) and
                                                   the Langmuir closure with c_max = Gamma_s / delta_s.

Each template-dependent input (gamma_sl, gamma_sn0, Delta_gamma_w, Delta_G_seq, Gamma_s,
delta_s) enters exactly one channel; template-independent bulk inputs (gamma_nl, V_m, T,
a_Ca, a_CO3, K_sp, c_bulk) may enter both.
"""
from nacre.physics import nucleation, sequestration, wetting
from nacre.physics import supersaturation as sat


def wetting_channel(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl):
    """Contact angle theta (rad) of the nucleus on the template: the theta channel."""
    return wetting.contact_angle_young(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl)


def enrichment_channel(Delta_G_seq, T, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp):
    """Local saturation ratio Omega_local in the binding layer: the Omega channel."""
    e = sequestration.enrichment_factor(Delta_G_seq, T)
    c_max = sequestration.binding_layer_saturation_concentration(Gamma_s, delta_s)
    c_local = sequestration.local_calcium_concentration(e, c_bulk, c_max)
    return sat.saturation_ratio_local(c_local, c_bulk, a_Ca, a_CO3, K_sp)


def template_heterogeneous_barrier(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl, V_m, T,
                                   Delta_G_seq, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp):
    """Heterogeneous nucleation barrier on the template, J per nucleus.

    f(theta_Young) Delta_G*_hom(gamma_nl, V_m, T, Omega_local): the bare gamma_nl in both
    Young and the homogeneous barrier, the template's binding only through Omega_local.
    """
    theta = wetting_channel(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl)
    omega = enrichment_channel(Delta_G_seq, T, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp)
    return nucleation.heterogeneous_barrier_from_saturation(theta, gamma_nl, V_m, omega, T)


TEMPLATE_DEPENDENT = ("gamma_sl", "gamma_sn0", "Delta_gamma_w", "Delta_G_seq", "Gamma_s", "delta_s")
TEMPLATE_INDEPENDENT = ("gamma_nl", "V_m", "T", "a_Ca", "a_CO3", "K_sp", "c_bulk")
COMPOSITE_ARGS = ("gamma_sl", "gamma_sn0", "Delta_gamma_w", "gamma_nl", "V_m", "T", "Delta_G_seq",
                  "c_bulk", "Gamma_s", "delta_s", "a_Ca", "a_CO3", "K_sp")
