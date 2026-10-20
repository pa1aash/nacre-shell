"""Saturation state and the chemical-potential driving force for precipitation.

Convention (theory contract v2, P0-W3.2): one definition of the saturation ratio,

    Omega = IAP / K_sp = a_Ca a_CO3 / K_sp,

and the driving force per formula unit Delta_mu = k_B T ln Omega (molar form
R T ln Omega). Delta_mu > 0 means a supersaturated solution. At equilibrium the ion
chemical potentials are uniform, so the driving force at the template is the bulk one,
Omega = Omega_bulk. The local-ideal Omega_local = (c_local / c_bulk) Omega_bulk of
contract v1 credits the binding free energy to the driving force; it survives only in the
double-counting demonstration (nacre.physics.devtools.wrong_variants).
"""
import numpy as np

from nacre.physics._domain import non_negative, positive, real, scalar_or_array
from nacre.physics.constants import BOLTZMANN, GAS_CONSTANT


def saturation_ratio_bulk(a_Ca, a_CO3, K_sp):
    """Bulk saturation ratio Omega_bulk = a_Ca a_CO3 / K_sp (dimensionless)."""
    a = positive("a_Ca (Ca2+ activity)", a_Ca)
    b = positive("a_CO3 (carbonate activity)", a_CO3)
    k = positive("K_sp (solubility product)", K_sp)
    return scalar_or_array(a * b / k)


def saturation_ratio_bulk_hydrated(a_Ca, a_CO3, a_w, n_hyd, K_sp):
    """LABELLED SENSITIVITY: Omega of a hydrated framing CaCO3.nH2O, a_Ca a_CO3 a_w^n / K_sp.

    Contract v3 (cp2 fix F7). The screen keeps IAP = a_Ca a_CO3; for a_w < 1 that overstates
    Omega by a_w^(-n), so drying states are optimistic. Never used for a verdict.
    """
    a = positive("a_Ca (Ca2+ activity)", a_Ca)
    b = positive("a_CO3 (carbonate activity)", a_CO3)
    w = positive("a_w (water activity)", a_w)
    n = np.asarray(n_hyd, dtype=float)
    if not np.all(np.isfinite(n)) or np.any(n < 0):
        raise ValueError("n_hyd (structural water per formula unit) must be finite and non-negative")
    k = positive("K_sp (solubility product)", K_sp)
    return scalar_or_array(a * b * np.exp(n * np.log(w)) / k)


def driving_force_per_formula_unit(omega, temperature):
    """Driving force Delta_mu = k_B T ln Omega per formula unit, in J.

    Negative for undersaturation (Omega < 1), zero at saturation.
    """
    om = positive("omega (saturation ratio)", omega)
    t = positive("temperature", temperature)
    return scalar_or_array(BOLTZMANN * t * np.log(om))


def driving_force_molar(omega, temperature):
    """Molar driving force Delta_mu_m = R T ln Omega, in J mol^-1."""
    om = positive("omega (saturation ratio)", omega)
    t = positive("temperature", temperature)
    return scalar_or_array(GAS_CONSTANT * t * np.log(om))


# ------------------------------------------------------------------ stoichiometric generalisation (contract v5)
def _stoichiometry(nu_Ca, nu_X, nu_Y, n_hyd):
    return (positive("nu_Ca (Ca ions per formula unit)", nu_Ca), positive("nu_X (anions X per formula unit)", nu_X),
            non_negative("nu_Y (anions Y per formula unit)", nu_Y),
            non_negative("n_hyd (structural water per formula unit)", n_hyd))


def ions_per_formula_unit(nu_Ca, nu_X, nu_Y):
    """Ions per formula unit nu = nu_Ca + nu_X + nu_Y (contract v5)."""
    ca = positive("nu_Ca (Ca ions per formula unit)", nu_Ca)
    x = positive("nu_X (anions X per formula unit)", nu_X)
    y = non_negative("nu_Y (anions Y per formula unit)", nu_Y)
    return scalar_or_array(ca + x + y)


def ln_ion_activity_product(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w, n_hyd):
    """ln IAP of one formula unit, summed over the ions, without forming the product (dimensionless)."""
    ca = positive("a_Ca (Ca2+ activity)", a_Ca)
    x = positive("a_X (activity of anion X)", a_X)
    y = positive("a_Y (activity of anion Y)", a_Y)
    w = positive("a_w (water activity)", a_w)
    n_ca, n_x, n_y, n = _stoichiometry(nu_Ca, nu_X, nu_Y, n_hyd)
    return scalar_or_array(n_ca * np.log(ca) + n_x * np.log(x) + n_y * np.log(y) + n * np.log(w))


def ion_activity_product(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w, n_hyd):
    """IAP = a_Ca^nu_Ca a_X^nu_X a_Y^nu_Y a_w^n of one formula unit (dimensionless; contract v5).

    Structural water enters only through a_w^n. For nu_Y = 0 and n = 0 the activity a_Y does not enter.
    """
    return scalar_or_array(np.exp(ln_ion_activity_product(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w, n_hyd)))


def ln_saturation_ratio_mineral(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w, n_hyd, K_sp):
    """ln Omega = ln(IAP / K_sp) of the formula unit (dimensionless)."""
    k = positive("K_sp (solubility product of the formula unit)", K_sp)
    return scalar_or_array(ln_ion_activity_product(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w, n_hyd) - np.log(k))


def saturation_ratio_mineral(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w, n_hyd, K_sp):
    """Omega_nu = IAP / K_sp of a mineral with nu ions per formula unit (contract v5).

    Calcite is nu_Ca = nu_X = 1, nu_Y = n = 0 and equals saturation_ratio_bulk exactly.
    """
    return scalar_or_array(np.exp(ln_saturation_ratio_mineral(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w, n_hyd, K_sp)))


def driving_force_formula_unit(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w, n_hyd, K_sp, temperature):
    """Delta_mu_fu = k_B T ln Omega_nu per FORMULA UNIT, in J. The per-ion value never enters a barrier."""
    t = positive("temperature", temperature)
    return scalar_or_array(BOLTZMANN * t * ln_saturation_ratio_mineral(a_Ca, a_X, a_Y, nu_Ca, nu_X, nu_Y, a_w,
                                                                       n_hyd, K_sp))


def molar_volume_formula_unit(M_fu, rho_s):
    """Molar volume of the formula unit V_m = M_fu / rho_s, in m^3 mol^-1 (V_m / nu never appears)."""
    m = positive("M_fu (molar mass per formula unit)", M_fu)
    r = positive("rho_s (density of the mineral framing)", rho_s)
    return scalar_or_array(m / r)


def hydroxide_activity(a_w, pH, pKw):
    """a_OH = a_w 10^(pH - pKw) from K_w = a_H a_OH / a_w with a_H = 10^-pH (dimensionless)."""
    w = positive("a_w (water activity)", a_w)
    ph = real("pH", pH)
    k = real("pKw", pKw)
    return scalar_or_array(w * np.exp(np.log(10.0) * (ph - k)))
