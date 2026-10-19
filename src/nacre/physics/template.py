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

Admissibility (contract v4, decision D27): the planar template-liquid interface exists only
while gamma_sl = gamma_sl0 + Delta_gamma_ads >= 0. Reported with it:
    Pi_ads          = -Delta_gamma_ads                   (lowering by adsorption)
    Pi_ads_max      = Gamma_s (-Delta_G_seq - R T (1 - exp(Delta_G_seq / (R T))))
                      (largest lowering at any Ca2+ activity, Delta_G_seq < 0)
    gamma_sl_floor  = gamma_sl0 - Pi_ads_max             (lowest gamma_sl at any dose)
    r_ads           = -Delta_gamma_ads / gamma_sl0       (validity ratio; admissible iff <= 1)
"""
import numpy as np

from nacre.physics import nucleation, sequestration, wetting
from nacre.physics import supersaturation as sat
from nacre.physics._domain import open_interval, positive, real, scalar_or_array
from nacre.physics.constants import GAS_CONSTANT


def template_liquid_energy_in_situ(gamma_sl0, Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """Template-liquid interfacial energy at the regime activities, J m^-2.

    gamma_sl = gamma_sl0 + Delta_gamma_ads: the Ca-free energy plus the change by
    equilibrium Ca2+ adsorption. Stronger binding lowers it.
    """
    sl0 = real("gamma_sl0 (template-liquid energy without Ca2+ binding)", gamma_sl0)
    d_ads = sequestration.adsorption_interfacial_energy_change(Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    return scalar_or_array(sl0 + np.asarray(d_ads))


def adsorption_lowering(Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """Pi_ads = -Delta_gamma_ads, the lowering of gamma_sl by Ca2+ adsorption, J m^-2.

    The spreading pressure of the occupied sites less the bulk-depletion term; admissibility is
    Pi_ads <= gamma_sl0.
    """
    d_ads = sequestration.adsorption_interfacial_energy_change(Delta_G_seq, T, c_bulk, Gamma_s, delta_s)
    return scalar_or_array(-np.asarray(d_ads))


def _expm1_minus_x(y):
    """exp(y) - 1 - y without cancellation (series for |y| < 1/2)."""
    y = np.atleast_1d(np.asarray(y, dtype=float))
    out = np.expm1(y) - y
    small = np.abs(y) < 0.5
    if np.any(small):
        ys = y[small]
        term, acc = ys * ys / 2.0, np.zeros_like(ys)
        for k in range(3, 30):
            acc += term
            term = term * ys / k
        out[small] = acc
    return out


def maximum_adsorption_lowering(Gamma_s, Delta_G_seq, T):
    """Pi_ads_max, the largest lowering of gamma_sl by Ca2+ adsorption at any Ca2+ activity, J m^-2.

    Gamma_s (-Delta_G_seq - R T (1 - exp(Delta_G_seq / (R T)))) = R T Gamma_s (ln E - 1 + 1/E),
    reached where the Gibbs excess vanishes; defined for a binding template (Delta_G_seq < 0),
    never above -Gamma_s Delta_G_seq and unrelated to gamma_sl0. delta_s does not enter.
    """
    gs = positive("Gamma_s (areal binding-site density)", Gamma_s)
    g = open_interval("Delta_G_seq (binding template)", Delta_G_seq, -np.inf, 0.0)
    t = positive("T (temperature)", T)
    rt = GAS_CONSTANT * t
    y = np.asarray(g / rt, dtype=float)
    return scalar_or_array(gs * rt * _expm1_minus_x(y).reshape(y.shape))


def template_liquid_energy_floor(gamma_sl0, Gamma_s, Delta_G_seq, T):
    """gamma_sl_floor = gamma_sl0 - Pi_ads_max: the lowest gamma_sl of a binding template at any dose, J m^-2.

    gamma_sl_floor >= 0 is sufficient for admissibility at every Ca2+ activity (reported, not gating).
    """
    sl0 = real("gamma_sl0 (template-liquid energy without Ca2+ binding)", gamma_sl0)
    return scalar_or_array(sl0 - np.asarray(maximum_adsorption_lowering(Gamma_s, Delta_G_seq, T)))


def adsorption_validity_ratio(gamma_sl0, Delta_G_seq, T, c_bulk, Gamma_s, delta_s):
    """r_ads = -Delta_gamma_ads / gamma_sl0, the validity ratio of the small-change term (dimensionless).

    gamma_sl = gamma_sl0 (1 - r_ads): admissible iff r_ads <= 1; near one the Gibbs-Langmuir
    expansion carries an error it does not control. Defined for gamma_sl0 > 0.
    """
    sl0 = positive("gamma_sl0 (template-liquid energy without Ca2+ binding)", gamma_sl0)
    return scalar_or_array(np.asarray(adsorption_lowering(Delta_G_seq, T, c_bulk, Gamma_s, delta_s)) / sl0)


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
