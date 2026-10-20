"""Formation criterion of route R1: Al3+-triggered gelation of a polyphosphate (contract v6; ruling C2).

The gel is an Al polyphosphate with nu_Al Al3+ and nu_PP chain units (PO3-) per formula unit,

    Omega_AlPP = a_Al^nu_Al a_PP^nu_PP / K_sp,AlPP,

a FALSIFYING-ONLY criterion: Omega_AlPP < 1 robustly means the gel cannot form at that state; Omega_AlPP > 1 means
"not excluded by thermodynamic accessibility", never a pass. a(Al3+) is taken in two labelled states: the
oxide-equilibrium value (slurry stage, pinned by the oxide; function below) and the pit state (cell stage, a separate
literature input). Complexation by the polyphosphate lowers the free ligand, not the pinned a(Al3+).
"""
import numpy as np

from nacre.physics._domain import non_negative, positive, real, scalar_or_array

LN10 = np.log(10.0)


def aluminium_activity_oxide_equilibrium(K_ox_Al, pH, a_w):
    """a_Al = K_ox,Al 10^(-3 pH) / a_w^3: free Al3+ activity pinned by the oxide or hydroxide in contact.

    From Al(OH)3 + 3 H+ = Al3+ + 3 H2O with K_ox,Al from the Al-O-H Pourbaix (dimensionless).
    """
    k = positive("K_ox_Al (oxide dissolution constant)", K_ox_Al)
    ph = real("pH", pH)
    w = positive("a_w (water activity)", a_w)
    return scalar_or_array(np.exp(np.log(k) - 3.0 * LN10 * ph - 3.0 * np.log(w)))


def free_chain_unit_activity(a_PP_tot, beta_AlPP, a_Al):
    """a_PP = a_PP,tot / (1 + beta_AlPP a_Al): free chain-unit activity after 1:1 complexation by Al3+.

    With beta_AlPP a gap the row is evaluated at beta_AlPP = 0 (the upper bound on a_PP) and flagged.
    """
    t = positive("a_PP_tot (total chain-unit activity)", a_PP_tot)
    b = non_negative("beta_AlPP (Al-polyphosphate complexation constant)", beta_AlPP)
    a = positive("a_Al (free Al3+ activity)", a_Al)
    return scalar_or_array(t / (1.0 + b * a))


def ln_ion_activity_product_alpp(a_Al, a_PP, nu_Al, nu_PP):
    a = positive("a_Al (free Al3+ activity)", a_Al)
    p = positive("a_PP (free chain-unit activity)", a_PP)
    na = positive("nu_Al (Al3+ per formula unit)", nu_Al)
    npp = positive("nu_PP (chain units per formula unit)", nu_PP)
    return na * np.log(a) + npp * np.log(p)


def ion_activity_product_alpp(a_Al, a_PP, nu_Al, nu_PP):
    """IAP_AlPP = a_Al^nu_Al a_PP^nu_PP of the gel's formula unit (dimensionless)."""
    return scalar_or_array(np.exp(ln_ion_activity_product_alpp(a_Al, a_PP, nu_Al, nu_PP)))


def saturation_ratio_alpp(a_Al, a_PP, nu_Al, nu_PP, K_sp_AlPP):
    """Omega_AlPP = IAP_AlPP / K_sp,AlPP: the R1 falsifying-only criterion (dimensionless)."""
    k = positive("K_sp_AlPP (solubility product of the gel)", K_sp_AlPP)
    return scalar_or_array(np.exp(ln_ion_activity_product_alpp(a_Al, a_PP, nu_Al, nu_PP) - np.log(k)))
