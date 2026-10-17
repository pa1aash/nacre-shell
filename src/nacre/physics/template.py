"""Heterogeneous barrier on the template through its single channel (claims C2 and C3).

Theory contract v2 (P0-W3.2, uniform chemical potential). The exact reference is the grand
potential of a cap on the template at the bulk chemical potentials; every template-ion
interaction sits inside the grand-canonical interfacial energies, so the template acts on
the barrier only through theta:

    theta channel  cos theta = (gamma_sl0 + Delta_gamma_ads - gamma_sn0 - Delta_gamma_w) / gamma_nl,
                   Delta_gamma_ads = -R T (Gamma_s ln(1 + x) - delta_s c_bulk),
                   x = exp(-Delta_G_seq / (R T)) c_bulk delta_s / Gamma_s;
    Omega channel  Omega = Omega_bulk = a_Ca a_CO3 / K_sp   (bulk inputs only).

Rule for the screen: when gamma_sl is supplied Ca-free (gamma_sl0) Delta_gamma_ads is added
once; when gamma_sl is supplied at the regime activities nothing is added; Omega is never
raised above Omega_bulk. Each template-dependent input (gamma_sl0, gamma_sn0,
Delta_gamma_w, Delta_G_seq, Gamma_s, delta_s) enters the theta channel only; the binding
inputs enter once, through Delta_gamma_ads.
"""
import numpy as np

from nacre.physics import nucleation, sequestration, wetting
from nacre.physics import supersaturation as sat
from nacre.physics._domain import real, scalar_or_array


def template_liquid_energy_in_situ(gamma_sl0, Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """Template-liquid interfacial energy at the regime activities, J m^-2.

    gamma_sl = gamma_sl0 + Delta_gamma_ads: the Ca-free energy plus the change by
    equilibrium Ca2+ adsorption. Stronger binding lowers it.
    """
    sl0 = real("gamma_sl0 (template-liquid energy without Ca2+ binding)", gamma_sl0)
    d_ads = sequestration.adsorption_interfacial_energy_change(Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    return scalar_or_array(sl0 + np.asarray(d_ads))


def contact_angle_cosine_template(gamma_sl0, gamma_sn0, Delta_gamma_w, gamma_nl, Delta_G_seq, T,
                                  c_bulk, Gamma_s, delta_s):
    """Young ratio on the template with Ca2+ adsorption on the template-liquid side (dimensionless).

    (gamma_sl0 + Delta_gamma_ads - gamma_sn0 - Delta_gamma_w) / gamma_nl, returned
    unclipped: only values in [-1, 1] are contact-angle cosines (see wetting).
    """
    sl = template_liquid_energy_in_situ(gamma_sl0, Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    return wetting.contact_angle_cosine_young(sl, gamma_sn0, Delta_gamma_w, gamma_nl)


def wetting_channel(gamma_sl0, gamma_sn0, Delta_gamma_w, gamma_nl, Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """Contact angle theta (rad) of the nucleus on the template: the only template channel.

    Raises ValueError where the Young ratio leaves [-1, 1] (no finite contact angle).
    """
    sl = template_liquid_energy_in_situ(gamma_sl0, Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    return wetting.contact_angle_young(sl, gamma_sn0, Delta_gamma_w, gamma_nl)


def omega_channel(a_Ca, a_CO3, K_sp):
    """Saturation ratio where the nucleus forms: Omega_bulk (uniform chemical potential)."""
    return sat.saturation_ratio_bulk(a_Ca, a_CO3, K_sp)


def template_heterogeneous_barrier(gamma_sl0, gamma_sn0, Delta_gamma_w, gamma_nl, V_m, T,
                                   Delta_G_seq, c_bulk, Gamma_s, delta_s, a_Ca, a_CO3, K_sp):
    """Heterogeneous nucleation barrier on the template, J per nucleus (contract composite).

    f(theta) Delta_G*_hom(gamma_nl, V_m, T, Omega_bulk), with theta from Young with the
    Ca-free gamma_sl0 plus Delta_gamma_ads, the bare gamma_nl in both Young and the
    homogeneous barrier, and the bulk saturation ratio.
    """
    theta = wetting_channel(gamma_sl0, gamma_sn0, Delta_gamma_w, gamma_nl, Delta_G_seq, T, c_bulk,
                            Gamma_s, delta_s)
    omega = omega_channel(a_Ca, a_CO3, K_sp)
    return nucleation.heterogeneous_barrier_from_saturation(theta, gamma_nl, V_m, omega, T)


def template_heterogeneous_barrier_in_situ(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl, V_m, T,
                                           a_Ca, a_CO3, K_sp):
    """The same barrier when gamma_sl is supplied at the regime activities (nothing is added)."""
    theta = wetting.contact_angle_young(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl)
    omega = omega_channel(a_Ca, a_CO3, K_sp)
    return nucleation.heterogeneous_barrier_from_saturation(theta, gamma_nl, V_m, omega, T)


TEMPLATE_DEPENDENT = ("gamma_sl0", "gamma_sn0", "Delta_gamma_w", "Delta_G_seq", "Gamma_s", "delta_s")
TEMPLATE_INDEPENDENT = ("gamma_nl", "V_m", "T", "a_Ca", "a_CO3", "K_sp", "c_bulk")
BINDING_INPUTS = ("Delta_G_seq", "Gamma_s", "delta_s")
COMPOSITE_ARGS = ("gamma_sl0", "gamma_sn0", "Delta_gamma_w", "gamma_nl", "V_m", "T", "Delta_G_seq",
                  "c_bulk", "Gamma_s", "delta_s", "a_Ca", "a_CO3", "K_sp")
