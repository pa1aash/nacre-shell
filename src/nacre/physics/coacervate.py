"""Liquid wetting of a coacervate on the Al oxide (contract v6; ruling C3, claims_redirect.md 9c).

Three phases: the substrate s (alumina-covered foil), the dense coacervate n and the coexisting dilute phase l. Each
substrate interface carries the Gibbs-Langmuir site term and the solute-exclusion term at the chemical potentials of
its facing phase,

    gamma_sx = gamma_sx0 - R T Gamma_P ln(1 + K_P a_P) + delta_P Pi_osm      (x = l, n),

and at coexistence a_P and Pi_osm are common to both liquids, so the two terms cancel in the difference:
Dgamma = gamma_sl - gamma_sn = gamma_sl0 - gamma_sn0, the site-free contact difference. The spreading coefficient is
S_coac = gamma_sl - gamma_sn - gamma_nl, with the Young cosine (gamma_sl - gamma_sn) / gamma_nl. The ideal-dilute
two-concentration form is REJECTED (nacre.physics.devtools.wrong_variants.coacervate_preference_ideal).
"""
import numpy as np

from nacre.physics._domain import non_negative, positive, real, scalar_or_array
from nacre.physics.constants import GAS_CONSTANT


def _substrate_phase_energy(gamma0, T, Gamma_P, K_P, a_P, delta_P, Pi_osm, label):
    g0 = real(label, gamma0)
    t = positive("T (temperature)", T)
    gp = positive("Gamma_P (site density)", Gamma_P)
    k = positive("K_P (Langmuir constant)", K_P)
    a = non_negative("a_P (chain-unit activity)", a_P)
    d = positive("delta_P (exclusion-layer thickness)", delta_P)
    pi = non_negative("Pi_osm (osmotic pressure)", Pi_osm)
    return scalar_or_array(g0 - GAS_CONSTANT * t * gp * np.log1p(k * a) + d * pi)


def substrate_dilute_energy(gamma_al_l0, T, Gamma_P, K_P, a_P, delta_P, Pi_osm):
    """gamma_sl: substrate - dilute phase energy, J m^-2 (admissible only where >= 0; checked by the screen)."""
    return _substrate_phase_energy(gamma_al_l0, T, Gamma_P, K_P, a_P, delta_P, Pi_osm,
                                   "gamma_al_l0 (site-free substrate - dilute contact)")


def substrate_dense_energy(gamma_al_n0, T, Gamma_P, K_P, a_P, delta_P, Pi_osm):
    """gamma_sn: substrate - coacervate energy at the same chemical potentials, J m^-2."""
    return _substrate_phase_energy(gamma_al_n0, T, Gamma_P, K_P, a_P, delta_P, Pi_osm,
                                   "gamma_al_n0 (site-free substrate - dense contact)")


def dense_phase_preference(gamma_al_l0, gamma_al_n0):
    """Dgamma = gamma_sl - gamma_sn = gamma_sl0 - gamma_sn0, J m^-2: the site and exclusion terms cancel at coexistence."""
    l0 = real("gamma_al_l0 (site-free substrate - dilute contact)", gamma_al_l0)
    n0 = real("gamma_al_n0 (site-free substrate - dense contact)", gamma_al_n0)
    return scalar_or_array(l0 - n0)


def spreading_coefficient(gamma_al_l, gamma_al_n, gamma_nl_c):
    """S_coac = gamma_sl - gamma_sn - gamma_nl, J m^-2; the K4 route form is S_coac >= m_S."""
    l = real("gamma_al_l (substrate - dilute energy)", gamma_al_l)
    n = real("gamma_al_n (substrate - coacervate energy)", gamma_al_n)
    c = non_negative("gamma_nl_c (coacervate - dilute tension)", gamma_nl_c)
    return scalar_or_array(l - n - c)


def contact_angle_cosine(gamma_al_l, gamma_al_n, gamma_nl_c):
    """cos theta = (gamma_sl - gamma_sn) / gamma_nl (unclipped: >= 1 complete wetting, <= -1 dewetting)."""
    l = real("gamma_al_l (substrate - dilute energy)", gamma_al_l)
    n = real("gamma_al_n (substrate - coacervate energy)", gamma_al_n)
    c = positive("gamma_nl_c (coacervate - dilute tension)", gamma_nl_c)
    return scalar_or_array((l - n) / c)
