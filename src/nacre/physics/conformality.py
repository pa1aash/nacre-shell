"""Wetting-based conformality observables (claim C4)."""
import numpy as np

from nacre.physics._domain import open_interval, positive, real, scalar_or_array


def spreading_coefficient(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl):
    """Spreading coefficient S = gamma_sl - (gamma_sn0 + Delta_gamma_w) - gamma_nl, J m^-2.

    S >= 0 is complete wetting of the template by the nucleus phase (layer growth);
    S < 0 is partial wetting (islands). Equals gamma_nl (cos theta_Young - 1).
    """
    sl = real("gamma_sl (template-liquid energy)", gamma_sl)
    sn0 = real("gamma_sn0 (template-nucleus energy, reference)", gamma_sn0)
    dw = real("Delta_gamma_w (water-displacement correction)", Delta_gamma_w)
    nl = positive("gamma_nl (nucleus-liquid energy)", gamma_nl)
    return scalar_or_array(sl - sn0 - dw - nl)


def coalescence_thickness(theta, N_s):
    """Geometric coalescence thickness h_c = tan(theta / 2) / (2 sqrt(N_s)), in m.

    Cap height of equal spherical-cap islands of contact angle theta (rad, in (0, pi)) on a
    square lattice of areal density N_s (m^-2) when neighbouring bases first touch. Geometric
    only: the charter's kinetic critical coalescence thickness is h_coal (cp2 fix F9), which
    needs a nucleation-and-growth model and is not computed in P0.
    """
    t = open_interval("theta (contact angle)", theta, 0.0, np.pi)
    n = positive("N_s (island density)", N_s)
    return scalar_or_array(np.tan(t / 2.0) / (2.0 * np.sqrt(n)))


def closure_thickness(theta, N_s):
    """Geometric closure thickness h_cl = tan(theta / 2) / sqrt(2 N_s), in m.

    Cap height at which equal spherical-cap islands on a square lattice of density N_s
    cover the whole area (base radius = spacing / sqrt 2); sqrt(2) times h_c.
    """
    t = open_interval("theta (contact angle)", theta, 0.0, np.pi)
    n = positive("N_s (island density)", N_s)
    return scalar_or_array(np.tan(t / 2.0) / np.sqrt(2.0 * n))


def closure_island_density(theta, d_max):
    """Smallest island density for which equal caps close the film at the admissible thickness, m^-2.

    N_s,closure = tan^2(theta / 2) / (2 d_max^2): the closure thickness h_cl(theta, N_s)
    stays within d_max exactly when N_s >= N_s,closure (square lattice of equal caps).
    theta in (0, pi) rad, d_max > 0 in m.
    """
    t = open_interval("theta (contact angle)", theta, 0.0, np.pi)
    d = positive("d_max (admissible film thickness)", d_max)
    return scalar_or_array(np.tan(t / 2.0) ** 2 / (2.0 * d ** 2))
