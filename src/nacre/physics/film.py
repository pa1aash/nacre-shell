"""Electronic limitation of an insulating interfacial film (claim C4 item 18, R-cell).

A stated limitation, not a corrosion or device claim: the film thickness above which the
collector contact can no longer pass a required current, in the ohmic and in the direct
tunnelling limit.
"""
import numpy as np

from nacre.physics._domain import positive, scalar_or_array
from nacre.physics.constants import ELECTRON_MASS, HBAR


def area_specific_resistance(rho_e, d_film):
    """Area-specific electronic resistance of the film R_A = rho_e d, in Ohm m^2."""
    return scalar_or_array(positive("rho_e (resistivity)", rho_e) * positive("d_film (thickness)", d_film))


def ohmic_thickness_bound(R_A_max, rho_e):
    """Largest film thickness compatible with R_A_max in the ohmic limit, R_A_max / rho_e (m)."""
    return scalar_or_array(positive("R_A_max", R_A_max) / positive("rho_e (resistivity)", rho_e))


def tunnelling_decay_constant(phi_B):
    """Decay constant of the electron wavefunction in the film, sqrt(2 m_e phi_B) / hbar (m^-1)."""
    return scalar_or_array(np.sqrt(2.0 * ELECTRON_MASS * positive("phi_B (barrier height)", phi_B)) / HBAR)


def tunnelling_thickness_bound(j_0, j_req, kappa):
    """Largest thickness passing j_req by direct tunnelling, ln(j_0 / j_req) / (2 kappa), in m.

    Negative when j_req exceeds the zero-thickness prefactor j_0 (no film thickness works).
    """
    j0 = positive("j_0 (tunnelling prefactor)", j_0)
    jr = positive("j_req (required current density)", j_req)
    k = positive("kappa (decay constant)", kappa)
    return scalar_or_array(np.log(j0 / jr) / (2.0 * k))
