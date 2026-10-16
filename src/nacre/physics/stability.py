"""Thermodynamic stability potentials (claim C5).

R-slurry: the aqueous Pourbaix potential per non-O non-H atom with O and H exchanged with
water, protons and electrons. R-cell: the Li-open grand potential at the electrode
potential on the Li+/Li scale. Hull construction over competing species is not here.
"""
import numpy as np

from nacre.physics._domain import non_negative, positive, real, scalar_or_array
from nacre.physics.constants import FARADAY, GAS_CONSTANT


def pourbaix_potential(G_phase, mu_H2O, N_O, N_H, N_M, Q_charge, T, pH, E_SHE):
    """Pourbaix potential Psi of a species per non-O non-H atom, J mol^-1.

    (G - n_O mu_H2O - R T ln10 (2 n_O - n_H) pH - (2 n_O - n_H + Q) F E_SHE) / n_M.
    """
    g = real("G_phase", G_phase)
    mu = real("mu_H2O", mu_H2O)
    no = non_negative("N_O", N_O)
    nh = non_negative("N_H", N_H)
    nm = positive("N_M", N_M)
    q = real("Q_charge", Q_charge)
    t = positive("T (temperature)", T)
    ph = real("pH", pH)
    e = real("E_SHE (potential vs SHE)", E_SHE)
    nu = 2.0 * no - nh
    return scalar_or_array((g - no * mu - GAS_CONSTANT * t * np.log(10.0) * nu * ph
                            - (nu + q) * FARADAY * e) / nm)


def energy_above_pourbaix_hull(Psi_pbx, Psi_hull):
    """Energy above the aqueous Pourbaix hull Psi - Psi_hull, J mol^-1 (non-negative)."""
    p = real("Psi_pbx", Psi_pbx)
    h = real("Psi_hull", Psi_hull)
    if np.any(p < h):
        raise ValueError("Psi_pbx lies below Psi_hull: the hull is the lower envelope")
    return scalar_or_array(p - h)


def lithium_chemical_potential(mu_Li0, E_Li):
    """Li chemical potential imposed by the electrode potential, mu_Li0 - F E_Li (J mol^-1)."""
    m = real("mu_Li0", mu_Li0)
    e = real("E_Li (potential vs Li+/Li)", E_Li)
    return scalar_or_array(m - FARADAY * e)


def lithium_grand_potential(G_phase, N_Li, mu_Li0, E_Li):
    """Li-open grand potential G - n_Li mu_Li per formula unit, J mol^-1."""
    g = real("G_phase", G_phase)
    n = non_negative("N_Li", N_Li)
    return scalar_or_array(g - n * lithium_chemical_potential(mu_Li0, E_Li))


def reaction_grand_potential_change(Delta_G_r, Delta_n_Li, E_Li):
    """Li-open grand-potential change of a decomposition reaction, Delta_G_r - Delta_n F E_Li (J mol^-1).

    Delta_n_Li Li atoms are released to the Li+/Li reservoir per formula unit (negative
    when taken up). Positive means the phase is stable against that reaction at E_Li.
    """
    g = real("Delta_G_r (reaction free energy)", Delta_G_r)
    dn = real("Delta_n_Li (Li released)", Delta_n_Li)
    e = real("E_Li (potential vs Li+/Li)", E_Li)
    return scalar_or_array(g - dn * FARADAY * e)


def reaction_limit_potential(Delta_G_r, Delta_n_Li):
    """Potential vs Li+/Li at which one reaction's grand-potential change vanishes, in V.

    Delta_G_r / (Delta_n_Li F). E_ox is the minimum over reactions with Delta_n_Li > 0 and
    E_red the maximum over reactions with Delta_n_Li < 0; a reaction exchanging no Li has no
    limit potential and is rejected.
    """
    g = real("Delta_G_r (reaction free energy)", Delta_G_r)
    dn = real("Delta_n_Li (Li released)", Delta_n_Li)
    if np.any(dn == 0):
        raise ValueError("Delta_n_Li = 0: a reaction that exchanges no Li sets no potential limit")
    return scalar_or_array(g / (dn * FARADAY))
